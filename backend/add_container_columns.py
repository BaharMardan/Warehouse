"""Add CONTAINER_TYPE + CONTAINER_NUMBER to FA_TALI_DETAILES (Task 3).

The tally line now has a «نوع کانتینر» dropdown and a conditional «شماره کانتینر»
box; these two nullable columns persist them. Existing rows are untouched (both
columns are nullable, so all current tally lines stay valid).

CHAR length semantics so Persian container-type text isn't truncated by byte count.

IDEMPOTENT: re-running skips columns that already exist (ORA-01430).
POSTGRES: replace each ALTER with `ALTER TABLE fa_tali_detailes ADD COLUMN <name> VARCHAR(n);`.

Run (backend env, same as run_ddl.py):
    python add_container_columns.py
"""
from app.core.db import get_connection

STATEMENTS = [
    "ALTER TABLE FA_TALI_DETAILES ADD (CONTAINER_TYPE   VARCHAR2(50 CHAR))",
    "ALTER TABLE FA_TALI_DETAILES ADD (CONTAINER_NUMBER VARCHAR2(30 CHAR))",
]

# ORA-01430: column being added already exists in table
IGNORE = ("ORA-01430",)


def main():
    with get_connection() as conn:
        cur = conn.cursor()
        for stmt in STATEMENTS:
            head = " ".join(stmt.split())
            try:
                cur.execute(stmt)
                print("OK  :", head)
            except Exception as exc:
                msg = str(exc)
                if any(code in msg for code in IGNORE):
                    print("SKIP:", head, "->", msg.split("\n")[0])
                else:
                    raise
        conn.commit()

        # confirm the columns exist
        cur.execute("""
            SELECT column_name, data_type, char_length
            FROM user_tab_columns
            WHERE table_name = 'FA_TALI_DETAILES'
              AND column_name IN ('CONTAINER_TYPE', 'CONTAINER_NUMBER')
            ORDER BY column_name
        """)
        print("\nColumns now on FA_TALI_DETAILES:")
        for r in cur.fetchall():
            print(f"  {r[0]}  {r[1]}({r[2]})")


if __name__ == "__main__":
    main()