"""Finish and correct the interrupted identity rebuild.

    python repair_identity_columns.py --report      # look, change nothing
    python repair_identity_columns.py --dry-run     # print every statement
    python repair_identity_columns.py

Replaces fix_identity_columns.py, which had three faults:

1. It ran ALTER TABLE ... MODIFY (col NOT NULL) after renaming the new column
   into place. An identity column is already NOT NULL, so this raised ORA-01442
   and stopped the rebuild just before the primary key was restored.

2. It treated any NUMBER primary key as a surrogate. FA_TALI_NUMBER_COUNTER's
   key is JALALI_YEAR -- a Persian year, entered deliberately -- and must not
   generate its own values. It was also NUMBER(4,0) and came back as NUMBER.

3. It called connection.rollback() when a step failed. Oracle commits DDL
   implicitly, so nothing was rolled back and the tables were left half built.

Because DDL cannot be rolled back, this script is written to be resumable
rather than transactional: it reads the current state of each table and does
only what is still missing. Re-running it after a failure is safe and is the
intended way to recover.

Primary keys and foreign keys are restored from the captured DDL in
sql/schema/, which is what that capture is for. Constraints that already exist
are reported and skipped.
"""

import argparse
import os
import sys

from app.core.db import get_connection

try:
    from run_sql import iter_statements
except ImportError:  # pragma: no cover
    print("run_sql.py must sit next to this script.")
    raise


SCHEMA_DIR = os.path.join("sql", "schema")
CONSTRAINTS_FILE = "03_constraints.sql"
FOREIGN_KEYS_FILE = "04_foreign_keys.sql"

# Keys that carry meaning and are supplied by the application. These must stay
# plain columns; an identity here would silently invent a year.
NATURAL_KEYS = {
    "FA_TALI_NUMBER_COUNTER": ("JALALI_YEAR", "NUMBER(4,0)"),
}

TEMP_SUFFIX = "_REBUILD_TMP"

# "already exists" outcomes when replaying captured constraint DDL.
ALREADY_THERE = (
    "ORA-00955",  # name is already used by an existing object
    "ORA-02260",  # table can have only one primary key
    "ORA-02261",  # such unique or primary key already exists
    "ORA-02264",  # name already used by an existing constraint
    "ORA-02275",  # such a referential constraint already exists
)


def _q(name: str) -> str:
    return f'"{name}"'


def _app_tables(cursor) -> list[str]:
    cursor.execute(
        """
        SELECT TABLE_NAME
        FROM USER_TABLES
        WHERE (DROPPED IS NULL OR DROPPED = 'NO')
          AND (SECONDARY IS NULL OR SECONDARY = 'N')
          AND UPPER(TABLE_NAME) LIKE 'FA\\_%' ESCAPE '\\'
        ORDER BY TABLE_NAME
        """
    )
    return [row[0] for row in cursor.fetchall()]


def _identity_columns(cursor) -> dict[str, str]:
    cursor.execute("SELECT TABLE_NAME, COLUMN_NAME FROM USER_TAB_IDENTITY_COLS")
    return {row[0]: row[1] for row in cursor.fetchall()}


def _has_primary_key(cursor, table: str) -> bool:
    cursor.execute(
        """
        SELECT COUNT(*)
        FROM USER_CONSTRAINTS
        WHERE TABLE_NAME = :t AND CONSTRAINT_TYPE = 'P'
        """,
        {"t": table},
    )
    return int(cursor.fetchone()[0]) > 0


def _column_exists(cursor, table: str, column: str) -> bool:
    cursor.execute(
        """
        SELECT COUNT(*)
        FROM USER_TAB_COLS
        WHERE TABLE_NAME = :t AND COLUMN_NAME = :c
        """,
        {"t": table, "c": column},
    )
    return int(cursor.fetchone()[0]) > 0


def _column_spec(cursor, table: str, column: str) -> str | None:
    cursor.execute(
        """
        SELECT DATA_TYPE, DATA_PRECISION, DATA_SCALE, NULLABLE
        FROM USER_TAB_COLUMNS
        WHERE TABLE_NAME = :t AND COLUMN_NAME = :c
        """,
        {"t": table, "c": column},
    )
    row = cursor.fetchone()
    if row is None:
        return None
    data_type, precision, scale, nullable = row
    if data_type == "NUMBER" and precision is not None:
        data_type = f"NUMBER({int(precision)},{int(scale or 0)})"
    return f"{data_type}{'' if nullable == 'Y' else ' NOT NULL'}"


def _row_count(cursor, table: str) -> int:
    cursor.execute(f"SELECT COUNT(*) FROM {_q(table)}")
    return int(cursor.fetchone()[0])


def _run(cursor, sql: str, apply: bool, ignore: tuple = ()) -> bool:
    if not apply:
        print(f"      {sql}")
        return True
    try:
        cursor.execute(sql)
        return True
    except Exception as exc:  # noqa: BLE001
        message = str(exc).splitlines()[0]
        if message.upper().startswith(ignore):
            return True
        print(f"      ! {message}")
        return False


def report(cursor) -> list[dict]:
    """Work out what each table still needs. Reads only."""
    identity = _identity_columns(cursor)
    findings = []

    for table in _app_tables(cursor):
        natural = NATURAL_KEYS.get(table)
        has_pk = _has_primary_key(cursor, table)
        identity_column = identity.get(table)
        needs = []

        if natural:
            column, wanted_type = natural
            if identity_column == column:
                needs.append("remove identity (natural key)")
            elif _column_spec(cursor, table, column) and not _column_spec(
                cursor, table, column
            ).startswith(wanted_type):
                needs.append(f"restore type {wanted_type}")
        if not has_pk:
            needs.append("restore primary key")

        if needs:
            findings.append(
                {
                    "table": table,
                    "identity": identity_column,
                    "natural": natural,
                    "has_pk": has_pk,
                    "needs": needs,
                    "rows": _row_count(cursor, table),
                }
            )

    return findings


def demote_natural_key(cursor, table: str, column: str, wanted_type: str, apply: bool) -> bool:
    """Turn an identity column back into a plain column of the right type."""
    temp = column + TEMP_SUFFIX
    before = _row_count(cursor, table)
    print(f"    demoting {column} to {wanted_type} ({before:,} row(s))")

    if _column_exists(cursor, table, temp):
        print(f"      ! {temp} already exists from an earlier attempt -- drop it first")
        return False

    steps = [
        f"ALTER TABLE {_q(table)} ADD ({_q(temp)} {wanted_type})",
        f"UPDATE {_q(table)} SET {_q(temp)} = {_q(column)}",
        f"ALTER TABLE {_q(table)} DROP COLUMN {_q(column)} CASCADE CONSTRAINTS",
        f"ALTER TABLE {_q(table)} RENAME COLUMN {_q(temp)} TO {_q(column)}",
        # Needed here, unlike the identity case: a plain column is nullable.
        f"ALTER TABLE {_q(table)} MODIFY ({_q(column)} NOT NULL)",
    ]
    for sql in steps:
        if not _run(cursor, sql, apply):
            return False

    if apply:
        after = _row_count(cursor, table)
        if after != before:
            print(f"      ! row count changed {before:,} -> {after:,}")
            return False
        cursor.execute(f"SELECT {_q(column)} FROM {_q(table)} ORDER BY 1")
        values = ", ".join(str(row[0]) for row in cursor.fetchall())
        print(f"      values preserved: {values}")
    return True


def replay(cursor, path: str, apply: bool, label: str) -> tuple[int, int]:
    """Re-apply captured constraint DDL, skipping what is already there."""
    if not os.path.exists(path):
        print(f"  ! {path} not found -- run extract_schema.py, or restore from git")
        return 0, 0

    added, present = 0, 0
    for _, _, sql in iter_statements(path):
        if not apply:
            print(f"      {sql.splitlines()[0][:100]}")
            added += 1
            continue
        try:
            cursor.execute(sql)
            if "CONSTRAINT" in sql.upper():
                name = sql.split("CONSTRAINT", 1)[-1].strip().split()[0]
            else:
                name = sql.strip().splitlines()[0][:60]
            print(f"    + {label} {name}")
            added += 1
        except Exception as exc:  # noqa: BLE001
            if str(exc).upper().startswith(ALREADY_THERE):
                present += 1
            else:
                print(f"    ! {str(exc).splitlines()[0]}")
    return added, present


def resync(cursor, apply: bool) -> int:
    count = 0
    for table, column in sorted(_identity_columns(cursor).items()):
        if _run(
            cursor,
            f"ALTER TABLE {_q(table)} MODIFY ({_q(column)} "
            f"GENERATED BY DEFAULT AS IDENTITY (START WITH LIMIT VALUE))",
            apply,
        ):
            count += 1
    return count


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--report", action="store_true", help="show state, change nothing")
    parser.add_argument("--dry-run", action="store_true", help="print statements only")
    parser.add_argument("--schema-dir", default=SCHEMA_DIR)
    args = parser.parse_args()
    apply = not (args.dry_run or args.report)

    with get_connection() as connection:
        cursor = connection.cursor()
        cursor.execute("SELECT USER FROM DUAL")
        print(f"Connected as {cursor.fetchone()[0]}\n")

        findings = report(cursor)
        if not findings:
            print("Nothing to repair -- every table has its primary key and the")
            print("right kind of key column.")
        else:
            print("Tables needing repair")
            for f in findings:
                identity = f["identity"] or "-"
                print(f"  {f['table']}  ({f['rows']:,} rows, identity: {identity})")
                for need in f["needs"]:
                    print(f"    - {need}")

        if args.report:
            print("\nReport only -- nothing was changed.")
            return

        if findings:
            print("\nRepairing key columns")
            for f in findings:
                if not f["natural"]:
                    continue
                column, wanted_type = f["natural"]
                if f["identity"] == column:
                    print(f"  {f['table']}")
                    if not demote_natural_key(
                        cursor, f["table"], column, wanted_type, apply
                    ):
                        print("\n  Stopped. Re-run after fixing the error above.")
                        sys.exit(1)

        print("\nRestoring primary and unique keys")
        added_pk, present_pk = replay(
            cursor, os.path.join(args.schema_dir, CONSTRAINTS_FILE), apply, "constraint"
        )
        print(f"    added {added_pk}, already present {present_pk}")

        print("\nRestoring foreign keys")
        added_fk, present_fk = replay(
            cursor, os.path.join(args.schema_dir, FOREIGN_KEYS_FILE), apply, "foreign key"
        )
        print(f"    added {added_fk}, already present {present_fk}")

        print("\nResyncing identity counters")
        print(f"    {resync(cursor, apply)} column(s)")

        if apply:
            print("\nVerifying")
            remaining = report(cursor)
            if remaining:
                for f in remaining:
                    print(f"  ! {f['table']}: {', '.join(f['needs'])}")
                sys.exit(1)
            identity = _identity_columns(cursor)
            for table, (column, _) in NATURAL_KEYS.items():
                state = "identity" if identity.get(table) == column else "plain"
                print(f"  {table}.{column}: {state}")
            print(f"  {len(identity)} identity column(s), every table has its key")
            print("\nOK")

    if args.dry_run:
        print("\nDry run -- nothing was changed.")


if __name__ == "__main__":
    main()
