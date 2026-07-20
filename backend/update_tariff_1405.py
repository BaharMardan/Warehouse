"""Update سایر خدمات + کالاهای خطرناک + دیماند to the بهار ۱۴۰۵ tariff (docx).

Data was read straight from the document, so the amounts/labels are exact.

کالاهای خطرناک (fa_kala_dangerous) — invoice-safe (not read by the calc):
  * Adds "storage_price" (انبارداری), same type as price_30_day; تخلیه و بارگیری reuses
    the existing "price_unloding". 30/60/90 tiers are kept (untouched), off the list.
  * Upserts the 13 rows (501–513) BY CODE and soft-deletes any active row outside that set.

سایر خدمات (fa_kala_other_service) — invoice-safe (calc intentionally omits it):
  * Upserts the 17 rows (301–317) BY CODE and soft-deletes any active row outside that set.

دیماند (fa_kala_diamound) — feeds the invoice AND the tally-549 golden case:
  * The file has no codes for it, so this SOFT-DELETES the old rows and INSERTS the 3 new
    ones with codes 601–603. Because the invoice's diamound join has no IS_DELETED filter,
    existing tallies keep resolving their OLD (now soft-deleted) rate — so historical
    invoices, including the golden case, are UNCHANGED — while new tallies pick the new
    tariff. (If you'd rather re-price old invoices too, tell me and I'll upsert in place.)

All soft-deletes are reversible. Idempotent (columns skipped via ORA-01430; re-running
re-applies the same rows). POSTGRES: swap the ALTER for `ADD COLUMN ...` (unquoted).

Run (backend env):
    python update_tariff_1405.py
"""
from app.core.db import get_connection

# --- کالاهای خطرناک: (code, title, انبارداری/storage, تخلیه و بارگیری/handling) ---
DANGEROUS = [
    ('501', 'دسته 1: مواد منفجره(هرتن)', 418418, 4771574),
    ('502', 'دسته2:گازها(هرتن)', 189897, 4274300),
    ('503', 'دسته3:مایعات قابل اشتعال (هرتن) گروه 1', 89234, 3652225),
    ('504', 'دسته4:مایعات قابل اشتعال (هرتن)گروه2', 104370, 3772784),
    ('505', 'دسته5:مایعات قابل اشتعال (هرتن)گروه3', 155780, 4351225),
    ('506', 'دسته6:جامدات قابل اشتعال(هرتن) گروه1', 86635, 3545851),
    ('507', 'دسته7:جامدات قابل اشتعال (هرتن)گروه2', 102167, 3574986),
    ('508', 'دسته8:جامدات قابل اشتعال(هرتن)گروه3', 141618, 3955659),
    ('509', 'دسته9:مواد اکسیدکننده وپراکسیدهای آلی(هرتن)', 138786, 3876546),
    ('510', 'دسته10:موادسمی و عفونی (هرتن)', 145866, 4074329),
    ('511', 'دسته11:مواد رادیواکتیو(هرتن)', 439338, 5010153),
    ('512', 'دسته12:مواد خورنده (هرتن)', 81954, 3354183),
    ('513', 'دسته13:مواد متفرقه خطرناک (هرتن)', 78051, 3194460),
]

# --- سایر خدمات: (code, title, price) ---
SERVICES = [
    ('301', 'برچسب', 2413950),
    ('302', 'پلمپ (هرعدد)', 1433081),
    ('303', 'جداسازی و یا نصب برزنت و چادر کانتینر و تریلی', 2069109),
    ('304', 'خدمات سیستمی', 3387898),
    ('305', 'خدمات پالتیزه', 3887264),
    ('306', 'باسکول دستی', 1033170),
    ('307', 'کابوتاژ سبک', 2413950),
    ('308', 'کابوتاژ نیمه سنگین و سنگین', 3179976),
    ('309', 'انوانتر ( هرتن)', 2135959),
    ('310', 'جک پالت(هرعدد/هروسیله)', 15288350),
    ('311', 'خدمات نفر ساعت', 1770230),
    ('312', 'ترخیص یکسره ( برروی حامل – هرتن )', 1265495),
    ('313', 'اصلاح قبض ،تفکیک قبض،کپی برابراصل', 3605816),
    ('314', 'چاپ مجدد قبض انبار،صورتحساب و.....', 4681600),
    ('315', 'برش ،قطعه برداری و نمونه برداری', 3438050),
    ('316', 'پالتیزاسیون(هرتن)', 750000),
    ('317', 'بابری در انبار هر ناوگان تریلی', 12500000),
]

# --- دیماند: (assigned code, title, غیراداری/gher_edari, تعطیل/holiday) ---
DIAMOUND = [
    ('601', 'سواری و وانت', 2092090, 4023250),
    ('602', 'کامیون ، خاور', 3580692, 5371843),
    ('603', 'کفی و تریلی', 4827900, 6437200),
]


def _mirror_type(cur, table, column):
    cur.execute("""
        SELECT data_type, data_length, data_precision, data_scale, char_length, char_used
        FROM user_tab_columns WHERE table_name = :t AND column_name = :c
    """, {"t": table, "c": column})
    r = cur.fetchone()
    if not r:
        raise RuntimeError(f'{table}."{column}" not found to mirror.')
    dt, dlen, prec, scale, clen, cused = r
    if dt in ("VARCHAR2", "CHAR", "NVARCHAR2", "NCHAR"):
        return f"{dt}({clen or dlen} {'CHAR' if cused == 'C' else 'BYTE'})"
    if dt == "NUMBER":
        return (f"NUMBER({prec},{scale or 0})" if scale else f"NUMBER({prec})") if prec else "NUMBER"
    return dt


def _next_pk_sql(table, pk):
    return f'(SELECT COALESCE(MAX("{pk}"), 0) + 1 FROM "{table}")'


def dangerous(cur):
    print("=== کالاهای خطرناک ===")
    try:
        t = _mirror_type(cur, "fa_kala_dangerous", "price_30_day")
        cur.execute(f'ALTER TABLE "fa_kala_dangerous" ADD ("storage_price" {t})')
        print(f'  added "storage_price" {t}')
    except Exception as e:
        if "ORA-01430" in str(e):
            print('  "storage_price" already exists')
        else:
            raise
    for code, title, storage, handling in DANGEROUS:
        b = {"c": code, "t": title, "s": storage, "h": handling}
        cur.execute('UPDATE "fa_kala_dangerous" SET TITLE=:t, "storage_price"=:s, '
                    '"price_unloding"=:h WHERE "code"=:c', b)
        if not cur.rowcount:
            cur.execute(
                f'INSERT INTO "fa_kala_dangerous" ("id_kala_dangerous", "code", TITLE, '
                f'"storage_price", "price_unloding", IS_DELETED, CREATE_AT, CREATE_BY) '
                f'VALUES ({_next_pk_sql("fa_kala_dangerous", "id_kala_dangerous")}, '
                f':c, :t, :s, :h, \'no\', SYSDATE, 1)', b)
    keep = {c for c, *_ in DANGEROUS}
    ph = ", ".join(f":k{i}" for i in range(len(keep)))
    cur.execute(f'UPDATE "fa_kala_dangerous" SET IS_DELETED=\'yes\', MODIFY_AT=SYSDATE, '
                f'MODIFY_BY=1 WHERE IS_DELETED=\'no\' AND "code" NOT IN ({ph})',
                {f"k{i}": c for i, c in enumerate(keep)})
    print(f"  upserted {len(DANGEROUS)}, soft-deleted {cur.rowcount} outside 501–513")


def services(cur):
    print("=== سایر خدمات ===")
    for code, title, price in SERVICES:
        b = {"c": code, "t": title, "p": str(price)}
        cur.execute('UPDATE "fa_kala_other_service" SET "title"=:t, "price"=:p WHERE "code"=:c', b)
        if not cur.rowcount:
            cur.execute(
                f'INSERT INTO "fa_kala_other_service" ("id_kala_other_service", "code", '
                f'"title", "price", IS_DELETED, CREATE_AT, CREATE_BY) '
                f'VALUES ({_next_pk_sql("fa_kala_other_service", "id_kala_other_service")}, '
                f':c, :t, :p, \'no\', SYSDATE, 1)', b)
    keep = {c for c, *_ in SERVICES}
    ph = ", ".join(f":k{i}" for i in range(len(keep)))
    cur.execute(f'UPDATE "fa_kala_other_service" SET IS_DELETED=\'yes\', MODIFY_AT=SYSDATE, '
                f'MODIFY_BY=1 WHERE IS_DELETED=\'no\' AND "code" NOT IN ({ph})',
                {f"k{i}": c for i, c in enumerate(keep)})
    print(f"  upserted {len(SERVICES)}, soft-deleted {cur.rowcount} outside 301–317")


def diamound(cur):
    print("=== دیماند ===")
    # soft-delete the old rows (still joinable by the invoice -> old invoices unchanged)
    cur.execute("UPDATE \"fa_kala_diamound\" SET IS_DELETED='yes', MODIFY_AT=SYSDATE, "
                "MODIFY_BY=1 WHERE IS_DELETED='no'")
    print(f"  soft-deleted {cur.rowcount} old row(s)")
    for code, title, gher, holiday in DIAMOUND:
        cur.execute(
            f'INSERT INTO "fa_kala_diamound" ("id_kala_diamound", "code", "title", '
            f'"price_gher_edari", "price_holiday", IS_DELETED, CREATE_AT, CREATE_BY) '
            f'VALUES ({_next_pk_sql("fa_kala_diamound", "id_kala_diamound")}, '
            f':c, :t, :g, :h, \'no\', SYSDATE, 1)',
            {"c": code, "t": title, "g": str(gher), "h": str(holiday)})
    print(f"  inserted {len(DIAMOUND)} new row(s) (codes 601–603)")


def main():
    with get_connection() as conn:
        cur = conn.cursor()
        dangerous(cur)
        services(cur)
        diamound(cur)
        conn.commit()

        for label, table, pk, cols in [
            ("کالاهای خطرناک", "fa_kala_dangerous", "code", '"storage_price", "price_unloding"'),
            ("سایر خدمات", "fa_kala_other_service", "code", '"price"'),
            ("دیماند", "fa_kala_diamound", "code", '"price_gher_edari", "price_holiday"'),
        ]:
            cur.execute(f'SELECT "{pk}", {cols} FROM "{table}" '
                        f"WHERE IS_DELETED='no' ORDER BY \"{pk}\"")
            rows = cur.fetchall()
            print(f"\n{label}: {len(rows)} active row(s)")
            for r in rows:
                print("  ", " | ".join(str(x) for x in r))


if __name__ == "__main__":
    main()