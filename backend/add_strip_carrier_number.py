"""Add the carrier-number link to strip/stuffing service rows.

Each strip/stuffing entry now records the carrier selected from the tally's goods
rows.  The migration is idempotent and keeps existing service entries valid.

Run with the API stopped:

    python add_strip_carrier_number.py
"""
from app.core.db import get_connection


TABLE = "fa_tali_kala_strip"
COLUMN = "number_hamel"


def _quote(identifier: str) -> str:
    return '"' + identifier.replace('"', '""') + '"'


def main() -> None:
    with get_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute("SELECT TABLE_NAME FROM USER_TABLES")
            tables = {str(row[0]).casefold(): str(row[0]) for row in cursor.fetchall()}
            table = tables.get(TABLE.casefold())
            if table is None:
                raise RuntimeError(f"Table {TABLE} does not exist")

            cursor.execute(
                "SELECT COLUMN_NAME FROM USER_TAB_COLUMNS WHERE TABLE_NAME = :table_name",
                {"table_name": table},
            )
            columns = {str(row[0]).casefold() for row in cursor.fetchall()}
            if COLUMN.casefold() in columns:
                print(f"SKIP: {table}.{COLUMN} already exists")
                return

            cursor.execute(
                f"ALTER TABLE {_quote(table)} ADD ({_quote(COLUMN)} VARCHAR2(150 CHAR) NULL)"
            )
            connection.commit()
            print(f"OK: added {table}.{COLUMN}")


if __name__ == "__main__":
    main()
