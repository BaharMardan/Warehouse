"""Separate reusable public invoice numbers from immutable record identities."""
def upgrade(cursor):
    cursor.execute('ALTER TABLE "FA_SORAT_HESAB_HEADER" ADD ("INVOICE_NUMBER" NUMBER)')
    cursor.execute('UPDATE "FA_SORAT_HESAB_HEADER" SET "INVOICE_NUMBER" = "ID_SORAT"')
    cursor.execute('ALTER TABLE "FA_SORAT_HESAB_HEADER" MODIFY ("INVOICE_NUMBER" NOT NULL)')
    cursor.execute("""CREATE UNIQUE INDEX "UQ_FA_ACTIVE_INVOICE_NUMBER" ON "FA_SORAT_HESAB_HEADER"
        (CASE WHEN NVL("SORAT_IS_DELETED", 'no') = 'no' THEN "INVOICE_NUMBER" END)""")
    cursor.execute('SELECT NVL(MAX("ID_SORAT"), 0) + 1 FROM "FA_SORAT_HESAB_HEADER"')
    first = int(cursor.fetchone()[0])
    cursor.execute(f'CREATE SEQUENCE "SEQ_FA_INVOICE_RECORD" START WITH {first} INCREMENT BY 1 NOCYCLE')
