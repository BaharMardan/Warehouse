"""Helpers for allocating immutable, yearly Jalali tally numbers."""

from datetime import date

import jdatetime
import oracledb


INSERT_COUNTER_SQL = """
INSERT INTO "FA_TALI_NUMBER_COUNTER" ("JALALI_YEAR", "LAST_NUMBER")
VALUES (:jalali_year, 0)
"""

INCREMENT_COUNTER_SQL = """
UPDATE "FA_TALI_NUMBER_COUNTER"
SET "LAST_NUMBER" = "LAST_NUMBER" + 1
WHERE "JALALI_YEAR" = :jalali_year
RETURNING "LAST_NUMBER" INTO :next_number
"""


def jalali_year_for(gregorian_date: date) -> int:
    """Return the Jalali year for an authoritative Gregorian creation date."""
    return jdatetime.date.fromgregorian(date=gregorian_date).year


def format_tally_number(jalali_year: int, sequence_number: int) -> str:
    return f"{jalali_year}-{sequence_number}"


def _oracle_error_code(exc: BaseException) -> int | None:
    if not exc.args:
        return None
    error = exc.args[0]
    return getattr(error, "code", None)


def allocate_next_tally_number(cursor, jalali_year: int) -> str:
    """Allocate one yearly number using the caller's open Oracle transaction.

    The first transaction for a year inserts its counter row. Concurrent
    transactions block on that primary key; the loser receives ORA-00001 and
    then increments the committed row. The update itself takes a row lock, so
    two successful transactions cannot receive the same sequence number.
    """
    try:
        cursor.execute(INSERT_COUNTER_SQL, {"jalali_year": jalali_year})
    except oracledb.IntegrityError as exc:
        if _oracle_error_code(exc) != 1:  # ORA-00001 is the expected race
            raise

    next_number_var = cursor.var(int)
    cursor.execute(
        INCREMENT_COUNTER_SQL,
        {
            "jalali_year": jalali_year,
            "next_number": next_number_var,
        },
    )
    if cursor.rowcount != 1:
        raise RuntimeError(f"Counter row for Jalali year {jalali_year} was not found")

    value = next_number_var.getvalue()
    if isinstance(value, (list, tuple)):
        value = value[0]
    return format_tally_number(jalali_year, int(value))
