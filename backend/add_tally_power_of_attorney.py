"""Add power-of-attorney fields to tally headers.

Run once in the backend environment that has Oracle access:

    python add_tally_power_of_attorney.py
"""

from app.core.db import get_connection


TABLE = "FA_TALI_HEADER"
COLUMNS = {
    "HAS_POWER_OF_ATTORNEY": "VARCHAR2(3 CHAR)",
    "POWER_OF_ATTORNEY_VALIDITY": "VARCHAR2(250 CHAR)",
}


def main() -> None:
    with get_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT COLUMN_NAME FROM USER_TAB_COLUMNS WHERE TABLE_NAME = :table_name",
                {"table_name": TABLE},
            )
            existing = {str(row[0]).upper() for row in cursor.fetchall()}
            for column, definition in COLUMNS.items():
                if column in existing:
                    print(f"SKIP: {TABLE}.{column} already exists")
                    continue
                cursor.execute(f'ALTER TABLE "{TABLE}" ADD ("{column}" {definition} NULL)')
                print(f"OK: added {TABLE}.{column}")
        connection.commit()


if __name__ == "__main__":
    main()
