"""Normalize the warehouse name «هانگار» in lookup and existing tally rows.

This migration fixes historical spelling variants in both places where the
warehouse name is used:

* FA_ANBAR.NAME_ANBAR, which supplies the «انبار» dropdown.
* FA_TALI_DETAILES.ZARIB_MAHAL, which stores the «ضریب محل» label.

The script is idempotent: running it again leaves already-correct values
unchanged. No rows or foreign-key identifiers are deleted or replaced.

Run from the backend directory:
    python normalize_hangar_names.py
"""
from app.core.db import get_connection


WAREHOUSE_VARIANTS = ("تانگارد", "تنگارد", "هنگار", "هانگارد")
LOCATION_VARIANTS = (
    "انبارداری تانگارد",
    "انبارداری تنگارد",
    "انبارداری هنگار",
    "انبارداری هانگارد",
)


def main() -> None:
    with get_connection() as conn:
        cur = conn.cursor()

        warehouse_binds = {
            f"warehouse_{index}": value
            for index, value in enumerate(WAREHOUSE_VARIANTS)
        }
        warehouse_placeholders = ", ".join(
            f":warehouse_{index}" for index in range(len(WAREHOUSE_VARIANTS))
        )
        cur.execute(
            f"""
            UPDATE FA_ANBAR
               SET NAME_ANBAR = :correct_warehouse
             WHERE TRIM(NAME_ANBAR) IN ({warehouse_placeholders})
            """,
            {"correct_warehouse": "هانگار", **warehouse_binds},
        )
        warehouse_count = cur.rowcount

        location_binds = {
            f"location_{index}": value
            for index, value in enumerate(LOCATION_VARIANTS)
        }
        location_placeholders = ", ".join(
            f":location_{index}" for index in range(len(LOCATION_VARIANTS))
        )
        cur.execute(
            f"""
            UPDATE FA_TALI_DETAILES
               SET ZARIB_MAHAL = :correct_location
             WHERE TRIM(ZARIB_MAHAL) IN ({location_placeholders})
            """,
            {"correct_location": "انبارداری هانگار", **location_binds},
        )
        location_count = cur.rowcount

        conn.commit()
        print(f"FA_ANBAR names corrected: {warehouse_count}")
        print(f"FA_TALI_DETAILES location labels corrected: {location_count}")
        print("Done. The canonical spelling is «هانگار».")


if __name__ == "__main__":
    main()
