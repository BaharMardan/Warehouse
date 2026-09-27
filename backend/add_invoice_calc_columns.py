"""Invoice calculation notes and row kinds for the 1405 invoice rules.

Adds:
  FA_SORA_HESAB_DETAILS.ROW_KIND   what the row is (system, storage, service,
                                   insurance, tax, prepayment, discount). Lets the
                                   invoice page group rows and lets the issue flow
                                   see whether a tally's prepayment/discount was
                                   already applied on one of its invoices.
  FA_SORA_HESAB_DETAILS.CALC_NOTE  how the row's amount was produced, for the
                                   operator's check.
  FA_SORAT_HESAB_HEADER.CALC_NOTE  cargo type and the day count of the invoice.

Legacy invoices keep NULL in all three. Run with the API stopped:
    python add_invoice_calc_columns.py
Rerunnable. Oracle DDL commits immediately.
"""
from app.core.db import get_connection

ROW_KINDS = ("system", "storage", "service", "insurance", "tax", "prepayment", "discount")


def column(cur, table, name, definition):
    cur.execute("SELECT 1 FROM user_tab_columns WHERE table_name=:t AND column_name=:c",
                {"t": table, "c": name})
    if cur.fetchone() is None:
        cur.execute(f'ALTER TABLE "{table}" ADD ("{name}" {definition})')
        print(f"Added {table}.{name}")
    else:
        print(f"{table}.{name} already exists")


def constraint(cur, table, name, definition):
    cur.execute("SELECT 1 FROM user_constraints WHERE constraint_name=:n", {"n": name})
    if cur.fetchone() is None:
        cur.execute(f'ALTER TABLE "{table}" ADD CONSTRAINT "{name}" {definition}')
        print(f"Added constraint {name}")


def main():
    with get_connection() as conn:
        with conn.cursor() as cur:
            column(cur, "FA_SORA_HESAB_DETAILS", "ROW_KIND", "VARCHAR2(20 CHAR)")
            column(cur, "FA_SORA_HESAB_DETAILS", "CALC_NOTE", "VARCHAR2(1000 CHAR)")
            column(cur, "FA_SORAT_HESAB_HEADER", "CALC_NOTE", "VARCHAR2(1000 CHAR)")
            kinds = ", ".join(f"'{kind}'" for kind in ROW_KINDS)
            constraint(cur, "FA_SORA_HESAB_DETAILS", "CK_SORA_DETAILS_ROW_KIND",
                       f'CHECK ("ROW_KIND" IS NULL OR "ROW_KIND" IN ({kinds}))')
        conn.commit()


if __name__ == "__main__":
    main()
