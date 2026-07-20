"""Prune قیمت کالا down to Table 1 — soft-delete any active row whose code is NOT a
Table-1 group (101–124). This removes the leftovers seen on the page (127, 501–509, …).

SOFT-delete (IS_DELETED='yes'), so it's reversible and INVOICE-SAFE: the invoice's
storage join is a LEFT JOIN with no IS_DELETED filter, so any tally line that still
references one of these rows keeps resolving. They just disappear from the قیمت کالا
list and the «گروه قیمت انبار» picker (both filter IS_DELETED='no').

IDEMPOTENT: re-running is a no-op once the leftovers are gone.

Run (backend env, same as run_ddl.py):
    python prune_kala_price_to_table1.py
"""
from app.core.db import get_connection

# The 24 Table-1 group codes to KEEP.
KEEP = [str(c) for c in range(101, 125)]


def main():
    with get_connection() as conn:
        cur = conn.cursor()

        placeholders = ", ".join(f":c{i}" for i in range(len(KEEP)))
        binds = {f"c{i}": code for i, code in enumerate(KEEP)}

        # show what will be removed first
        cur.execute(
            f'SELECT CODE, "goods_group" FROM "fa_kala_price" '
            f"WHERE IS_DELETED = 'no' AND CODE NOT IN ({placeholders}) ORDER BY CODE",
            binds,
        )
        doomed = cur.fetchall()
        if not doomed:
            print("Nothing to prune — قیمت کالا already matches Table 1.")
            return
        print("Soft-deleting these non-Table-1 rows:")
        for code, group in doomed:
            print(f"  code {code}  ({'—' if group is None else str(group)[:30]})")

        cur.execute(
            f'UPDATE "fa_kala_price" '
            f"SET IS_DELETED = 'yes', MODIFY_AT = SYSDATE, MODIFY_BY = 1 "
            f"WHERE IS_DELETED = 'no' AND CODE NOT IN ({placeholders})",
            binds,
        )
        removed = cur.rowcount
        conn.commit()
        print(f"\nSoft-deleted {removed} row(s).")

        # confirm the remaining active set
        cur.execute(
            'SELECT CODE, "goods_group" FROM "fa_kala_price" '
            "WHERE IS_DELETED = 'no' ORDER BY CODE"
        )
        rows = cur.fetchall()
        print(f"\nقیمت کالا now has {len(rows)} active row(s):")
        for code, group in rows:
            print(f"  {code:>4}  {'' if group is None else str(group)[:40]}")


if __name__ == "__main__":
    main()