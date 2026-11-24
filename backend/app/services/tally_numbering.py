import re

"""Helpers for allocating immutable, continuous tally numbers."""


# The counter table originally used the Jalali year as its key. Key zero is
# reserved for the global counter so installations that already ran the
# previous migration do not need a destructive table replacement.
GLOBAL_COUNTER_KEY = 0

INCREMENT_COUNTER_SQL = """
UPDATE "FA_TALI_NUMBER_COUNTER"
SET "LAST_NUMBER" = "LAST_NUMBER" + 1
WHERE "JALALI_YEAR" = :counter_key
RETURNING "LAST_NUMBER" INTO :next_number
"""


def allocate_next_tally_number(cursor) -> str:
    """Allocate one global number using the caller's Oracle transaction.

    Updating the single counter row locks it until the surrounding tally
    creation transaction commits or rolls back. This prevents duplicates when
    several operators save a tally at the same time.

    The row must first be initialized by ``migrate_tally_numbering.py`` with
    the latest real-world tally number at go-live.
    """
    next_number_var = cursor.var(int)
    cursor.execute(
        INCREMENT_COUNTER_SQL,
        {
            "counter_key": GLOBAL_COUNTER_KEY,
            "next_number": next_number_var,
        },
    )
    if cursor.rowcount != 1:
        raise RuntimeError(
            "The continuous tally counter is not initialized. "
            "Run migrate_tally_numbering.py with --last-issued first."
        )

    value = next_number_var.getvalue()
    if isinstance(value, (list, tuple)):
        value = value[0]
    return str(int(value))


MODE_SQL = 'SELECT "VALUE_NUMBER" FROM "FA_APP_SETTINGS" WHERE "SETTING_KEY" = \'manual_tally_numbering\''


def manual_numbering(cursor, *, lock=False):
    cursor.execute(MODE_SQL + (' FOR UPDATE' if lock else ''))
    row = cursor.fetchone()
    return row is not None and int(row[0]) == 1


def normalize_manual_tally_number(supplied):
    from fastapi import HTTPException
    value = str(supplied or '').strip().translate(str.maketrans('۰۱۲۳۴۵۶۷۸۹٠١٢٣٤٥٦٧٨٩', '01234567890123456789'))
    value = value.replace('٫', '.')
    parts = value.split('.')
    if (not re.fullmatch(r'[0-9]+(?:\.[0-9]+)?', value)
            or len(value.replace('.', '')) > 15 or int(parts[0]) <= 0):
        raise HTTPException(422, 'شماره تالی را مانند 1941 یا 1941.1، حداکثر ۱۵ رقم وارد کنید')
    value = str(int(parts[0])) + ('.' + parts[1] if len(parts) == 2 else '')
    return value


def choose_tally_number(cursor, supplied):
    from fastapi import HTTPException
    # Serialize creates with mode changes; the existing DB unique key is also retained.
    manual = manual_numbering(cursor, lock=True)
    if manual:
        value = normalize_manual_tally_number(supplied)
        cursor.execute('SELECT 1 FROM "FA_TALI_HEADER" WHERE "TALI_NUMBER" = :tally_number', {'tally_number': value})
        if cursor.fetchone():
            raise HTTPException(409, 'این شماره تالی قبلاً ثبت شده است')
        return value
    while True:
        value = allocate_next_tally_number(cursor)
        cursor.execute('SELECT 1 FROM "FA_TALI_HEADER" WHERE "TALI_NUMBER" = :tally_number', {'tally_number': value})
        if not cursor.fetchone():
            return value


def editable_tally_number(cursor, supplied, tally_id):
    from fastapi import HTTPException
    if not manual_numbering(cursor, lock=True):
        raise HTTPException(409, 'ویرایش شماره تالی فقط در حالت شماره‌گذاری دستی مجاز است')
    value = normalize_manual_tally_number(supplied)
    cursor.execute('SELECT 1 FROM "FA_TALI_HEADER" WHERE "TALI_NUMBER" = :tally_number AND "ID_TALI" <> :id',
                   {'tally_number': value, 'id': tally_id})
    if cursor.fetchone():
        raise HTTPException(409, 'این شماره تالی قبلاً ثبت شده است')
    return value


def sync_receipt_numbers(cursor, tally_id, number, previous_number, actor_id):
    """Renumber active receipts under the caller's tally lock and transaction.

    Preserve issuance year, child sequence and historical voided documents.
    Complete every preflight check before updating the first receipt.
    """
    from fastapi import HTTPException
    cursor.execute("""SELECT "ID_ghabz", "GHABZ_NUMBER", "GHABZ_SEQ", "IS_MASTER", "NUMBER_tali"
        FROM "fa_ghabz_anbar_header" WHERE "TALI_ID" = :tid AND "IS_DELETED" = 'no'
        ORDER BY "ID_ghabz" FOR UPDATE""", {'tid': tally_id})
    updates = []
    for rid, old_number, sequence, master, saved_tally in cursor.fetchall():
        parts = str(old_number or '').split('_')
        if len(parts) not in (2, 3) or not re.fullmatch(r'[0-9]{4}', parts[0]):
            raise HTTPException(409, 'قالب شماره قبض فعلی قابل اصلاح خودکار نیست')
        # Preserve the issued suffix exactly, including legacy _0 masters.
        desired = parts[0] + '_' + number + ('_' + parts[2] if len(parts) == 3 else '')
        if desired != old_number or str(saved_tally or '') != number:
            updates.append({'id': rid, 'receipt_number': desired, 'tally_number': number, 'actor': actor_id})
    if not updates and str(previous_number or '') == number:
        return
    cursor.execute("""SELECT COUNT(*) FROM "FA_SORAT_HESAB_HEADER" i
        WHERE NVL(i."SORAT_IS_DELETED", 'no') = 'no' AND (
            i."TALI_ID_HEADER" = :tid OR i."ID_GHABZ_ANBAR" IN (
                SELECT "ID_ghabz" FROM "fa_ghabz_anbar_header" WHERE "TALI_ID" = :tid))""",
        {'tid': tally_id})
    if cursor.fetchone()[0]:
        raise HTTPException(409, 'برای اصلاح شماره تالی و قبض‌ها، ابتدا تمام صورتحساب‌های فعال این تالی را باطل کنید')
    for update in updates:
        cursor.execute('SELECT 1 FROM "fa_ghabz_anbar_header" WHERE "GHABZ_NUMBER" = :receipt_number AND "ID_ghabz" <> :id',
                       {'receipt_number': update['receipt_number'], 'id': update['id']})
        if cursor.fetchone():
            raise HTTPException(409, 'شماره قبض جدید قبلاً استفاده شده است')
    for update in updates:
        cursor.execute("""UPDATE "fa_ghabz_anbar_header" SET "GHABZ_NUMBER" = :receipt_number,
            "NUMBER_tali" = :tally_number, "MODIFY_AT" = SYSDATE, "MODIFY_BY" = :actor
            WHERE "ID_ghabz" = :id""", update)
