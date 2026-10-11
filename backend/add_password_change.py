"""Add the temporary-password flag. Existing accounts keep their current passwords.

Run from backend/: .venv/Scripts/python.exe add_password_change.py
Safe to repeat; no password hashes or existing account flags are modified.
"""
from app.core.db import get_connection


def main():
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""SELECT COUNT(*) FROM USER_TAB_COLUMNS
                WHERE TABLE_NAME = 'FA_USERS' AND COLUMN_NAME = 'MUST_CHANGE_PASSWORD'""")
            if not cur.fetchone()[0]:
                cur.execute("""ALTER TABLE "FA_USERS" ADD (
                    "MUST_CHANGE_PASSWORD" VARCHAR2(3 CHAR) DEFAULT 'no' NOT NULL)""")
            cur.execute("""SELECT COUNT(*) FROM USER_CONSTRAINTS
                WHERE CONSTRAINT_NAME = 'CK_USERS_PASSWORD_CHANGE'""")
            if not cur.fetchone()[0]:
                cur.execute("""ALTER TABLE "FA_USERS" ADD CONSTRAINT "CK_USERS_PASSWORD_CHANGE"
                    CHECK ("MUST_CHANGE_PASSWORD" IN ('yes', 'no'))""")
            cur.execute("""SELECT COUNT(*) FROM USER_TAB_COLUMNS WHERE TABLE_NAME = 'FA_USERS'
                AND COLUMN_NAME = 'MUST_CHANGE_PASSWORD' AND NULLABLE = 'N'""")
            if cur.fetchone()[0] != 1:
                raise RuntimeError("Password-change flag verification failed")
    print("Password-change schema is ready; existing passwords are unchanged.")


if __name__ == "__main__":
    main()
