"""Add per-receipt pallet quantity. Run before deploying the receipt UI/API."""
from app.core.db import get_connection


def main():
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""SELECT 1 FROM user_tab_columns
                WHERE table_name = 'fa_ghabz_anbar_header' AND column_name = 'PALLET_QUANTITY'""")
            if cur.fetchone() is None:
                cur.execute('ALTER TABLE "fa_ghabz_anbar_header" ADD ("PALLET_QUANTITY" NUMBER)')
            cur.execute("""SELECT 1 FROM user_constraints
                WHERE table_name = 'fa_ghabz_anbar_header' AND constraint_name = 'CK_GHABZ_PALLET_QUANTITY'""")
            if cur.fetchone() is None:
                cur.execute("""ALTER TABLE "fa_ghabz_anbar_header"
                    ADD CONSTRAINT "CK_GHABZ_PALLET_QUANTITY"
                    CHECK ("PALLET_QUANTITY" IS NULL OR
                        ("PALLET_QUANTITY" >= 1 AND "PALLET_QUANTITY" = TRUNC("PALLET_QUANTITY")))""")
        conn.commit()


if __name__ == "__main__":
    main()
