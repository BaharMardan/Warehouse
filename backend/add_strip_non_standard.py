"""Task 4A/4B migration — add the Non-standard strip price and the per-junction
Pricing Type, then backfill the four Non-standard values from the rate sheet.

Adds:
  1. "fa_kala_strip"."non_standard"        — the Non-standard (غیراستاندارد) price.
     Created with the SAME type as the existing "normal" column (queried at runtime),
     so read/write behave identically to normal/dangerous.
  2. "fa_tali_kala_strip"."pricing_type"   — normal | non_standard | dangerous.
     VARCHAR2(20 CHAR), nullable. The invoice treats NULL as "normal", so existing
     junctions (and the tally-549 golden invoice) are unchanged.

Both columns are nullable -> every existing row stays valid. normal/dangerous values
are never touched. Both tables are lowercase-named, so the new columns are created as
quoted lowercase identifiers to match the existing convention.

Backfill (step 3): sets non_standard for the four known codes from the PDF, ONLY where
it is still NULL (won't clobber anything entered later). Set SEED = False to skip it.

IDEMPOTENT: existing columns are skipped (ORA-01430); the backfill only fills NULLs.
POSTGRES: replace the ALTERs with `ADD COLUMN <name> <type>` (lowercase, unquoted).

Run (backend env, same as run_ddl.py):
    python add_strip_non_standard.py
"""
from app.core.db import get_connection

SEED = True  # backfill the four Non-standard values from the rate sheet (PDF)

# code -> Non-standard value (غیراستاندارد column of the PDF)
NON_STANDARD_BY_CODE = {
    "201": "35381425",
    "202": "3538142",
    "401": "47808439",
    "402": "4780843",
}


def _mirror_type_of_normal(cur) -> str:
    """Build a column-type string identical to fa_kala_strip."normal"."""
    cur.execute("""
        SELECT data_type, data_length, data_precision, data_scale, char_length, char_used
        FROM user_tab_columns
        WHERE table_name = 'fa_kala_strip' AND column_name = 'normal'
    """)
    r = cur.fetchone()
    if not r:
        raise RuntimeError('Could not find fa_kala_strip."normal" to mirror its type.')
    data_type, data_length, precision, scale, char_length, char_used = r
    if data_type in ("VARCHAR2", "CHAR", "NVARCHAR2", "NCHAR"):
        n = char_length or data_length
        sem = "CHAR" if char_used == "C" else "BYTE"
        return f"{data_type}({n} {sem})"
    if data_type == "NUMBER":
        if precision is not None:
            return f"NUMBER({precision},{scale or 0})" if scale else f"NUMBER({precision})"
        return "NUMBER"
    return data_type  # FLOAT/DATE/etc. — unlikely for a price, but pass it through


def _add_column(cur, table: str, column: str, col_type: str):
    stmt = f'ALTER TABLE "{table}" ADD ("{column}" {col_type})'
    try:
        cur.execute(stmt)
        print(f"OK  : added \"{table}\".\"{column}\" {col_type}")
    except Exception as exc:
        if "ORA-01430" in str(exc):  # column already exists
            print(f"SKIP: \"{table}\".\"{column}\" already exists")
        else:
            raise


def main():
    with get_connection() as conn:
        cur = conn.cursor()

        # 1) non_standard on the rate table, same type as normal
        normal_type = _mirror_type_of_normal(cur)
        print(f'(fa_kala_strip."normal" is {normal_type})')
        _add_column(cur, "fa_kala_strip", "non_standard", normal_type)

        # 2) pricing_type on the junction table
        _add_column(cur, "fa_tali_kala_strip", "pricing_type", "VARCHAR2(20 CHAR)")

        # 3) backfill the four Non-standard values (only where still NULL)
        if SEED:
            for code, val in NON_STANDARD_BY_CODE.items():
                cur.execute(
                    'UPDATE "fa_kala_strip" SET "non_standard" = :v '
                    'WHERE "code" = :c AND "non_standard" IS NULL',
                    {"v": val, "c": code},
                )
                print(f"seed: code {code} -> non_standard {val}  ({cur.rowcount} row)")

        conn.commit()

        # confirm
        cur.execute(
            'SELECT "code", "normal", "non_standard", "dangerous" '
            'FROM "fa_kala_strip" ORDER BY "code"'
        )
        print("\nfa_kala_strip (code | normal | non_standard | dangerous):")
        for row in cur.fetchall():
            print("  ", " | ".join("NULL" if v is None else str(v) for v in row))


if __name__ == "__main__":
    main()