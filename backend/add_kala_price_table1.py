"""قیمت کالا -> Excel Table 1 (بهار ۱۴۰۵ tariff, گروه کالا).

Reshapes the قیمت کالا rows to Table 1's columns: code · گروه کالا · انبارداری
(storage) · تخلیه و بارگیری (handling). Adds two columns and upserts the 24 group
rows (101–124) BY CODE.

Adds:
  1. "fa_kala_price"."goods_group"   VARCHAR2(200 CHAR)  — the گروه کالا row label.
  2. "fa_kala_price"."storage_price" (same type as price_30_day) — انبارداری.
     تخلیه و بارگیری reuses the existing "price_unloding" column.

Non-destructive & invoice-safe:
  * Upsert BY CODE — an existing code is UPDATEd (only goods_group / storage_price /
    price_unloding), a missing code is INSERTed. Nothing is deleted.
  * The 30/60/90-day tier columns are NOT touched, so the invoice engine (which still
    reads them) behaves exactly as before. They stay editable in the modal; they're
    just off the list now. Porting the invoice to this tariff is a separate, later task.

Both tables are lowercase-named; new columns are quoted lowercase to match convention.
IDEMPOTENT: existing columns are skipped (ORA-01430); re-running just rewrites the same
24 rows. POSTGRES: swap the ALTERs for `ADD COLUMN <name> <type>` (lowercase, unquoted).

Run (backend env, same as run_ddl.py):
    python add_kala_price_table1.py
"""
from app.core.db import get_connection

# (code, گروه کالا, انبارداری/storage, تخلیه و بارگیری/handling) — read from Table 1.
SEED = [
    ('101', 'آهن آلات و فلزات استاندارد(هرتن)', 56003, 3940623),
    ('102', 'آهن آلات و فلزات غیراستاندارد(هرتن)', 61604, 3453585),
    ('103', 'لاستیک وسائل نقلیه سنگین (انواع کامیون ، تریلی ، اتوبوس ، تراکتور ) هرتن', 78320, 6995739),
    ('104', 'انواع حیوانات(هرقطعه-راس-قلاده)', 892356, 2817107),
    ('105', 'تنه،تخته چندلایه وانواع نئوپان وMDF والواروتخته', 44819, 2228712),
    ('106', 'موتورسیکلت(هردستگاه)', 488337, 1068350),
    ('107', 'خدمات با بغل کن(رولها ،عدلهای غیرخطرناک وکالاهای مشابه)', 48150, 2935475),
    ('108', 'کالای الکترونیکی و انواع تجهیزات الکترونیکی وکامپیوتری', 43009, 39527570),
    ('109', 'کالای حجیم ترافیکی(هرتن)', 93017, 4016644),
    ('110', 'کالای عمومی کیسه ای و یا غیرپالتیزه(هرتن)', 63360, 4649988),
    ('111', 'جامبو(هرتن)', 61153, 3134027),
    ('112', 'قطعات ماشین آلات و تجهیزات(هرتن)', 82878, 3013330),
    ('113', 'وسائل نقلیه بیش از 10تن تا 20 تن(هر دستگاه)', 2475880, 60157075),
    ('114', 'دستگاه ها و ماشین آلات مختلف (هرتن)', 86258, 3664432),
    ('115', 'انواع خودرو و وسائل نقلیه تا 2 تن (هردستگاه)', 1274509, 7022929),
    ('116', 'انواع خودرو وسائل نقلیه بیش از 2تن تا 5تن (هردستگاه)', 1438602, 10005682),
    ('117', 'انواع خودرو وسائل نقلیه بیش از5تن تا 10تن (هردستگاه)', 2801183, 19654437),
    ('118', 'کانتینر20 فوت پرتا 10 تن ( هردستگاه)', 804650, 38694065),
    ('119', 'کانتینر20 فوت پر مازاد بر10تن(هرتن)', 80465, 3347231),
    ('120', 'کانتینر40فوت پرتا وزن 15 تن (هر دستگاه)', 1906300, 56977322),
    ('121', 'کانتینر40فوت پر مازاد بر15 تن (هرتن)', 160930, 5656689),
    ('122', 'کانتینر20 فوت خالی ( هردستگاه)', 402325, 26536524),
    ('123', 'کانتینر40فوت خالی (هردستگاه )', 804650, 39527570),
    ('124', 'سایرکالاها( هرتن)', 43009, 2583915),
]


def _mirror_type_of(cur, column: str) -> str:
    """Build a type string identical to fa_kala_price.<column>."""
    cur.execute("""
        SELECT data_type, data_length, data_precision, data_scale, char_length, char_used
        FROM user_tab_columns
        WHERE table_name = 'fa_kala_price' AND column_name = :c
    """, {"c": column})
    r = cur.fetchone()
    if not r:
        raise RuntimeError(f'Could not find fa_kala_price."{column}" to mirror its type.')
    dt, dlen, prec, scale, clen, cused = r
    if dt in ("VARCHAR2", "CHAR", "NVARCHAR2", "NCHAR"):
        n = clen or dlen
        return f"{dt}({n} {'CHAR' if cused == 'C' else 'BYTE'})"
    if dt == "NUMBER":
        if prec is not None:
            return f"NUMBER({prec},{scale or 0})" if scale else f"NUMBER({prec})"
        return "NUMBER"
    return dt


def _add_column(cur, column: str, col_type: str):
    try:
        cur.execute(f'ALTER TABLE "fa_kala_price" ADD ("{column}" {col_type})')
        print(f'OK  : added "fa_kala_price"."{column}" {col_type}')
    except Exception as exc:
        if "ORA-01430" in str(exc):
            print(f'SKIP: "fa_kala_price"."{column}" already exists')
        else:
            raise


def main():
    with get_connection() as conn:
        cur = conn.cursor()

        # 1) columns
        _add_column(cur, "goods_group", "VARCHAR2(200 CHAR)")
        storage_type = _mirror_type_of(cur, "price_30_day")
        print(f'(price_30_day is {storage_type} -> storage_price mirrors it)')
        _add_column(cur, "storage_price", storage_type)

        # 2) upsert BY CODE (CODE is UPPERCASE; the new cols are lowercase)
        inserted = updated = 0
        for code, group, storage, handling in SEED:
            binds = {"c": code, "g": group, "s": storage, "h": handling}
            cur.execute(
                'UPDATE "fa_kala_price" '
                'SET "goods_group" = :g, "storage_price" = :s, "price_unloding" = :h '
                'WHERE CODE = :c',
                binds,
            )
            if cur.rowcount:
                updated += cur.rowcount
                print(f"UPDATE: {code}  {group[:28]}")
            else:
                cur.execute(
                    'INSERT INTO "fa_kala_price" '
                    '("id_kala_price", CODE, "goods_group", "storage_price", "price_unloding", '
                    ' IS_DELETED, CREATE_AT, CREATE_BY) '
                    'VALUES ((SELECT COALESCE(MAX("id_kala_price"), 0) + 1 FROM "fa_kala_price"), '
                    ' :c, :g, :s, :h, \'no\', SYSDATE, 1)',
                    binds,
                )
                inserted += 1
                print(f"INSERT: {code}  {group[:28]}")

        conn.commit()
        print(f"\n{updated} updated, {inserted} inserted.")

        # 3) show the Table-1 view of active rows
        cur.execute(
            'SELECT CODE, "goods_group", "storage_price", "price_unloding" '
            'FROM "fa_kala_price" WHERE IS_DELETED = \'no\' ORDER BY CODE'
        )
        print("\nقیمت کالا now (code | گروه کالا | انبارداری | تخلیه و بارگیری):")
        for code, group, storage, handling in cur.fetchall():
            g = "" if group is None else str(group)[:34]
            print(f"  {code:>4} | {g:<34} | {storage} | {handling}")


if __name__ == "__main__":
    main()