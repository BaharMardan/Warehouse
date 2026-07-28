"""Add the selected Diamond time type to each Tally/Diamond junction.

Each row in ``fa_kala_diamound`` has two amounts:

* ``price_gher_edari`` for ``off_hours``
* ``price_holiday`` for ``holiday``

The junction previously stored only the catalog row id, so it could not remember
which amount the operator selected. This migration adds a nullable
``pricing_type`` column and backfills old rows to ``off_hours``. That preserves
the application's previous billing behaviour for every existing Tally.

Run while the backend is stopped:

    python add_diamound_pricing_type.py

The migration is idempotent and safe to run again.
"""

from app.core.db import get_connection


TABLE = "fa_tali_kala_diamound"
COLUMN = "pricing_type"


def main() -> None:
    with get_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT COUNT(*)
                FROM USER_TAB_COLUMNS
                WHERE TABLE_NAME = :table_name
                  AND COLUMN_NAME = :column_name
                """,
                {"table_name": TABLE, "column_name": COLUMN},
            )
            exists = cursor.fetchone()[0] > 0

            if exists:
                print(f'SKIP: "{TABLE}"."{COLUMN}" already exists')
            else:
                cursor.execute(
                    f'ALTER TABLE "{TABLE}" '
                    f'ADD ("{COLUMN}" VARCHAR2(20 CHAR))'
                )
                print(f'OK  : added "{TABLE}"."{COLUMN}"')

            cursor.execute(
                f'UPDATE "{TABLE}" '
                f'SET "{COLUMN}" = \'off_hours\' '
                f'WHERE "{COLUMN}" IS NULL'
            )
            print(
                "OK  : preserved previous behaviour for "
                f"{cursor.rowcount} existing row(s)"
            )

        connection.commit()


if __name__ == "__main__":
    main()
