"""Report what the قبض انبار numbering migration actually left in the database.

Read-only. Run any time, with the API up or down:

    python verify_ghabz_numbering.py

Checks the five columns, then the two uniqueness objects. The uniqueness check
matters more than it looks: a UNIQUE CONSTRAINT and a plain non-unique INDEX of
the same name both satisfy a naive "already exists" test, but only the unique
one prevents two concurrent saves from allocating the same sequence on one
tally.
"""

from app.core.db import get_connection


HEADER_TABLE = "fa_ghabz_anbar_header"
DETAILS_TABLE = "FA_ghabz_anbar_DETAILES"

EXPECTED_COLUMNS = {
    HEADER_TABLE: {
        "GHABZ_NUMBER": "VARCHAR2(30)",
        "GHABZ_SEQ": "NUMBER",
        "TRACKING_NUMBER": "VARCHAR2(100)",
    },
    DETAILS_TABLE: {
        "HSCODE": "VARCHAR2(250)",
        "ID_TALI_DETAILS": "NUMBER",
    },
}

EXPECTED_UNIQUE = {
    "UQ_FA_GHABZ_NUMBER": ["GHABZ_NUMBER"],
    "UQ_FA_GHABZ_TALI_SEQ": ["TALI_ID", "GHABZ_SEQ"],
}


def _resolve_table(cursor, requested: str) -> str | None:
    cursor.execute("SELECT TABLE_NAME FROM USER_TABLES")
    known = {str(row[0]).casefold(): str(row[0]) for row in cursor.fetchall()}
    return known.get(requested.casefold())


def _describe(data_type: str, char_length, precision, scale) -> str:
    if data_type in {"VARCHAR2", "NVARCHAR2", "CHAR"}:
        return f"{data_type}({int(char_length or 0)})"
    if data_type == "NUMBER":
        if precision is None:
            return "NUMBER"
        return f"NUMBER({int(precision)},{int(scale or 0)})"
    return data_type


def _check_columns(cursor) -> list[str]:
    problems: list[str] = []
    print("columns")
    print("-------")
    for requested_table, columns in EXPECTED_COLUMNS.items():
        table = _resolve_table(cursor, requested_table)
        if table is None:
            problems.append(f"table {requested_table} is missing")
            print(f"  FAIL  {requested_table}: table not found")
            continue

        cursor.execute(
            """
            SELECT COLUMN_NAME, DATA_TYPE, CHAR_LENGTH, DATA_PRECISION,
                   DATA_SCALE, NULLABLE
              FROM USER_TAB_COLUMNS
             WHERE TABLE_NAME = :table_name
            """,
            {"table_name": table},
        )
        found = {
            str(row[0]).casefold(): row for row in cursor.fetchall()
        }

        for column, expected in columns.items():
            row = found.get(column.casefold())
            if row is None:
                problems.append(f"{table}.{column} is missing")
                print(f"  FAIL  {table}.{column}: missing")
                continue
            actual = _describe(str(row[1]), row[2], row[3], row[4])
            nullable = "NULL" if str(row[5]) == "Y" else "NOT NULL"
            verdict = "ok  " if actual == expected else "WARN"
            if actual != expected:
                problems.append(
                    f"{table}.{column} is {actual}, expected {expected}"
                )
            print(f"  {verdict}  {table}.{row[0]}: {actual} {nullable}")
    return problems


def _check_uniqueness(cursor) -> list[str]:
    problems: list[str] = []
    print()
    print("uniqueness")
    print("----------")
    for name, expected_columns in EXPECTED_UNIQUE.items():
        cursor.execute(
            """
            SELECT CONSTRAINT_TYPE, STATUS, TABLE_NAME
              FROM USER_CONSTRAINTS
             WHERE CONSTRAINT_NAME = :name
            """,
            {"name": name},
        )
        constraint = cursor.fetchone()

        cursor.execute(
            """
            SELECT UNIQUENESS, TABLE_NAME, STATUS
              FROM USER_INDEXES
             WHERE INDEX_NAME = :name
            """,
            {"name": name},
        )
        index = cursor.fetchone()

        cursor.execute(
            """
            SELECT COLUMN_NAME
              FROM USER_IND_COLUMNS
             WHERE INDEX_NAME = :name
             ORDER BY COLUMN_POSITION
            """,
            {"name": name},
        )
        index_columns = [str(row[0]) for row in cursor.fetchall()]

        if constraint is None and index is None:
            problems.append(f"{name} does not exist")
            print(f"  FAIL  {name}: not found")
            continue

        if constraint is not None:
            kind = {"U": "UNIQUE constraint", "P": "PRIMARY KEY"}.get(
                str(constraint[0]), f"constraint type {constraint[0]}"
            )
            enforced = str(constraint[0]) in {"U", "P"} and str(constraint[1]) == "ENABLED"
            print(f"  {'ok  ' if enforced else 'FAIL'}  {name}: {kind}, {constraint[1]}")
            if not enforced:
                problems.append(f"{name} exists but is not an enabled UNIQUE constraint")
        else:
            uniqueness = str(index[0])
            enforced = uniqueness == "UNIQUE"
            print(
                f"  {'ok  ' if enforced else 'FAIL'}  {name}: "
                f"{uniqueness} index (no constraint), {index[2]}"
            )
            if not enforced:
                problems.append(
                    f"{name} is a NON-UNIQUE index — it does not prevent duplicates"
                )

        if index_columns and [c.casefold() for c in index_columns] != [
            c.casefold() for c in expected_columns
        ]:
            problems.append(
                f"{name} covers {index_columns}, expected {expected_columns}"
            )
            print(f"  WARN  {name}: covers {index_columns}, expected {expected_columns}")
        elif index_columns:
            print(f"        {name}: covers {index_columns}")
    return problems


def _check_data(cursor) -> None:
    print()
    print("existing rows")
    print("-------------")
    table = _resolve_table(cursor, HEADER_TABLE)
    if table is None:
        return
    cursor.execute(
        f"""
        SELECT COUNT(*),
               COUNT("TALI_ID"),
               COUNT("GHABZ_NUMBER"),
               COUNT("GHABZ_SEQ")
          FROM "{table}"
        """
    )
    total, with_tally, with_number, with_seq = cursor.fetchone()
    print(f"  receipts total          : {int(total)}")
    print(f"  linked to a tally       : {int(with_tally)}")
    print(f"  already have a number   : {int(with_number)}")
    print(f"  already have a sequence : {int(with_seq)}")

    cursor.execute(
        f"""
        SELECT "TALI_ID", "GHABZ_SEQ", COUNT(*)
          FROM "{table}"
         WHERE "TALI_ID" IS NOT NULL AND "GHABZ_SEQ" IS NOT NULL
         GROUP BY "TALI_ID", "GHABZ_SEQ"
        HAVING COUNT(*) > 1
        """
    )
    duplicates = cursor.fetchall()
    if duplicates:
        print(f"  DUPLICATE (tally, sequence) pairs: {len(duplicates)}")
        for tali_id, seq, count in duplicates:
            print(f"    tally {int(tali_id)} sequence {int(seq)} appears {int(count)}x")
    else:
        print("  duplicate (tally, sequence) pairs: none")


def main() -> None:
    with get_connection() as connection:
        with connection.cursor() as cursor:
            problems = _check_columns(cursor)
            problems += _check_uniqueness(cursor)
            _check_data(cursor)

    print()
    if problems:
        print(f"{len(problems)} problem(s) found:")
        for problem in problems:
            print(f"  - {problem}")
    else:
        print("all good — schema matches what the numbering code expects")


if __name__ == "__main__":
    main()
