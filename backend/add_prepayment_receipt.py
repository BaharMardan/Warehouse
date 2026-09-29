"""Create private prepayment-receipt storage. Safe to rerun."""
from app.core.db import get_connection


def main():
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT COUNT(*) FROM USER_TABLES WHERE TABLE_NAME = 'FA_TALLY_PAYMENT_RECEIPT'")
            if cur.fetchone()[0]:
                print("FA_TALLY_PAYMENT_RECEIPT already exists")
                return
            cur.execute("""CREATE TABLE FA_TALLY_PAYMENT_RECEIPT (
                TALLY_ID NUMBER PRIMARY KEY REFERENCES FA_TALI_HEADER(ID_TALI),
                FILE_NAME NVARCHAR2(240) NOT NULL,
                MIME_TYPE VARCHAR2(100) NOT NULL,
                FILE_CONTENT BLOB NOT NULL,
                MODIFIED_AT DATE NOT NULL,
                MODIFIED_BY NUMBER NOT NULL
            )""")
        conn.commit()
        print("Created FA_TALLY_PAYMENT_RECEIPT")


if __name__ == "__main__":
    main()
