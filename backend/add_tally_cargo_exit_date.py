"""Add optional cargo exit date. Safe to rerun; existing headers retain NULL."""
from app.core.db import get_connection


def main():
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""SELECT DATA_TYPE FROM USER_TAB_COLUMNS
                WHERE TABLE_NAME = 'FA_TALI_HEADER' AND COLUMN_NAME = 'DATE_CARGO_EXIT'""")
            existing = cur.fetchone()
            if existing is None:
                cur.execute('ALTER TABLE "FA_TALI_HEADER" ADD ("DATE_CARGO_EXIT" DATE)')
                print("Added FA_TALI_HEADER.DATE_CARGO_EXIT")
            elif existing[0] != "DATE":
                raise RuntimeError("DATE_CARGO_EXIT exists with an unexpected type")
            else:
                print("FA_TALI_HEADER.DATE_CARGO_EXIT already exists")
        conn.commit()


if __name__ == "__main__":
    main()
