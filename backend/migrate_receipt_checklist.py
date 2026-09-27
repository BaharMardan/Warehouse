"""Rerunnable receipt checklist and proportional invoice allocation migration.

Oracle DDL commits immediately. Existing invoice links remain authoritative;
legacy detailed receipt ownership is selected explicitly, never guessed by HS.
"""
from app.core.db import get_connection


def column(cur, table, name, definition):
    cur.execute("SELECT 1 FROM user_tab_columns WHERE table_name=:t AND column_name=:c",
                {"t": table, "c": name})
    if cur.fetchone() is None:
        cur.execute(f'ALTER TABLE "{table}" ADD ("{name}" {definition})')


def constraint(cur, table, name, definition):
    cur.execute("SELECT 1 FROM user_constraints WHERE constraint_name=:n", {"n": name})
    if cur.fetchone() is None:
        cur.execute(f'ALTER TABLE "{table}" ADD CONSTRAINT "{name}" {definition}')


def main():
    from add_ghabz_pallet_quantity import main as add_pallet_quantity
    add_pallet_quantity()
    with get_connection() as conn:
        with conn.cursor() as cur:
            table = "fa_ghabz_anbar_header"
            for name, definition in {
                "WORKFLOW_STATUS": "VARCHAR2(20 CHAR) DEFAULT 'created' NOT NULL",
                "REQUIRES_INVOICE": "VARCHAR2(3 CHAR) DEFAULT 'yes' NOT NULL",
                "KEEPER_REQUIRED": "VARCHAR2(3 CHAR) DEFAULT 'yes' NOT NULL",
                "FINALIZED_AT": "DATE", "FINALIZED_BY": "NUMBER",
                "INVOICE_ISSUED_AT": "DATE", "INVOICE_ISSUED_BY": "NUMBER",
                "ALLOCATION_RATIO": "NUMBER",
            }.items():
                column(cur, table, name, definition)
            constraint(cur, table, "CK_GHABZ_WORKFLOW_STATUS",
                """CHECK ("WORKFLOW_STATUS" IN ('created','sent_to_keeper','finalized','invoice_issued'))""")
            constraint(cur, table, "CK_GHABZ_ALLOCATION_RATIO",
                """CHECK ("ALLOCATION_RATIO" > 0 AND "ALLOCATION_RATIO" <= 1)""")
            cur.execute("SELECT 1 FROM user_tables WHERE table_name='FA_GHABZ_TALLY_SOURCE'")
            if cur.fetchone() is None:
                cur.execute("""CREATE TABLE "FA_GHABZ_TALLY_SOURCE" (
                    "RECEIPT_ID" NUMBER NOT NULL, "TALLY_DETAIL_ID" NUMBER NOT NULL,
                    "QUANTITY_SHARE" NUMBER DEFAULT 0 NOT NULL,
                    "WEIGHT_SHARE" NUMBER DEFAULT 0 NOT NULL, "BASKOL_SHARE" NUMBER DEFAULT 0 NOT NULL,
                    CONSTRAINT "PK_GHABZ_TALLY_SOURCE" PRIMARY KEY ("RECEIPT_ID","TALLY_DETAIL_ID"),
                    CONSTRAINT "FK_GTS_RECEIPT" FOREIGN KEY ("RECEIPT_ID")
                        REFERENCES "fa_ghabz_anbar_header" ("ID_ghabz"),
                    CONSTRAINT "FK_GTS_TALLY_DETAIL" FOREIGN KEY ("TALLY_DETAIL_ID")
                        REFERENCES "FA_TALI_DETAILES" ("ID_TALI_DETAILS"),
                    CONSTRAINT "CK_GTS_SHARES" CHECK ("QUANTITY_SHARE" BETWEEN 0 AND 1
                        AND "WEIGHT_SHARE" BETWEEN 0 AND 1 AND "BASKOL_SHARE" BETWEEN 0 AND 1)
                )""")
            cur.execute("SELECT 1 FROM user_tables WHERE table_name='FA_RECEIPT_SERVICE_POOL'")
            if cur.fetchone() is None:
                cur.execute("""CREATE TABLE "FA_RECEIPT_SERVICE_POOL" (
                    "TALLY_ID" NUMBER NOT NULL, "LINE_NO" NUMBER NOT NULL,
                    "DESCRIPTION" VARCHAR2(550 CHAR), "TOTAL_PRICE" NUMBER NOT NULL,
                    CONSTRAINT "PK_RECEIPT_SERVICE_POOL" PRIMARY KEY ("TALLY_ID","LINE_NO"),
                    CONSTRAINT "FK_RECEIPT_POOL_TALLY" FOREIGN KEY ("TALLY_ID")
                        REFERENCES "FA_TALI_HEADER" ("ID_TALI"),
                    CONSTRAINT "CK_RECEIPT_POOL_PRICE" CHECK ("TOTAL_PRICE" >= 0)
                )""")
            column(cur, "FA_SORA_HESAB_DETAILS", "SERVICE_POOL_LINE", "NUMBER")
            cur.execute("""UPDATE "fa_ghabz_anbar_header" h SET "WORKFLOW_STATUS"='invoice_issued'
                WHERE h."WORKFLOW_STATUS" IN ('created','sent_to_keeper')
                  AND EXISTS (SELECT 1 FROM "FA_SORAT_HESAB_HEADER" i
                    WHERE i."ID_GHABZ_ANBAR"=h."ID_ghabz"
                      AND NVL(i."SORAT_IS_DELETED",'no')='no')""")
        conn.commit()


if __name__ == "__main__":
    main()
