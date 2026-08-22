"""
Prepare per-tally قبض انبار numbering and tally-sourced print fields.

Receipt number format:

    <jalali year>_<tally number>_<sequence>

Example:

    1405_866_1

The Jalali year comes from the parent tally.
The sequence restarts from 1 for each tally.

Legacy number_ghabz is NOT changed.
It contains old APEX-era receipt numbers.

Added columns:

HEADER:
    GHABZ_NUMBER
    GHABZ_SEQ
    TRACKING_NUMBER

DETAILS:
    HSCODE
    ID_TALI_DETAILS

Indexes:

    UQ_FA_GHABZ_NUMBER
        Unique printed receipt number

    UQ_FA_GHABZ_TALI_SEQ
        Conditional unique index:
        prevents duplicate new sequences while preserving
        legacy duplicated NULL/old data.

Run:

    python migrate_ghabz_numbering.py
"""

from app.core.db import get_connection


HEADER_TABLE = "fa_ghabz_anbar_header"
DETAILS_TABLE = "FA_ghabz_anbar_DETAILES"

NUMBER_CONSTRAINT = "UQ_FA_GHABZ_NUMBER"
SEQUENCE_INDEX = "UQ_FA_GHABZ_TALI_SEQ"


COLUMNS = {
    HEADER_TABLE: {
        "GHABZ_NUMBER": ("VARCHAR2(30 CHAR)", 30),
        "GHABZ_SEQ": ("NUMBER", 0),
        "TRACKING_NUMBER": ("VARCHAR2(100 CHAR)", 100),
    },
    DETAILS_TABLE: {
        "HSCODE": ("VARCHAR2(250 CHAR)", 250),
        "ID_TALI_DETAILS": ("NUMBER", 0),
    },
}


def _q(identifier: str) -> str:
    return '"' + identifier.replace('"', '""') + '"'


def _resolve_table(cursor, requested: str) -> str:
    """
    Oracle quoted tables are case sensitive.
    Match existing table names case-insensitively.
    """

    cursor.execute(
        """
        SELECT TABLE_NAME
        FROM USER_TABLES
        """
    )

    known = {
        str(row[0]).casefold(): str(row[0])
        for row in cursor.fetchall()
    }

    table = known.get(requested.casefold())

    if table is None:
        raise RuntimeError(
            f"Table {requested} does not exist"
        )

    return table


def _known_columns(cursor, table: str):

    cursor.execute(
        """
        SELECT COLUMN_NAME,
               DATA_TYPE,
               CHAR_LENGTH
        FROM USER_TAB_COLUMNS
        WHERE TABLE_NAME = :table_name
        """,
        {
            "table_name": table
        }
    )

    return {
        str(name).casefold():
        (
            str(name),
            str(data_type),
            int(length or 0)
        )
        for name, data_type, length in cursor.fetchall()
    }


def _add_columns(cursor, requested_table):

    table = _resolve_table(cursor, requested_table)

    existing = _known_columns(cursor, table)

    changed = 0
    skipped = 0

    for column, (definition, required_length) in COLUMNS[requested_table].items():

        found = existing.get(column.casefold())

        if found is None:

            cursor.execute(
                f"""
                ALTER TABLE {_q(table)}
                ADD (
                    {_q(column)}
                    {definition}
                    NULL
                )
                """
            )

            print(
                f"OK  : added {table}.{column} {definition}"
            )

            changed += 1
            continue


        actual_name, data_type, char_length = found

        is_text = required_length > 0


        if is_text and data_type not in (
            "VARCHAR2",
            "NVARCHAR2"
        ):
            raise RuntimeError(
                f"{table}.{actual_name} is {data_type}, expected text"
            )


        if not is_text and data_type != "NUMBER":

            raise RuntimeError(
                f"{table}.{actual_name} is {data_type}, expected NUMBER"
            )


        if is_text and char_length < required_length:

            cursor.execute(
                f"""
                ALTER TABLE {_q(table)}
                MODIFY (
                    {_q(actual_name)}
                    VARCHAR2({required_length} CHAR)
                )
                """
            )

            print(
                f"OK  : widened {table}.{actual_name}"
            )

            changed += 1

        else:

            print(
                f"SKIP: {table}.{actual_name} already ready"
            )

            skipped += 1


    return changed, skipped



def _constraint_exists(cursor, name):

    cursor.execute(
        """
        SELECT COUNT(*)
        FROM USER_CONSTRAINTS
        WHERE CONSTRAINT_NAME = :name
        """,
        {
            "name": name
        }
    )

    return cursor.fetchone()[0] > 0



def _index_exists(cursor, name):

    cursor.execute(
        """
        SELECT COUNT(*)
        FROM USER_INDEXES
        WHERE INDEX_NAME = :name
        """,
        {
            "name": name
        }
    )

    return cursor.fetchone()[0] > 0



def _add_unique_number_constraint(cursor):

    if _constraint_exists(
        cursor,
        NUMBER_CONSTRAINT
    ):

        print(
            f"SKIP: constraint {NUMBER_CONSTRAINT} already exists"
        )

        return 0


    table = _resolve_table(
        cursor,
        HEADER_TABLE
    )


    cursor.execute(
        f"""
        ALTER TABLE {_q(table)}
        ADD CONSTRAINT {_q(NUMBER_CONSTRAINT)}
        UNIQUE (GHABZ_NUMBER)
        ENABLE
        """
    )


    print(
        f"OK  : added {NUMBER_CONSTRAINT}"
    )

    return 1



def _add_sequence_index(cursor):

    """
    Do NOT use UNIQUE(TALI_ID, GHABZ_SEQ)

    Legacy قبض records contain duplicates.

    This index only applies when GHABZ_SEQ exists.
    """

    if _index_exists(
        cursor,
        SEQUENCE_INDEX
    ):

        print(
            f"SKIP: index {SEQUENCE_INDEX} already exists"
        )

        return 0


    table = _resolve_table(
        cursor,
        HEADER_TABLE
    )


    cursor.execute(
        f"""
        CREATE UNIQUE INDEX {_q(SEQUENCE_INDEX)}
        ON {_q(table)}
        (
            CASE
                WHEN GHABZ_SEQ IS NOT NULL
                THEN TALI_ID
            END,

            CASE
                WHEN GHABZ_SEQ IS NOT NULL
                THEN GHABZ_SEQ
            END
        )
        """
    )


    print(
        f"OK  : added index {SEQUENCE_INDEX}"
    )

    return 1



def main():

    changed = 0
    skipped = 0


    with get_connection() as connection:

        with connection.cursor() as cursor:


            for table in (
                HEADER_TABLE,
                DETAILS_TABLE
            ):

                added, kept = _add_columns(
                    cursor,
                    table
                )

                changed += added
                skipped += kept



            changed += _add_unique_number_constraint(
                cursor
            )


            changed += _add_sequence_index(
                cursor
            )


        connection.commit()


    print(
        f"done — changed={changed}, skipped={skipped}"
    )



if __name__ == "__main__":
    main()