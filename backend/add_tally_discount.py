"""Add optional discount (تخفیف) in rials to tally headers.

Mirrors add_tally_prepayment.py. The invoice deducts it after VAT, together
with PREPAYMENT: charges + VAT - prepayment - discount.

Run with the API stopped: python add_tally_discount.py
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
                {"table_name": "FA_TALI_HEADER", "column_name": "DISCOUNT"},
            )
            existing = cursor.fetchone()
            if existing is None:
                cursor.execute(
                    'ALTER TABLE "FA_TALI_HEADER" ADD ("DISCOUNT" NUMBER(16, 0) '
                    'CHECK ("DISCOUNT" BETWEEN 0 AND 9007199254740991))'
                )
                print("Added FA_TALI_HEADER.DISCOUNT")
            elif existing != ("NUMBER", 16, 0):
                raise RuntimeError("DISCOUNT exists with an unexpected type; review its definition.")
            else:
                print("FA_TALI_HEADER.DISCOUNT already exists")
        connection.commit()


if __name__ == "__main__":
    main()
