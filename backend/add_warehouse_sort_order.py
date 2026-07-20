"""Add + populate FA_ANBAR.SORT_ORDER to control the warehouse dropdown order.

The «انبار» dropdown must read:  6, 7, 8, 9, 10, 11, هنگار, بارانداز  — independent of
the primary key. This adds a SORT_ORDER column (a standard lookup display-order
column) and sets it on the 8 existing active warehouses, matched BY NAME.

The /anbar list endpoint orders by this column (crud factory order_by="SORT_ORDER",
with id_anbar as a tiebreaker), so the dropdown follows SORT_ORDER everywhere it's used
(tally form + receipt form + any future screen).

NON-DESTRUCTIVE
    * No rows deleted, no ids changed. Existing tally lines / ghabz headers that
      reference a warehouse are completely untouched.
IDEMPOTENT
    * Re-running is safe: the ALTER is skipped if the column already exists
      (ORA-01430), and the UPDATEs are keyed by name.
DATABASE-AGNOSTIC
    * On PostgreSQL, replace the ALTER with:  ALTER TABLE fa_anbar ADD COLUMN sort_order INTEGER;
      Everything else is standard SQL.

Run (backend env, same as run_ddl.py):
    python add_warehouse_sort_order.py
"""
from app.core.db import get_connection

# name_anbar -> display position (this list IS the ordering; edit here to reorder)
ORDER = {"6": 1, "7": 2, "8": 3, "9": 4, "10": 5, "11": 6, "هنگار": 7, "بارانداز": 8}


def main():
    with get_connection() as conn:
        cur = conn.cursor()

        # 1) add the column if it isn't there yet (ORA-01430 = column already exists)
        try:
            cur.execute("ALTER TABLE FA_ANBAR ADD (SORT_ORDER NUMBER)")
            print("added column FA_ANBAR.SORT_ORDER")
        except Exception as exc:
            if "ORA-01430" in str(exc):
                print("FA_ANBAR.SORT_ORDER already exists — skipping ALTER")
            else:
                raise

        # 2) set the display order on the active warehouses, matched by name
        for name, pos in ORDER.items():
            cur.execute(
                "UPDATE FA_ANBAR SET sort_order = :pos "
                "WHERE name_anbar = :name AND is_deleted = 'no'",
                {"pos": pos, "name": name},
            )
            flag = "" if cur.rowcount == 1 else f"  <-- matched {cur.rowcount} rows"
            print(f"SORT_ORDER {pos}  ->  {name}{flag}")

        conn.commit()

        # 3) confirm exactly what the dropdown will now show
        cur.execute(
            "SELECT id_anbar, name_anbar, sort_order FROM FA_ANBAR "
            "WHERE is_deleted = 'no' ORDER BY sort_order, id_anbar"
        )
        print("\nDropdown order (sort_order | id_anbar -> name_anbar):")
        for r in cur.fetchall():
            so = "NULL" if r[2] is None else int(r[2])
            print(f"  {str(so):>4}  |  {r[0]:>4}  ->  {r[1]}")


if __name__ == "__main__":
    main()