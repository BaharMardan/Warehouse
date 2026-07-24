"""Add the user-entered owner national ID to FA_TALI_HEADER.

This field belongs to a tally and is independent from FA_PRODUCT_OWNER.
Existing tally rows remain unchanged because the column is nullable.

Run once while the API is stopped:

    python add_tally_owner_national_code.py

The migration is idempotent and safe to run again.
"""

from app.core.db import get_connection


TABLE = "FA_TALI_HEADER"
COLUMN = "OWNER_NATIONAL_CODE"


def main() -> None:
    with get_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT DATA_TYPE, CHAR_LENGTH
                FROM USER_TAB_COLUMNS
                WHERE TABLE_NAME = :table_name
                  AND COLUMN_NAME = :column_name
                """,
                {"table_name": TABLE, "column_name": COLUMN},
            )
            existing = cursor.fetchone()

            if existing is None:
                cursor.execute(
                    f'ALTER TABLE "{TABLE}" '
                    f'ADD ("{COLUMN}" VARCHAR2(20 CHAR))'
                )
                print(f"OK  : added {TABLE}.{COLUMN} as VARCHAR2(20 CHAR)")
            else:
                data_type, char_length = existing
                if data_type not in {"VARCHAR2", "NVARCHAR2"}:
                    raise RuntimeError(
                        f"{TABLE}.{COLUMN} already exists as {data_type}; "
                        "review it before running this migration."
                    )
                if (char_length or 0) < 20:
                    cursor.execute(
                        f'ALTER TABLE "{TABLE}" '
                        f'MODIFY ("{COLUMN}" VARCHAR2(20 CHAR))'
                    )
                    print(
                        f"OK  : expanded {TABLE}.{COLUMN} "
                        "to VARCHAR2(20 CHAR)"
                    )
                else:
                    print(
                        f"SKIP: {TABLE}.{COLUMN} is already "
                        f"{data_type}({char_length})"
                    )

        connection.commit()


if __name__ == "__main__":
    main()
