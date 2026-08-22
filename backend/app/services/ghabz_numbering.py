"""Allocate warehouse-receipt numbers of the form ``<jalali year>_<tally>_<seq>``.

Example: ``1405_866_1`` is the first receipt issued against tally 866, whose
parent tally was created in Jalali year 1405.

Concurrency
-----------
The sequence is ``MAX(GHABZ_SEQ) + 1`` scoped to one tally, which is only safe
if two operators cannot compute that maximum at the same time. Rather than add
a counter table, the allocator locks the *parent tally row* with SELECT ... FOR
UPDATE. Everything that allocates against tally N therefore queues behind that
one row, and the lock is released by the caller's commit or rollback -- so a
failed insert never burns a number. UQ_FA_GHABZ_TALI_SEQ is the database-level
backstop if this logic is ever bypassed.

Soft deletes
------------
The maximum is taken over *every* row for the tally, including soft-deleted
ones. A deleted receipt keeps its number out of circulation permanently: the
number was printed on paper and handed to a customer, so handing the same one
out again would create two different physical documents with one identity.
This also keeps the allocator consistent with UQ_FA_GHABZ_NUMBER, which does
not filter soft deletes either.
"""

from app.services.jalali import jalali_year


# FOR UPDATE without a lock timeout: the transaction is a handful of statements
# long, so a queued operator waits milliseconds.
LOCK_TALLY_SQL = """
SELECT "TALI_NUMBER", "CREATE_AT", "DATE_UNLOADING"
FROM "FA_TALI_HEADER"
WHERE "ID_TALI" = :tali_id
  AND "IS_DELETED" = 'no'
FOR UPDATE
"""

# Deliberately unfiltered by IS_DELETED -- see the module docstring.
NEXT_SEQUENCE_SQL = """
SELECT NVL(MAX("GHABZ_SEQ"), 0) + 1
FROM "fa_ghabz_anbar_header"
WHERE "TALI_ID" = :tali_id
"""

DATABASE_NOW_SQL = "SELECT SYSDATE FROM DUAL"


class TallyNotFound(LookupError):
    """The tally does not exist, or has been soft-deleted."""


class TallyNotNumbered(ValueError):
    """The tally has no TALI_NUMBER, so no receipt number can be built from it."""


def _year_source(cursor, create_at, date_unloading):
    """Pick the date whose Jalali year goes in the receipt number.

    The tally's creation date is the intended anchor. Legacy tallies imported
    from APEX can have a NULL CREATE_AT, so fall back to the unloading date --
    a real business date on the same document -- and only then to today.
    """
    if create_at is not None:
        return create_at
    if date_unloading is not None:
        return date_unloading
    cursor.execute(DATABASE_NOW_SQL)
    return cursor.fetchone()[0]


def allocate_ghabz_number(cursor, tali_id: int) -> tuple[str, int, str]:
    """Lock the tally and allocate its next receipt number.

    Returns ``(ghabz_number, sequence, tali_number)``. The caller owns the
    transaction and must commit for the number to be kept.
    """
    cursor.execute(LOCK_TALLY_SQL, {"tali_id": tali_id})
    row = cursor.fetchone()
    if row is None:
        raise TallyNotFound(f"Tally {tali_id} was not found")

    tali_number, create_at, date_unloading = row
    if tali_number is None or str(tali_number).strip() == "":
        raise TallyNotNumbered(f"Tally {tali_id} has no tally number")
    tali_number = str(tali_number).strip()

    year = jalali_year(_year_source(cursor, create_at, date_unloading))

    cursor.execute(NEXT_SEQUENCE_SQL, {"tali_id": tali_id})
    sequence = int(cursor.fetchone()[0])

    return f"{year}_{tali_number}_{sequence}", sequence, tali_number
