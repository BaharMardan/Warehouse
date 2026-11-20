"""Persist presentation preferences independently of financial receipt records."""


def upgrade(cursor):
    cursor.execute("""CREATE TABLE "FA_TALLY_RECEIPT_LAYOUT" (
        "TALLY_ID" NUMBER PRIMARY KEY REFERENCES "FA_TALI_HEADER" ("ID_TALI"),
        "SEPARATE_ROWS" VARCHAR2(3 CHAR) DEFAULT 'no' NOT NULL,
        "MODIFY_AT" TIMESTAMP DEFAULT SYSTIMESTAMP NOT NULL,
        "MODIFY_BY" NUMBER NOT NULL,
        CONSTRAINT "CK_RECEIPT_LAYOUT_SEPARATE" CHECK ("SEPARATE_ROWS" IN ('yes','no'))
    )""")
