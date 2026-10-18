"""Durable handoff events; no production rows are changed or backfilled."""


def upgrade(cursor):
    cursor.execute("""
        CREATE TABLE "FA_HANDOFF_CLOCK" (
            "ID" NUMBER(1) PRIMARY KEY CHECK ("ID" = 1),
            "VERSION" NUMBER(19) DEFAULT 0 NOT NULL
        )
    """)
    cursor.execute('INSERT INTO "FA_HANDOFF_CLOCK" ("ID", "VERSION") VALUES (1, 0)')
    cursor.execute("""
        CREATE TABLE "FA_HANDOFF_EVENTS" (
            "ID" NUMBER(19) PRIMARY KEY,
            "TARGET" VARCHAR2(8 CHAR) NOT NULL CHECK ("TARGET" IN ('keeper', 'operator')),
            "TALLY_ID" NUMBER NOT NULL,
            "RECEIPT_ID" NUMBER,
            "ACTOR_ID" NUMBER NOT NULL,
            "CREATED_AT" TIMESTAMP DEFAULT SYS_EXTRACT_UTC(SYSTIMESTAMP) NOT NULL
        )
    """)
    cursor.execute('CREATE INDEX "IX_FA_HANDOFF_TARGET_ID" ON "FA_HANDOFF_EVENTS" ("TARGET", "ID")')
