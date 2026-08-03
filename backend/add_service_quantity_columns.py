"""Add an optional quantity column to every tally service junction.

Historically only ``fa_tali_kala_other_service`` stored ``NUMBER_SERVICE``.
The tally UI now exposes the same optional quantity field for demand, strip and
stuffing, empty-carrier night stop, and vehicle/yard entry rows.  This migration
adds the matching Oracle column to those four junction tables.

The migration is idempotent and resolves quoted table names case-insensitively.
Run it with the API stopped:

    python add_service_quantity_columns.py
"""

from app.core.db import get_connection


TABLES = (
    "fa_tali_kala_diamound",
    "fa_tali_kala_strip",
    "fa_tali_kala_time_stop_vehicle",
    "fa_tali_kala_vehicle_enter_price",
)
COLUMN = "NUMBER_SERVICE"


def _quote(identifier: str) -> str:
    return '"' + identifier.replace('"', '""') + '"'


def main() -> None:
    added = 0
    skipped = 0
    failed: list[str] = []

    with get_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute("SELECT TABLE_NAME FROM USER_TABLES")
            known_tables = {
                str(row[0]).casefold(): str(row[0]) for row in cursor.fetchall()
            }

            for requested_table in TABLES:
                table = known_tables.get(requested_table.casefold())
                if table is None:
                    print(f"FAIL: table {requested_table} does not exist")
                    failed.append(requested_table)
                    continue

                cursor.execute(
                    """
                    SELECT COLUMN_NAME
                      FROM USER_TAB_COLUMNS
                     WHERE TABLE_NAME = :table_name
                    """,
                    {"table_name": table},
                )
                columns = {str(row[0]).casefold() for row in cursor.fetchall()}
                if COLUMN.casefold() in columns:
                    print(f"SKIP: {table}.{COLUMN} already exists")
                    skipped += 1
                    continue

                try:
                    cursor.execute(
                        f"ALTER TABLE {_quote(table)} "
                        f"ADD ({_quote(COLUMN)} NUMBER NULL)"
                    )
                    print(f"OK  : added optional {table}.{COLUMN}")
                    added += 1
                except Exception as exc:
                    print(f"FAIL: {table}.{COLUMN}: {exc}")
                    failed.append(f"{table}.{COLUMN}")

        if failed:
            connection.rollback()
        else:
            connection.commit()

    print(f"Summary: added={added}, skipped={skipped}, failed={len(failed)}")
    if failed:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
