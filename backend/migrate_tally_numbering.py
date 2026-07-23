"""Migrate tally numbers to the automatic ``<Jalali year>-<number>`` format.

Run once while the API is stopped:

    python migrate_tally_numbering.py

The script is safe to re-run. It preserves existing tally/receipt values,
converts their number columns to VARCHAR2, creates the yearly counter table,
adds the tally-number uniqueness constraint, and creates/repairs the ID_TALI
sequence above the current maximum ID.
"""

from app.core.db import get_connection


TALLY_TABLE = "FA_TALI_HEADER"
TALLY_NUMBER_COLUMN = "TALI_NUMBER"
RECEIPT_TABLE = "fa_ghabz_anbar_header"
RECEIPT_TALLY_NUMBER_COLUMN = "NUMBER_tali"
COUNTER_TABLE = "FA_TALI_NUMBER_COUNTER"
SEQUENCE_NAME = "SEQ_FA_TALI_HEADER"
UNIQUE_CONSTRAINT = "UQ_FA_TALI_NUMBER"


def _q(identifier: str) -> str:
    return f'"{identifier}"'


def _column_info(cursor, table: str, column: str):
    cursor.execute(
        """
        SELECT DATA_TYPE, CHAR_LENGTH, NULLABLE
        FROM USER_TAB_COLUMNS
        WHERE TABLE_NAME = :table_name AND COLUMN_NAME = :column_name
        """,
        {"table_name": table, "column_name": column},
    )
    return cursor.fetchone()


def _constraints_for_column(
    cursor,
    table: str,
    column: str,
) -> list[tuple[str, str, str]]:
    cursor.execute(
        """
        SELECT DISTINCT c.CONSTRAINT_NAME, c.CONSTRAINT_TYPE, c.GENERATED
        FROM USER_CONSTRAINTS c
        JOIN USER_CONS_COLUMNS cc
          ON cc.CONSTRAINT_NAME = c.CONSTRAINT_NAME
        WHERE c.TABLE_NAME = :table_name
          AND cc.COLUMN_NAME = :column_name
        """,
        {"table_name": table, "column_name": column},
    )
    return list(cursor.fetchall())


def _constraint_columns(cursor, table: str, constraint: str) -> list[str]:
    cursor.execute(
        """
        SELECT COLUMN_NAME
        FROM USER_CONS_COLUMNS
        WHERE TABLE_NAME = :table_name
          AND CONSTRAINT_NAME = :constraint_name
        ORDER BY POSITION
        """,
        {"table_name": table, "constraint_name": constraint},
    )
    return [row[0] for row in cursor.fetchall()]


def _single_column_unique_constraints(
    cursor,
    table: str,
    column: str,
) -> list[str]:
    return [
        name
        for name, constraint_type, _generated in _constraints_for_column(
            cursor,
            table,
            column,
        )
        if constraint_type == "U"
        and _constraint_columns(cursor, table, name) == [column]
    ]


def _convert_column_to_text(cursor, connection, table: str, column: str) -> None:
    info = _column_info(cursor, table, column)
    if info is None:
        raise RuntimeError(f"{table}.{column} was not found")

    data_type, char_length, nullable = info
    if data_type in {"VARCHAR2", "NVARCHAR2"}:
        if (char_length or 0) < 20:
            cursor.execute(
                f"ALTER TABLE {_q(table)} "
                f"MODIFY ({_q(column)} VARCHAR2(20 CHAR))"
            )
            print(f"OK  : expanded {table}.{column} to VARCHAR2(20 CHAR)")
        else:
            print(f"SKIP: {table}.{column} is already {data_type}({char_length})")
        return

    constraints = _constraints_for_column(cursor, table, column)
    unique_constraints = _single_column_unique_constraints(cursor, table, column)
    # Oracle represents a NOT NULL declaration as a generated CHECK
    # constraint. It is safe to drop with the old column because nullable=N is
    # captured above and reapplied after the rename.
    #
    # A single-column UNIQUE constraint can also be preserved safely: drop it
    # immediately before replacing the column, then recreate it with the same
    # name immediately after the rename. Primary keys, foreign keys,
    # user-defined checks, and multi-column unique constraints still stop the
    # migration for manual review.
    blocking_constraints = [
        name
        for name, constraint_type, generated in constraints
        if not (
            nullable == "N"
            and constraint_type == "C"
            and generated == "GENERATED NAME"
        )
        and name not in unique_constraints
    ]
    if blocking_constraints:
        joined = ", ".join(blocking_constraints)
        raise RuntimeError(
            f"{table}.{column} has constraint(s) {joined}. "
            "Review them before converting the column."
        )

    temp_column = f"{column}_TMP"
    if _column_info(cursor, table, temp_column) is not None:
        cursor.execute(
            f"ALTER TABLE {_q(table)} DROP COLUMN {_q(temp_column)}"
        )
        print(f"INFO: removed leftover {table}.{temp_column}")

    cursor.execute(
        f"ALTER TABLE {_q(table)} "
        f"ADD ({_q(temp_column)} VARCHAR2(20 CHAR))"
    )
    cursor.execute(
        f"UPDATE {_q(table)} "
        f"SET {_q(temp_column)} = TO_CHAR({_q(column)}) "
        f"WHERE {_q(column)} IS NOT NULL"
    )
    copied = cursor.rowcount
    connection.commit()

    for constraint_name in unique_constraints:
        cursor.execute(
            f"ALTER TABLE {_q(table)} "
            f"DROP CONSTRAINT {_q(constraint_name)}"
        )
        print(
            f"INFO: temporarily removed unique constraint "
            f"{constraint_name}"
        )

    cursor.execute(f"ALTER TABLE {_q(table)} DROP COLUMN {_q(column)}")
    cursor.execute(
        f"ALTER TABLE {_q(table)} "
        f"RENAME COLUMN {_q(temp_column)} TO {_q(column)}"
    )
    if nullable == "N":
        cursor.execute(
            f"ALTER TABLE {_q(table)} MODIFY ({_q(column)} NOT NULL)"
        )
    for constraint_name in unique_constraints:
        cursor.execute(
            f"ALTER TABLE {_q(table)} "
            f"ADD CONSTRAINT {_q(constraint_name)} "
            f"UNIQUE ({_q(column)})"
        )
        print(f"OK  : restored unique constraint {constraint_name}")
    print(
        f"OK  : converted {table}.{column} to VARCHAR2(20 CHAR); "
        f"preserved {copied} value(s)"
    )


def _create_counter_table(cursor) -> None:
    cursor.execute(
        "SELECT COUNT(*) FROM USER_TABLES WHERE TABLE_NAME = :table_name",
        {"table_name": COUNTER_TABLE},
    )
    if cursor.fetchone()[0]:
        print(f"SKIP: {COUNTER_TABLE} already exists")
        return

    cursor.execute(
        f"""
        CREATE TABLE {_q(COUNTER_TABLE)} (
            "JALALI_YEAR" NUMBER(4) NOT NULL,
            "LAST_NUMBER" NUMBER NOT NULL,
            CONSTRAINT "PK_FA_TALI_NUMBER_COUNTER" PRIMARY KEY ("JALALI_YEAR"),
            CONSTRAINT "CK_FA_TALI_COUNTER_POSITIVE" CHECK ("LAST_NUMBER" >= 0)
        )
        """
    )
    print(f"OK  : created {COUNTER_TABLE}")


def _check_duplicates(cursor) -> None:
    cursor.execute(
        f"""
        SELECT {_q(TALLY_NUMBER_COLUMN)}, COUNT(*)
        FROM {_q(TALLY_TABLE)}
        WHERE {_q(TALLY_NUMBER_COLUMN)} IS NOT NULL
        GROUP BY {_q(TALLY_NUMBER_COLUMN)}
        HAVING COUNT(*) > 1
        """
    )
    duplicates = cursor.fetchall()
    if duplicates:
        preview = ", ".join(f"{value} ({count}x)" for value, count in duplicates[:10])
        raise RuntimeError(
            "Duplicate existing tally numbers must be resolved before adding "
            f"the unique constraint: {preview}"
        )


def _create_unique_constraint(cursor) -> None:
    existing = _single_column_unique_constraints(
        cursor,
        TALLY_TABLE,
        TALLY_NUMBER_COLUMN,
    )
    if existing:
        print(
            "SKIP: tally number is already protected by unique constraint "
            + ", ".join(existing)
        )
        return

    cursor.execute(
        """
        SELECT COUNT(*)
        FROM USER_CONSTRAINTS
        WHERE CONSTRAINT_NAME = :constraint_name
        """,
        {"constraint_name": UNIQUE_CONSTRAINT},
    )
    if cursor.fetchone()[0]:
        print(f"SKIP: {UNIQUE_CONSTRAINT} already exists")
        return

    _check_duplicates(cursor)
    cursor.execute(
        f"ALTER TABLE {_q(TALLY_TABLE)} "
        f"ADD CONSTRAINT {_q(UNIQUE_CONSTRAINT)} "
        f"UNIQUE ({_q(TALLY_NUMBER_COLUMN)})"
    )
    print(f"OK  : created {UNIQUE_CONSTRAINT}")


def _backfill_counters(cursor) -> None:
    cursor.execute(
        f"""
        SELECT {_q(TALLY_NUMBER_COLUMN)}
        FROM {_q(TALLY_TABLE)}
        WHERE REGEXP_LIKE({_q(TALLY_NUMBER_COLUMN)}, '^[0-9]{{4}}-[0-9]+$')
        """
    )
    maximum_by_year: dict[int, int] = {}
    for (value,) in cursor.fetchall():
        year_text, number_text = value.split("-", 1)
        year, number = int(year_text), int(number_text)
        maximum_by_year[year] = max(maximum_by_year.get(year, 0), number)

    merge_sql = f"""
    MERGE INTO {_q(COUNTER_TABLE)} counter
    USING (
        SELECT :jalali_year AS "JALALI_YEAR", :last_number AS "LAST_NUMBER"
        FROM DUAL
    ) source
    ON (counter."JALALI_YEAR" = source."JALALI_YEAR")
    WHEN MATCHED THEN UPDATE SET
        counter."LAST_NUMBER" =
            GREATEST(counter."LAST_NUMBER", source."LAST_NUMBER")
    WHEN NOT MATCHED THEN INSERT ("JALALI_YEAR", "LAST_NUMBER")
        VALUES (source."JALALI_YEAR", source."LAST_NUMBER")
    """
    for year, last_number in sorted(maximum_by_year.items()):
        cursor.execute(
            merge_sql,
            {"jalali_year": year, "last_number": last_number},
        )
        print(f"OK  : counter {year} starts after {last_number}")

    if not maximum_by_year:
        print("INFO: no formatted existing tally numbers needed counter backfill")


def _ensure_sequence(cursor) -> None:
    cursor.execute(
        f"SELECT NVL(MAX({_q('ID_TALI')}), 0) FROM {_q(TALLY_TABLE)}"
    )
    next_required = int(cursor.fetchone()[0]) + 1

    cursor.execute(
        """
        SELECT COUNT(*)
        FROM USER_SEQUENCES
        WHERE SEQUENCE_NAME = :sequence_name
        """,
        {"sequence_name": SEQUENCE_NAME},
    )
    if cursor.fetchone()[0] == 0:
        cursor.execute(
            f"CREATE SEQUENCE {_q(SEQUENCE_NAME)} "
            f"START WITH {next_required} INCREMENT BY 1 NOCACHE NOCYCLE"
        )
        print(f"OK  : created {SEQUENCE_NAME} starting at {next_required}")
        return

    cursor.execute(f"SELECT {_q(SEQUENCE_NAME)}.NEXTVAL FROM DUAL")
    current = int(cursor.fetchone()[0])
    if current >= next_required:
        print(f"SKIP: {SEQUENCE_NAME} is already safe (used {current})")
        return

    # NEXTVAL above consumed `current`. Leave the next normal NEXTVAL exactly at
    # max(ID_TALI)+1. If it is already one step away, no temporary increment is
    # needed.
    jump = next_required - current
    if jump > 1:
        cursor.execute(
            f"ALTER SEQUENCE {_q(SEQUENCE_NAME)} INCREMENT BY {jump - 1}"
        )
        cursor.execute(f"SELECT {_q(SEQUENCE_NAME)}.NEXTVAL FROM DUAL")
        cursor.fetchone()
        cursor.execute(f"ALTER SEQUENCE {_q(SEQUENCE_NAME)} INCREMENT BY 1")
    print(f"OK  : advanced {SEQUENCE_NAME} to {next_required}")


def main() -> None:
    with get_connection() as connection:
        cursor = connection.cursor()
        try:
            _convert_column_to_text(
                cursor,
                connection,
                TALLY_TABLE,
                TALLY_NUMBER_COLUMN,
            )
            _convert_column_to_text(
                cursor,
                connection,
                RECEIPT_TABLE,
                RECEIPT_TALLY_NUMBER_COLUMN,
            )
            _create_counter_table(cursor)
            _create_unique_constraint(cursor)
            _backfill_counters(cursor)
            _ensure_sequence(cursor)
            connection.commit()
        except Exception:
            connection.rollback()
            raise

        cursor.execute(
            f"""
            SELECT DATA_TYPE, CHAR_LENGTH
            FROM USER_TAB_COLUMNS
            WHERE TABLE_NAME = :table_name AND COLUMN_NAME = :column_name
            """,
            {
                "table_name": TALLY_TABLE,
                "column_name": TALLY_NUMBER_COLUMN,
            },
        )
        data_type, char_length = cursor.fetchone()
        print(
            f"done — {TALLY_TABLE}.{TALLY_NUMBER_COLUMN} is "
            f"{data_type}({char_length})"
        )


if __name__ == "__main__":
    main()
