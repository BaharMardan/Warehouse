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


def choose_tally_number(cursor, supplied):
    from fastapi import HTTPException
    # Serialize creates with mode changes; the existing DB unique key is also retained.
    manual = manual_numbering(cursor, lock=True)
    if manual:
        value = str(supplied or '').strip().translate(str.maketrans('۰۱۲۳۴۵۶۷۸۹٠١٢٣٤٥٦٧٨٩', '01234567890123456789'))
        if not value.isascii() or not value.isdigit() or len(value) > 15 or int(value) <= 0:
            raise HTTPException(422, 'شماره تالی را به‌صورت عدد صحیح مثبت، حداکثر ۱۵ رقم وارد کنید')
        value = str(int(value))
        cursor.execute('SELECT 1 FROM "FA_TALI_HEADER" WHERE "TALI_NUMBER" = :tally_number', {'tally_number': value})
        if cursor.fetchone():
            raise HTTPException(409, 'این شماره تالی قبلاً ثبت شده است')
        return value
    while True:
        value = allocate_next_tally_number(cursor)
        cursor.execute('SELECT 1 FROM "FA_TALI_HEADER" WHERE "TALI_NUMBER" = :tally_number', {'tally_number': value})
        if not cursor.fetchone():
            return value
