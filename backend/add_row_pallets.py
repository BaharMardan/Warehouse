"""Run before deploying row-level volumetric storage. Does not guess legacy counts."""
from app.core.db import get_connection


def main():
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT 1 FROM user_tab_columns WHERE table_name = 'FA_TALI_DETAILES' AND column_name = 'ROW_PALLETS'")
            if cur.fetchone() is None:
                cur.execute('''ALTER TABLE "FA_TALI_DETAILES" ADD ("ROW_PALLETS" NUMBER
                    CHECK ("ROW_PALLETS" >= 1 AND "ROW_PALLETS" = TRUNC("ROW_PALLETS")))''')
            cur.execute("SELECT 1 FROM user_tables WHERE table_name = 'FA_RECEIPT_PALLETS'")
            if cur.fetchone() is None:
                cur.execute('''CREATE TABLE "FA_RECEIPT_PALLETS" (
                    "RECEIPT_ID" NUMBER NOT NULL REFERENCES "fa_ghabz_anbar_header" ("ID_ghabz"),
                    "TALLY_DETAIL_ID" NUMBER NOT NULL REFERENCES "FA_TALI_DETAILES" ("ID_TALI_DETAILS"),
                    "PALLETS" NUMBER NOT NULL CHECK ("PALLETS" >= 1 AND "PALLETS" = TRUNC("PALLETS")),
                    CONSTRAINT "PK_RECEIPT_PALLETS" PRIMARY KEY ("RECEIPT_ID", "TALLY_DETAIL_ID"))''')
        conn.commit()


if __name__ == '__main__':
    main()
