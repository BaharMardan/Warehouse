"""Add the two optional tracking/procedure columns to FA_TALI_HEADER.

Run once with the API stopped:

    python add_tally_tracking_procedure_fields.py

The migration is repeat-safe. Existing tally rows remain unchanged and receive
NULL for both new fields.
"""

from app.core.db import get_connection


REQUESTED_TABLE = "FA_TALI_HEADER"
COLUMNS = {
    "TRACKING_NUMBER": 100,
    "CUSTOMS_PROCEDURE": 30,
}


def _quote(identifier: str) -> str:
    return '"' + identifier.replace('"', '""') + '"'


def _known_columns(cursor, table: str) -> dict[str, tuple[str, str, int, str]]:
    cursor.execute(
        """
        SELECT COLUMN_NAME, DATA_TYPE, CHAR_LENGTH, NULLABLE
          FROM USER_TAB_COLUMNS
         WHERE TABLE_NAME = :table_name
        """,
        {"table_name": table},
    )
    return {
        str(column).casefold(): (
            str(column),
            str(data_type),
            int(char_length or 0),
            str(nullable),
        )
        for column, data_type, char_length, nullable in cursor.fetchall()
    }


def main() -> None:
    changed = 0
    skipped = 0

    with get_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute("SELECT TABLE_NAME FROM USER_TABLES")
            tables = {
                str(row[0]).casefold(): str(row[0]) for row in cursor.fetchall()
            }
            table = tables.get(REQUESTED_TABLE.casefold())
            if table is None:
                raise RuntimeError(f"Table {REQUESTED_TABLE} does not exist")

            columns = _known_columns(cursor, table)
            for requested_column, required_length in COLUMNS.items():
                resolved = columns.get(requested_column.casefold())
                if resolved is None:
                    cursor.execute(
                        f"ALTER TABLE {_quote(table)} ADD "
                        f"({_quote(requested_column)} "
                        f"VARCHAR2({required_length} CHAR) NULL)"
                    )
                    print(f"OK  : added optional {table}.{requested_column}")
                    changed += 1
                    continue

                column, data_type, char_length, nullable = resolved
                if data_type not in {"VARCHAR2", "NVARCHAR2"}:
                    raise RuntimeError(
                        f"{table}.{column} exists as {data_type}; expected text"
                    )

                column_changed = False
                if char_length < required_length:
                    definition = (
                        f"NVARCHAR2({required_length})"
                        if data_type == "NVARCHAR2"
                        else f"VARCHAR2({required_length} CHAR)"
                    )
                    cursor.execute(
                        f"ALTER TABLE {_quote(table)} MODIFY "
                        f"({_quote(column)} {definition})"
                    )
                    print(f"OK  : expanded {table}.{column} to {definition}")
                    changed += 1
                    column_changed = True

                if nullable != "Y":
                    cursor.execute(
                        f"ALTER TABLE {_quote(table)} MODIFY ({_quote(column)} NULL)"
                    )
                    print(f"OK  : made {table}.{column} optional")
                    changed += 1
                    column_changed = True

                if not column_changed:
                    print(f"SKIP: {table}.{column} is already ready")
                    skipped += 1

        connection.commit()

    print(f"done — changed={changed}, skipped={skipped}")


if __name__ == "__main__":
    main()
