"""Persistent notification acknowledgements, isolated per user."""
from app.core.db import get_connection


def main():
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT COUNT(*) FROM USER_TABLES WHERE TABLE_NAME = 'FA_ABANDONED_SEEN'")
            if cur.fetchone()[0]:
                print("FA_ABANDONED_SEEN already exists")
                return
            cur.execute("""CREATE TABLE FA_ABANDONED_SEEN (
                USER_ID NUMBER NOT NULL REFERENCES FA_USERS(ID),
                EVENT_TOKEN VARCHAR2(64) NOT NULL,
                SEEN_AT DATE NOT NULL,
                CONSTRAINT PK_FA_ABANDONED_SEEN PRIMARY KEY (USER_ID, EVENT_TOKEN)
            )""")
        conn.commit()
        print("Created FA_ABANDONED_SEEN")


if __name__ == "__main__":
    main()
