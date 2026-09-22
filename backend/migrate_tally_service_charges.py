"""Separate tally handling services (including crane) and record optional freight.

Run once before deploying the matching API code. Existing strip records remain
unloading records and retain their historical catalog pricing.
"""
from app.core.db import get_connection


def add_column(cursor, table: str, definition: str) -> None:
    try:
        cursor.execute(f'ALTER TABLE "{table}" ADD ({definition})')
    except Exception as exc:
        if "ORA-01430" not in str(exc):
            raise


def main() -> None:
    with get_connection() as connection:
        cursor = connection.cursor()
        add_column(cursor, "fa_kala_price", '"price_loading" NUMBER')
        cursor.execute('UPDATE "fa_kala_price" SET "price_loading" = "price_unloding" WHERE "price_loading" IS NULL')
        add_column(cursor, "fa_tali_kala_strip", '"service_kind" VARCHAR2(12 CHAR) DEFAULT \'strip\' NOT NULL')
        add_column(cursor, "FA_TALI_HEADER", '"HAS_TRANSPORTATION" VARCHAR2(3 CHAR)')
        try:
            cursor.execute('''CREATE TABLE "FA_TALI_CARRIER_TRANSPORTATION" (
                "TALI_ID" NUMBER NOT NULL,
                "NUMBER_HAMEL" VARCHAR2(200 CHAR) NOT NULL,
                "HAS_TRANSPORTATION" VARCHAR2(3 CHAR) NOT NULL,
                CONSTRAINT "PK_TALI_CARRIER_TRANSPORT" PRIMARY KEY ("TALI_ID", "NUMBER_HAMEL"),
                CONSTRAINT "CK_TALI_CARRIER_TRANSPORT" CHECK ("HAS_TRANSPORTATION" IN ('yes', 'no'))
            )''')
        except Exception as exc:
            if "ORA-00955" not in str(exc):
                raise
        cursor.execute('''INSERT INTO "FA_TALI_CARRIER_TRANSPORTATION"
            ("TALI_ID", "NUMBER_HAMEL", "HAS_TRANSPORTATION")
            SELECT h."ID_TALI", MIN(d."NUMBER_HAMEL"), h."HAS_TRANSPORTATION"
            FROM "FA_TALI_HEADER" h
            JOIN "FA_TALI_DETAILES" d ON d."ID_HEADERS_TALI" = h."ID_TALI" AND d."IS_DELETED" = 'no'
            WHERE h."HAS_TRANSPORTATION" IN ('yes', 'no') AND d."NUMBER_HAMEL" IS NOT NULL
              AND NOT EXISTS (SELECT 1 FROM "FA_TALI_CARRIER_TRANSPORTATION" t WHERE t."TALI_ID" = h."ID_TALI")
            GROUP BY h."ID_TALI", h."HAS_TRANSPORTATION"
            HAVING COUNT(DISTINCT d."NUMBER_HAMEL") = 1''')
        connection.commit()


if __name__ == "__main__":
    main()
