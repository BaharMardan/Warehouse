"""Drop the ``_0`` suffix from existing master receipt numbers.

Master receipts (قبض انبار مادر) used to print as ``1405_1503_0``. They now
print as ``1405_1503``: a number without a sequence suffix is the master, so an
operator can tell it apart from the children (``1405_1503_1``, ...) at a glance.

GHABZ_SEQ stays 0 -- only the printed GHABZ_NUMBER string changes. The
allocator looks masters up by GHABZ_NUMBER (UQ_FA_GHABZ_NUMBER is the
constraint that actually collides), so rows issued before this change must be
renamed or re-issuing a master would insert a second row instead of reviving
the existing one.

Only rows marked IS_MASTER = 'yes' with a trailing ``_0`` are touched; a child
receipt can never end in ``_0`` because children start at sequence 1.

Run once with the API stopped (safe to re-run):

    python migrate_ghabz_master_number_suffix.py
"""

from app.core.db import get_connection


SELECT_SQL = """
SELECT "ID_ghabz", "GHABZ_NUMBER"
FROM "fa_ghabz_anbar_header"
WHERE NVL("IS_MASTER", 'no') = 'yes'
  AND "GHABZ_NUMBER" LIKE '%\\_0' ESCAPE '\\'
ORDER BY "ID_ghabz"
"""

UPDATE_SQL = """
UPDATE "fa_ghabz_anbar_header"
SET "GHABZ_NUMBER" = :new_number
WHERE "ID_ghabz" = :id_ghabz
"""


def main() -> None:
    with get_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute(SELECT_SQL)
            rows = cursor.fetchall()
            if not rows:
                print("No master receipts with a _0 suffix; nothing to do.")
                return

            for id_ghabz, number in rows:
                new_number = number[: -len("_0")]
                cursor.execute(
                    UPDATE_SQL, {"new_number": new_number, "id_ghabz": id_ghabz}
                )
                print(f"  {number} -> {new_number}")

        conn.commit()
        print(f"Renamed {len(rows)} master receipt(s).")


if __name__ == "__main__":
    main()
