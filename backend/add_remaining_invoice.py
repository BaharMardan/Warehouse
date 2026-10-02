"""Add traceability and immutable input snapshots for remaining invoices; rerunnable."""
from app.core.db import get_connection


def main():
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT COUNT(*) FROM user_tables WHERE table_name = 'FA_REMAINING_INVOICE'")
            if not cur.fetchone()[0]:
                cur.execute('''CREATE TABLE "FA_REMAINING_INVOICE" (
                    "INVOICE_ID" NUMBER PRIMARY KEY REFERENCES "FA_SORAT_HESAB_HEADER" ("ID_SORAT"),
                    "ORIGINAL_INVOICE_ID" NUMBER NOT NULL REFERENCES "FA_SORAT_HESAB_HEADER" ("ID_SORAT"),
                    "RECEIPT_ID" NUMBER NOT NULL REFERENCES "fa_ghabz_anbar_header" ("ID_ghabz"),
                    "REQUEST_ID" VARCHAR2(36 CHAR) NOT NULL UNIQUE,
                    "SNAPSHOT_JSON" CLOB NOT NULL,
                    "PREVIEW_HASH" VARCHAR2(64 CHAR) NOT NULL,
                    CONSTRAINT "CK_REMAINING_PARENT" CHECK ("INVOICE_ID" <> "ORIGINAL_INVOICE_ID")
                )''')
                cur.execute('CREATE INDEX "IX_REMAINING_PARENT" ON "FA_REMAINING_INVOICE" ("ORIGINAL_INVOICE_ID")')
                cur.execute('CREATE INDEX "IX_REMAINING_RECEIPT" ON "FA_REMAINING_INVOICE" ("RECEIPT_ID")')
        conn.commit()
    print("Remaining invoice metadata ready")


if __name__ == "__main__":
    main()
