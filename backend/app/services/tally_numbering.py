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
