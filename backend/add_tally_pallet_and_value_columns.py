"""Add pallet count and goods value to FA_TALI_DETAILES.

The two nullable columns back the «تعداد پالت» and «ارزش کالا» inputs on each
tally goods row. Existing rows remain valid and keep NULL for both values.

Run once while the API is stopped:

    python add_tally_pallet_and_value_columns.py

The migration is idempotent and safe to run again.
"""

from app.core.db import get_connection


TABLE = "FA_TALI_DETAILES"
COLUMNS = {
    "NUMBER_PALLET": "NUMBER(10)",
    "VALUE_KALA": "NUMBER(20, 2)",
}


def main() -> None:
    with get_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT COLUMN_NAME, DATA_TYPE, DATA_PRECISION, DATA_SCALE
                FROM USER_TAB_COLUMNS
                WHERE TABLE_NAME = :table_name
                  AND COLUMN_NAME IN ('NUMBER_PALLET', 'VALUE_KALA')
                """,
                {"table_name": TABLE},
            )
            existing = {row[0]: row[1:] for row in cursor.fetchall()}

            for column, definition in COLUMNS.items():
                if column in existing:
                    data_type, precision, scale = existing[column]
                    if data_type != "NUMBER":
                        raise RuntimeError(
                            f"{TABLE}.{column} already exists as {data_type}; "
                            "review it before running this migration."
                        )
                    print(
                        f"SKIP: {TABLE}.{column} is already "
                        f"NUMBER({precision}, {scale})"
                    )
                    continue

                cursor.execute(
                    f'ALTER TABLE "{TABLE}" ADD ("{column}" {definition})'
                )
                print(f"OK  : added {TABLE}.{column} as {definition}")

        connection.commit()


if __name__ == "__main__":
    main()
