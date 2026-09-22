"""Add optional prepayment in rials to tally headers.

Run with the API stopped: python add_tally_prepayment.py
Existing rows retain NULL. This migration can be run again safely.
"""

from app.core.db import get_connection


def main() -> None:
    with get_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                """SELECT DATA_TYPE, DATA_PRECISION, DATA_SCALE
                   FROM USER_TAB_COLUMNS
                   WHERE TABLE_NAME = :table_name AND COLUMN_NAME = :column_name""",
                {"table_name": "FA_TALI_HEADER", "column_name": "PREPAYMENT"},
            )
            existing = cursor.fetchone()
            if existing is None:
                cursor.execute(
                    'ALTER TABLE "FA_TALI_HEADER" ADD ("PREPAYMENT" NUMBER(16, 0) '
                    'CHECK ("PREPAYMENT" BETWEEN 0 AND 9007199254740991))'
                )
                print("Added FA_TALI_HEADER.PREPAYMENT")
            elif existing != ("NUMBER", 16, 0):
                raise RuntimeError("PREPAYMENT exists with an unexpected type; review its definition.")
            else:
                print("FA_TALI_HEADER.PREPAYMENT already exists")
        connection.commit()


if __name__ == "__main__":
    main()
