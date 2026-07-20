"""Convert FA_TALI_DETAILES.ZARIB_MAHAL from NUMBER to VARCHAR2 (text).

WHY
    «ضریب محل» used to be a numeric coefficient. The tally «افزودن ردیف کالا» form
    now offers it as a dropdown of storage-location types (انبارداری مسقف / تانگارد /
    بارانداز / محوطه), which are text. To store those labels the column must be
    VARCHAR2 instead of NUMBER.

    NOTE ON INVOICING: the invoice engine multiplies by ZARIB_MAHAL. Existing rows
    are preserved here as their text form (TO_CHAR), e.g. "1", so old invoices that
    relied on numeric coefficients still parse. NEW rows that store a location LABEL
    will not multiply until the invoice logic is reworked to map label -> coefficient
    (a separate, deliberate change).

HOW (safe on a non-empty column)
    Oracle refuses to change a NUMBER column to VARCHAR2 while it holds data
    (ORA-01439). So we add a temp text column, copy values across as text, drop the
    old column, and rename the temp one back. Column position is irrelevant — every
    query references it by name ("ZARIB_MAHAL").

IDEMPOTENT
    Re-running is safe: if ZARIB_MAHAL is already VARCHAR2 the script exits without
    touching anything. A leftover temp column from a half-finished run is cleaned up
    before starting.

NON-DESTRUCTIVE
    No rows are deleted; existing coefficient values are kept (as text). Only the
    column's datatype changes.

Run (backend env, same as the other migration scripts):
    python alter_zarib_mahal_to_text.py
"""
from app.core.db import get_connection

TABLE = "FA_TALI_DETAILES"
COL = "ZARIB_MAHAL"
TMP = "ZARIB_MAHAL_TMP"


def _data_type(cur, table: str, col: str) -> str | None:
    cur.execute(
        "SELECT data_type FROM user_tab_columns "
        "WHERE table_name = :t AND column_name = :c",
        {"t": table, "c": col},
    )
    row = cur.fetchone()
    return row[0] if row else None


def main() -> None:
    with get_connection() as conn:
        cur = conn.cursor()

        current = _data_type(cur, TABLE, COL)
        if current is None:
            raise SystemExit(f"{TABLE}.{COL} not found — aborting.")
        if current.upper().startswith("VARCHAR"):
            print(f"{TABLE}.{COL} is already {current} — nothing to do.")
            return

        print(f"{TABLE}.{COL} is currently {current}; converting to VARCHAR2(100 CHAR)…")

        # 0) clean up a temp column left behind by a previous half-run
        if _data_type(cur, TABLE, TMP) is not None:
            cur.execute(f'ALTER TABLE {TABLE} DROP COLUMN "{TMP}"')
            print(f"  dropped leftover {TMP}")

        # 1) add the text column
        cur.execute(f'ALTER TABLE {TABLE} ADD ("{TMP}" VARCHAR2(100 CHAR))')
        print(f"  added {TMP}")

        # 2) copy existing coefficients across as text (preserves old data)
        cur.execute(
            f'UPDATE {TABLE} SET "{TMP}" = TO_CHAR("{COL}") WHERE "{COL}" IS NOT NULL'
        )
        print(f"  copied {cur.rowcount} existing value(s) to text")
        conn.commit()

        # 3) drop the numeric column, 4) rename temp -> ZARIB_MAHAL
        cur.execute(f'ALTER TABLE {TABLE} DROP COLUMN "{COL}"')
        cur.execute(f'ALTER TABLE {TABLE} RENAME COLUMN "{TMP}" TO "{COL}"')
        print(f"  {COL} is now VARCHAR2(100 CHAR)")

        # verify
        final = _data_type(cur, TABLE, COL)
        print(f"done — {TABLE}.{COL} is {final}")


if __name__ == "__main__":
    main()