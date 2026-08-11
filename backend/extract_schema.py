"""Capture the live schema DDL into versioned .sql files under sql/schema/.

Run from the backend directory, with the API stopped or running (read-only):

    python extract_schema.py

The script never writes to the database. It only reads USER_* dictionary views
and calls DBMS_METADATA.GET_DDL on objects the connected user owns.

Output layout (all files overwritten on every run):

    sql/schema/README.md            capture manifest: objects, row counts, high-water marks
    sql/schema/rebuild.sql          runs the numbered files below in order
    sql/schema/01_sequences.sql
    sql/schema/02_tables.sql
    sql/schema/03_constraints.sql   primary keys, unique keys, check constraints
    sql/schema/04_foreign_keys.sql
    sql/schema/05_indexes.sql       non-constraint indexes only
    sql/schema/06_triggers.sql
    sql/schema/07_comments.sql

Output is deterministic: objects are captured in alphabetical order, storage and
tablespace clauses are stripped, the owning schema prefix is removed, and
START WITH counters are normalised to 1. Re-running produces byte-identical
files unless the schema actually changed, so `git diff` is meaningful. The live
sequence and identity high-water marks are recorded in README.md instead, where
they belong -- they are data, not schema.

Rebuild a fresh database from the output with:

    sqlplus <user>/<password>@<dsn> @sql/schema/rebuild.sql
"""

import argparse
import datetime
import os
import re

from app.core.db import get_connection


OUTPUT_DIR = os.path.join("sql", "schema")

# Tables the FastAPI backend currently reads or writes. Used only to flag rows
# in the manifest -- capture is never limited to this list, because a schema
# backup that omits a table the app needs next month is not a backup.
APP_TABLES = {
    "fa_anbar",
    "fa_commodity_catalog",
    "fa_ghabz_anbar_detailes",
    "fa_ghabz_anbar_header",
    "fa_kala",
    "fa_kala_dangerous",
    "fa_kala_diamound",
    "fa_kala_other_service",
    "fa_kala_price",
    "fa_kala_strip",
    "fa_kala_time_stop_vehicle",
    "fa_kala_vehicle_enter_price",
    "fa_owner_representative",
    "fa_product_owner",
    "fa_representative_company",
    "fa_sorat_hesab_header",
    "fa_sys_term_categories",
    "fa_sys_terms",
    "fa_tagh_anbar",
    "fa_tali_detailes",
    "fa_tali_header",
    "fa_tali_kala_dangerous",
    "fa_tali_kala_diamound",
    "fa_tali_kala_other_service",
    "fa_tali_kala_price",
    "fa_tali_kala_strip",
    "fa_tali_kala_time_stop_vehicle",
    "fa_tali_kala_vehicle_enter_price",
    "fa_tali_number_counter",
    "fa_transport_company",
    "fa_users",
}

# Oracle sample-schema and tooling leftovers that are not part of the product.
SKIP_PREFIXES = ("BIN$", "APEX$", "AQ$", "DR$", "MLOG$", "RUPD$", "SYS_")
SKIP_EXACT = {
    "COUNTRIES",
    "DEPARTMENTS",
    "EMPLOYEES",
    "JOBS",
    "JOB_HISTORY",
    "LOCATIONS",
    "REGIONS",
}

TRANSFORM_PARAMS = [
    ("PRETTY", True),
    ("SQLTERMINATOR", True),
    ("SEGMENT_ATTRIBUTES", False),
    ("STORAGE", False),
    ("TABLESPACE", False),
    ("CONSTRAINTS", False),
    ("REF_CONSTRAINTS", False),
]

# ORA-31608: specified object of type ... not found (no dependent objects)
NO_DEPENDENT_OBJECTS = "ORA-31608"

_START_WITH_RE = re.compile(r"\bSTART WITH\s+\d+", re.IGNORECASE)

# Fallback for environments where SET_TRANSFORM_PARAM rejects a parameter and
# storage clauses survive into the DDL anyway.
_NOISE_RE = [
    re.compile(r"\s*SEGMENT CREATION (?:IMMEDIATE|DEFERRED)", re.IGNORECASE),
    re.compile(r'\s*(?:NO)?COMPRESS FOR [A-Z ]+|\s*\b(?:NO)?COMPRESS\b', re.IGNORECASE),
    re.compile(r"\s*\b(?:NO)?LOGGING\b", re.IGNORECASE),
    re.compile(r'\s*TABLESPACE\s+"[^"]+"', re.IGNORECASE),
    re.compile(r"\s*STORAGE\s*\([^)]*\)", re.IGNORECASE),
    re.compile(
        r"\s*PCTFREE\s+\d+|\s*PCTUSED\s+\d+|\s*INITRANS\s+\d+|\s*MAXTRANS\s+\d+",
        re.IGNORECASE,
    ),
]


def _q(identifier: str) -> str:
    return f'"{identifier}"'


def _text(value) -> str:
    """DBMS_METADATA returns a CLOB. app.core.db sets fetch_lobs = False, so it
    normally arrives as str already; handle the LOB case defensively."""
    if value is None:
        return ""
    if isinstance(value, str):
        return value
    return value.read()


def _clean(ddl: str, owner: str, keep_start_with: bool, terminate: bool = True) -> str:
    """Strip environment-specific noise so the file is portable and stable.

    ``terminate`` appends a statement terminator when SQLTERMINATOR could not be
    set. Triggers pass False: their body already ends in END; and they are
    closed with a slash instead.
    """
    ddl = ddl.strip()
    # Only the connected schema's own prefix is removed. Anything broader would
    # corrupt three-part names such as "HR"."FA_KALA"."NAME" in COMMENT DDL.
    ddl = ddl.replace(f'"{owner}".', "")
    if not keep_start_with:
        ddl = _START_WITH_RE.sub("START WITH 1", ddl)
    for pattern in _NOISE_RE:
        ddl = pattern.sub("", ddl)
    # DBMS_METADATA pads lines with trailing spaces; kill them so git diffs are clean.
    lines = [line.rstrip() for line in ddl.splitlines()]
    lines = [line for i, line in enumerate(lines) if line or (i and lines[i - 1])]
    while lines and not lines[0]:
        lines.pop(0)
    while lines and not lines[-1]:
        lines.pop()
    result = "\n".join(lines)
    if terminate and result and not result.rstrip().endswith(";"):
        result += " ;"
    return result


def _get_ddl(
    cursor,
    object_type: str,
    name: str,
    owner: str,
    keep_start_with: bool,
    terminate: bool = True,
):
    """Return cleaned DDL for one object, or None when it has none."""
    try:
        cursor.execute(
            "SELECT DBMS_METADATA.GET_DDL(:object_type, :name) FROM DUAL",
            {"object_type": object_type, "name": name},
        )
        row = cursor.fetchone()
    except Exception as exc:  # noqa: BLE001 - reported, not swallowed
        if NO_DEPENDENT_OBJECTS in str(exc):
            return None
        print(f"  ! {object_type} {name}: {exc}")
        return None
    if row is None:
        return None
    ddl = _clean(_text(row[0]), owner, keep_start_with, terminate)
    return ddl or None


def _get_dependent_ddl(cursor, object_type: str, name: str, owner: str, keep_start_with: bool):
    try:
        cursor.execute(
            "SELECT DBMS_METADATA.GET_DEPENDENT_DDL(:object_type, :name) FROM DUAL",
            {"object_type": object_type, "name": name},
        )
        row = cursor.fetchone()
    except Exception as exc:  # noqa: BLE001
        if NO_DEPENDENT_OBJECTS in str(exc):
            return None
        print(f"  ! {object_type} on {name}: {exc}")
        return None
    if row is None:
        return None
    ddl = _clean(_text(row[0]), owner, keep_start_with)
    return ddl or None


def _configure_session(cursor) -> set[str]:
    """Apply session transforms and return the set that actually took effect.

    The value must be a PL/SQL BOOLEAN literal. Binding a Python bool or int
    sends a NUMBER, PL/SQL resolves the VARCHAR2 overload instead, and every
    call fails with ORA-31600. Parameter names come from TRANSFORM_PARAMS, not
    from input, so inlining them is safe.
    """
    applied = set()
    for param, value in TRANSFORM_PARAMS:
        literal = "TRUE" if value else "FALSE"
        try:
            cursor.execute(
                f"""
                BEGIN
                    DBMS_METADATA.SET_TRANSFORM_PARAM(
                        DBMS_METADATA.SESSION_TRANSFORM, :param, {literal});
                END;
                """,
                {"param": param},
            )
            applied.add(param)
        except Exception as exc:  # noqa: BLE001
            first_line = str(exc).splitlines()[0]
            print(f"  ! transform {param} rejected: {first_line}")
    return applied


def _current_owner(cursor) -> str:
    cursor.execute("SELECT USER FROM DUAL")
    return cursor.fetchone()[0]


def _is_wanted(table_name: str) -> bool:
    if table_name in SKIP_EXACT:
        return False
    if table_name.upper().startswith(SKIP_PREFIXES):
        return False
    if table_name.upper().startswith("FA_") or table_name.lower().startswith("fa_"):
        return True
    return table_name.lower() in APP_TABLES


def _tables(cursor) -> list[str]:
    """Real table names, exactly as stored. Never assume upper case: this schema
    mixes FA_KALA with fa_kala_price."""
    cursor.execute(
        """
        SELECT TABLE_NAME
        FROM USER_TABLES
        WHERE (DROPPED IS NULL OR DROPPED = 'NO')
          AND (SECONDARY IS NULL OR SECONDARY = 'N')
        ORDER BY LOWER(TABLE_NAME), TABLE_NAME
        """
    )
    return [row[0] for row in cursor.fetchall() if _is_wanted(row[0])]


def _sequences(cursor) -> list[tuple[str, int]]:
    """Standalone sequences only. Identity-backing sequences (ISEQ$$_...) are
    created automatically with their column and must not be scripted separately."""
    cursor.execute(
        """
        SELECT SEQUENCE_NAME, LAST_NUMBER
        FROM USER_SEQUENCES
        WHERE SEQUENCE_NAME NOT IN (
            SELECT SEQUENCE_NAME FROM USER_TAB_IDENTITY_COLS
        )
        ORDER BY LOWER(SEQUENCE_NAME), SEQUENCE_NAME
        """
    )
    return [
        (row[0], int(row[1]) if row[1] is not None else 0)
        for row in cursor.fetchall()
        if not row[0].upper().startswith(SKIP_PREFIXES)
        and not row[0].upper().startswith("ISEQ$")
    ]


def _constraints(cursor, table: str, kinds: tuple[str, ...]) -> list[str]:
    """Constraint names for a table, excluding auto-generated NOT NULL checks
    (those are already inline in the CREATE TABLE output)."""
    placeholders = ", ".join(f":k{i}" for i in range(len(kinds)))
    params = {f"k{i}": kind for i, kind in enumerate(kinds)}
    params["table_name"] = table
    cursor.execute(
        f"""
        SELECT CONSTRAINT_NAME, CONSTRAINT_TYPE, GENERATED, SEARCH_CONDITION_VC
        FROM USER_CONSTRAINTS
        WHERE TABLE_NAME = :table_name
          AND CONSTRAINT_TYPE IN ({placeholders})
        ORDER BY CONSTRAINT_TYPE, CONSTRAINT_NAME
        """,
        params,
    )
    names = []
    for name, kind, generated, condition in cursor.fetchall():
        if kind == "C" and generated == "GENERATED NAME":
            text = (condition or "").upper()
            if "IS NOT NULL" in text:
                continue
        names.append(name)
    return names


def _plain_indexes(cursor, table: str) -> list[str]:
    """Indexes that are not backing a primary/unique constraint."""
    cursor.execute(
        """
        SELECT i.INDEX_NAME
        FROM USER_INDEXES i
        WHERE i.TABLE_NAME = :table_name
          AND i.INDEX_NAME NOT IN (
              SELECT c.INDEX_NAME
              FROM USER_CONSTRAINTS c
              WHERE c.TABLE_NAME = :table_name
                AND c.CONSTRAINT_TYPE IN ('P', 'U')
                AND c.INDEX_NAME IS NOT NULL
          )
          AND (i.DROPPED IS NULL OR i.DROPPED = 'NO')
        ORDER BY i.INDEX_NAME
        """,
        {"table_name": table},
    )
    return [row[0] for row in cursor.fetchall()]


def _triggers(cursor, table: str) -> list[str]:
    cursor.execute(
        """
        SELECT TRIGGER_NAME
        FROM USER_TRIGGERS
        WHERE TABLE_NAME = :table_name
        ORDER BY TRIGGER_NAME
        """,
        {"table_name": table},
    )
    return [row[0] for row in cursor.fetchall()]


def _row_count(cursor, table: str) -> int | None:
    try:
        cursor.execute(f"SELECT COUNT(*) FROM {_q(table)}")
        return int(cursor.fetchone()[0])
    except Exception as exc:  # noqa: BLE001
        print(f"  ! count {table}: {exc}")
        return None


def _identity_high_water(cursor) -> dict[str, int]:
    """Current value of every identity column, keyed as table.column."""
    marks = {}
    try:
        cursor.execute(
            """
            SELECT t.TABLE_NAME, t.COLUMN_NAME, s.LAST_NUMBER
            FROM USER_TAB_IDENTITY_COLS t
            JOIN USER_SEQUENCES s ON s.SEQUENCE_NAME = t.SEQUENCE_NAME
            ORDER BY t.TABLE_NAME, t.COLUMN_NAME
            """
        )
        for table, column, last_number in cursor.fetchall():
            marks[f"{table}.{column}"] = int(last_number or 0)
    except Exception as exc:  # noqa: BLE001
        print(f"  ! identity high-water marks unavailable: {exc}")
    return marks


_INLINE_CONSTRAINT_RE = re.compile(
    r'CONSTRAINT\s+"[^"]+"\s+(?:PRIMARY KEY|UNIQUE|FOREIGN KEY|CHECK)',
    re.IGNORECASE,
)


def _verify(applied: set[str], table_blocks: list[str]) -> list[str]:
    """Catch the failure mode where transforms silently did not apply, leaving
    constraints both inline in CREATE TABLE and repeated as ALTER statements.
    Running that would fail with ORA-02264 partway through the rebuild."""
    problems = []
    required = {"CONSTRAINTS", "REF_CONSTRAINTS"}
    for param in sorted(required - applied):
        problems.append(
            f"transform {param} was rejected, so constraints are inline in "
            f"02_tables.sql as well as in 03/04 -- rebuild.sql would fail"
        )
    inline = [
        block.splitlines()[0].lstrip("- ").strip()
        for block in table_blocks
        if _INLINE_CONSTRAINT_RE.search(block)
    ]
    if inline:
        shown = ", ".join(inline[:5])
        more = f" (+{len(inline) - 5} more)" if len(inline) > 5 else ""
        problems.append(f"inline constraints still present in: {shown}{more}")
    return problems


def _section(title: str) -> str:
    bar = "-" * 74
    return f"-- {bar}\n-- {title}\n-- {bar}"


def _write(path: str, header: str, blocks: list[str]) -> int:
    body = "\n\n".join(blocks)
    content = f"{header}\n\n{body}\n" if blocks else f"{header}\n\n-- (none)\n"
    with open(path, "w", encoding="utf-8", newline="\n") as handle:
        handle.write(content)
    return len(blocks)


def _file_header(title: str, note: str = "") -> str:
    lines = [_section(title)]
    if note:
        lines.append(f"-- {note}")
    lines.append("-- Generated by extract_schema.py. Do not edit by hand.")
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output",
        default=OUTPUT_DIR,
        help=f"directory to write into (default: {OUTPUT_DIR})",
    )
    parser.add_argument(
        "--keep-start-with",
        action="store_true",
        help="preserve live START WITH counters instead of normalising them to 1",
    )
    parser.add_argument(
        "--skip-counts",
        action="store_true",
        help="skip row counts (faster on large transactional tables)",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="write the files even when the capture is not rebuild-safe",
    )
    args = parser.parse_args()

    os.makedirs(args.output, exist_ok=True)
    keep = args.keep_start_with

    with get_connection() as connection:
        cursor = connection.cursor()
        applied = _configure_session(cursor)
        owner = _current_owner(cursor)
        print(f"Connected as {owner}")

        tables = _tables(cursor)
        sequences = _sequences(cursor)
        print(f"Found {len(tables)} tables, {len(sequences)} sequences")

        sequence_blocks = []
        for name, _ in sequences:
            ddl = _get_ddl(cursor, "SEQUENCE", name, owner, keep)
            if ddl:
                sequence_blocks.append(f"-- {name}\n{ddl}")

        table_blocks = []
        constraint_blocks = []
        foreign_key_blocks = []
        index_blocks = []
        trigger_blocks = []
        comment_blocks = []
        stats = []

        for table in tables:
            print(f"  {table}")
            ddl = _get_ddl(cursor, "TABLE", table, owner, keep)
            if ddl:
                table_blocks.append(f"-- {table}\n{ddl}")

            table_constraints = []
            for name in _constraints(cursor, table, ("P", "U", "C")):
                piece = _get_ddl(cursor, "CONSTRAINT", name, owner, keep)
                if piece:
                    table_constraints.append(piece)
            if table_constraints:
                constraint_blocks.append(f"-- {table}\n" + "\n".join(table_constraints))

            table_foreign_keys = []
            for name in _constraints(cursor, table, ("R",)):
                piece = _get_ddl(cursor, "REF_CONSTRAINT", name, owner, keep)
                if piece:
                    table_foreign_keys.append(piece)
            if table_foreign_keys:
                foreign_key_blocks.append(f"-- {table}\n" + "\n".join(table_foreign_keys))

            table_indexes = []
            for name in _plain_indexes(cursor, table):
                piece = _get_ddl(cursor, "INDEX", name, owner, keep)
                if piece:
                    table_indexes.append(piece)
            if table_indexes:
                index_blocks.append(f"-- {table}\n" + "\n".join(table_indexes))

            table_triggers = []
            for name in _triggers(cursor, table):
                piece = _get_ddl(cursor, "TRIGGER", name, owner, keep, terminate=False)
                if piece:
                    table_triggers.append(f"{piece}\n/")
            if table_triggers:
                trigger_blocks.append(f"-- {table}\n" + "\n\n".join(table_triggers))

            comments = _get_dependent_ddl(cursor, "COMMENT", table, owner, keep)
            if comments:
                comment_blocks.append(f"-- {table}\n{comments}")

            stats.append(
                {
                    "table": table,
                    "rows": None if args.skip_counts else _row_count(cursor, table),
                    "constraints": len(table_constraints),
                    "foreign_keys": len(table_foreign_keys),
                    "indexes": len(table_indexes),
                    "triggers": len(table_triggers),
                    "referenced": table.lower() in APP_TABLES,
                }
            )

        identity_marks = _identity_high_water(cursor)

    problems = _verify(applied, table_blocks)
    if problems and not args.force:
        print("\nCapture is not rebuild-safe:")
        for problem in problems:
            print(f"  ! {problem}")
        print("\nNothing was written. Re-run with --force to keep the output anyway.")
        raise SystemExit(1)

    out = args.output
    written = {
        "01_sequences.sql": _write(
            os.path.join(out, "01_sequences.sql"),
            _file_header("SEQUENCES"),
            sequence_blocks,
        ),
        "02_tables.sql": _write(
            os.path.join(out, "02_tables.sql"),
            _file_header(
                "TABLES",
                "Columns, defaults and NOT NULL only. Keys arrive in 03 and 04.",
            ),
            table_blocks,
        ),
        "03_constraints.sql": _write(
            os.path.join(out, "03_constraints.sql"),
            _file_header("PRIMARY, UNIQUE AND CHECK CONSTRAINTS"),
            constraint_blocks,
        ),
        "04_foreign_keys.sql": _write(
            os.path.join(out, "04_foreign_keys.sql"),
            _file_header(
                "FOREIGN KEYS",
                "Applied last so table creation order does not matter.",
            ),
            foreign_key_blocks,
        ),
        "05_indexes.sql": _write(
            os.path.join(out, "05_indexes.sql"),
            _file_header(
                "INDEXES",
                "Constraint-backing indexes are excluded; they come with 03.",
            ),
            index_blocks,
        ),
        "06_triggers.sql": _write(
            os.path.join(out, "06_triggers.sql"),
            _file_header("TRIGGERS"),
            trigger_blocks,
        ),
        "07_comments.sql": _write(
            os.path.join(out, "07_comments.sql"),
            _file_header("TABLE AND COLUMN COMMENTS"),
            comment_blocks,
        ),
    }

    rebuild = [
        "-- Rebuild the schema in dependency order.",
        "-- Generated by extract_schema.py. Do not edit by hand.",
        "--",
        "--     sqlplus <user>/<password>@<dsn> @rebuild.sql",
        "",
        "SET DEFINE OFF",
        "SET ECHO ON",
        "",
    ]
    rebuild += [f"@@{name}" for name in sorted(written)]
    rebuild += ["", "SET ECHO OFF", "SHOW ERRORS", "EXIT"]
    with open(os.path.join(out, "rebuild.sql"), "w", encoding="utf-8", newline="\n") as handle:
        handle.write("\n".join(rebuild) + "\n")

    _write_manifest(out, owner, stats, sequences, identity_marks, written, args)

    print()
    for name in sorted(written):
        print(f"  {name}: {written[name]} object group(s)")
    print(f"  rebuild.sql, README.md")
    print(f"\nWrote {len(written) + 2} files to {out}/")


def _write_manifest(out, owner, stats, sequences, identity_marks, written, args) -> None:
    captured = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
    total_rows = sum(s["rows"] or 0 for s in stats)
    referenced = sum(1 for s in stats if s["referenced"])

    lines = [
        "# Schema capture",
        "",
        "Generated by `extract_schema.py`. Do not edit by hand.",
        "",
        f"- Captured: {captured}",
        f"- Schema: `{owner}`",
        f"- Tables: {len(stats)} ({referenced} referenced by the backend)",
        f"- Sequences: {len(sequences)}",
    ]
    if not args.skip_counts:
        lines.append(f"- Total rows: {total_rows:,}")
    lines += [
        "",
        "The `.sql` files describe structure only. Live counter values are recorded",
        "below rather than baked into the DDL, so the files stay stable in git.",
        "",
        "## Tables",
        "",
        "`App` marks tables the FastAPI backend currently reads or writes.",
        "",
        "| Table | Rows | Cons | FK | Idx | Trg | App |",
        "| --- | ---: | ---: | ---: | ---: | ---: | :---: |",
    ]
    for s in sorted(stats, key=lambda r: r["table"].lower()):
        rows = "-" if s["rows"] is None else f"{s['rows']:,}"
        lines.append(
            f"| `{s['table']}` | {rows} | {s['constraints']} | {s['foreign_keys']} "
            f"| {s['indexes']} | {s['triggers']} | {'x' if s['referenced'] else ''} |"
        )

    missing = sorted(APP_TABLES - {s["table"].lower() for s in stats})
    if missing:
        lines += [
            "",
            "## Referenced but not found",
            "",
            "The backend names these tables but they are absent from the schema:",
            "",
        ]
        lines += [f"- `{name}`" for name in missing]

    lines += ["", "## Sequence high-water marks", ""]
    if sequences:
        lines += ["| Sequence | Next value |", "| --- | ---: |"]
        lines += [f"| `{name}` | {last:,} |" for name, last in sequences]
    else:
        lines.append("None.")

    lines += ["", "## Identity column high-water marks", ""]
    if identity_marks:
        lines += ["| Column | Next value |", "| --- | ---: |"]
        lines += [f"| `{key}` | {value:,} |" for key, value in sorted(identity_marks.items())]
    else:
        lines.append("None.")

    lines += [
        "",
        "## Files",
        "",
        "| File | Object groups |",
        "| --- | ---: |",
    ]
    lines += [f"| `{name}` | {written[name]} |" for name in sorted(written)]
    lines += [
        "",
        "Run `rebuild.sql` against an empty schema to recreate everything in order.",
        "",
    ]

    with open(os.path.join(out, "README.md"), "w", encoding="utf-8", newline="\n") as handle:
        handle.write("\n".join(lines))


if __name__ == "__main__":
    main()
