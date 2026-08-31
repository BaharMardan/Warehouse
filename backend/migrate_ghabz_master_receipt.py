"""Add the master-receipt (قبض انبار مادر) concept to the database.

The employer needs one receipt covering the whole tally for internal records,
while the same goods are also split across several customer receipts. The stock
trigger forbids that: it sums every receipt of a tally per goods code and caps
the total at the tally, so a master plus its children counts the goods twice and
raises ORA-20001.

This migration makes the master a summary rather than a draw:

* fa_ghabz_anbar_header gains IS_MASTER ('yes'/'no', default 'no').
* TRG_CHK_GHABZ_TALI_LIMIT measures a master receipt on its own -- each line
  still may not exceed the tally's total for that code, so a hand edit cannot
  inflate it -- and excludes masters from the sum it applies to child receipts.

It also carries the soft-delete filters, so this supersedes
migrate_ghabz_trigger_soft_delete.py and is safe to run whether or not that one
was applied:

    receipt lines    AND "d"."IS_DELETED" = 'no'
    receipt headers  AND "h"."IS_DELETED" = 'no'
    tally rows       AND "t"."IS_DELETED" = 'no'

The master always takes GHABZ_SEQ = 0, so it prints as 1405_1503_0 and the
existing UNIQUE (TALI_ID, GHABZ_SEQ) enforces one master per tally with no
extra code.

IMPORTANT: this alters a legacy object. If the APEX application still writes to
these tables, its behaviour changes too. Read the trigger diff before running.

Run once with the API stopped (safe to re-run):

    python migrate_ghabz_master_receipt.py
"""

from app.core.db import get_connection


HEADER_TABLE = "fa_ghabz_anbar_header"
MASTER_COLUMN = "IS_MASTER"
TRIGGER_NAME = "TRG_CHK_GHABZ_TALI_LIMIT"

TRIGGER_SQL = """\
CREATE OR REPLACE EDITIONABLE TRIGGER "TRG_CHK_GHABZ_TALI_LIMIT"
FOR INSERT OR UPDATE ON "FA_ghabz_anbar_DETAILES"
COMPOUND TRIGGER

    TYPE "t_row" IS RECORD (
        "ID_GHABZ_ANBAR_HEADAR"  "FA_ghabz_anbar_DETAILES"."ID_GHABZ_ANBAR_HEADAR"%TYPE,
        "CODE_KALA"              "FA_ghabz_anbar_DETAILES"."code_kala"%TYPE
    );

    TYPE "t_rows" IS TABLE OF "t_row";
    "g_rows" "t_rows" := "t_rows"();

    BEFORE EACH ROW IS
    BEGIN
        "g_rows".EXTEND;
        "g_rows"("g_rows".COUNT)."ID_GHABZ_ANBAR_HEADAR" := :NEW."ID_GHABZ_ANBAR_HEADAR";
        "g_rows"("g_rows".COUNT)."CODE_KALA"             := :NEW."code_kala";
    END BEFORE EACH ROW;

    AFTER STATEMENT IS

        "v_tali_id"               "FA_TALI_HEADER"."ID_TALI"%TYPE;
        "v_is_master"             "fa_ghabz_anbar_header"."IS_MASTER"%TYPE;

        "v_sum_number"            NUMBER;
        "v_sum_weight"            NUMBER;
        "v_sum_weight_baskol"     NUMBER;

        "v_tali_number"           NUMBER;
        "v_tali_weight"           NUMBER;
        "v_tali_weight_baskol"    NUMBER;

    BEGIN
        FOR i IN 1 .. "g_rows".COUNT LOOP

            BEGIN
                SELECT "h"."TALI_ID", NVL("h"."IS_MASTER", 'no')
                INTO "v_tali_id", "v_is_master"
                FROM "fa_ghabz_anbar_header" "h"
                WHERE "h"."ID_ghabz" = "g_rows"(i)."ID_GHABZ_ANBAR_HEADAR";

            EXCEPTION WHEN NO_DATA_FOUND THEN
                RAISE_APPLICATION_ERROR(
                    -20010,
                    'برای قبض انبار با ID = ' || "g_rows"(i)."ID_GHABZ_ANBAR_HEADAR" ||
                    ' هیچ رکورد هدر یافت نشد'
                );
            END;

            -- A master receipt is a summary of the whole tally, not a draw
            -- against it. It is measured on its own so that it can coexist with
            -- the customer receipts that split the same goods; those are summed
            -- with each other and exclude the master.
            IF "v_is_master" = 'yes' THEN

                SELECT
                    NVL(SUM("d"."NUMBER_KALA"),0),
                    NVL(SUM("d"."WEIGHTE_asnad"),0),
                    NVL(SUM("d"."WEIGHTE_BASKOL"),0)
                INTO
                    "v_sum_number",
                    "v_sum_weight",
                    "v_sum_weight_baskol"
                FROM "FA_ghabz_anbar_DETAILES" "d"
                WHERE "d"."ID_GHABZ_ANBAR_HEADAR" = "g_rows"(i)."ID_GHABZ_ANBAR_HEADAR"
                  AND "d"."code_kala" = "g_rows"(i)."CODE_KALA"
                  AND "d"."IS_DELETED" = 'no';

            ELSE

                SELECT
                    NVL(SUM("d"."NUMBER_KALA"),0),
                    NVL(SUM("d"."WEIGHTE_asnad"),0),
                    NVL(SUM("d"."WEIGHTE_BASKOL"),0)
                INTO
                    "v_sum_number",
                    "v_sum_weight",
                    "v_sum_weight_baskol"
                FROM "FA_ghabz_anbar_DETAILES" "d"
                JOIN "fa_ghabz_anbar_header" "h"
                  ON "h"."ID_ghabz" = "d"."ID_GHABZ_ANBAR_HEADAR"
                WHERE "h"."TALI_ID" = "v_tali_id"
                  AND "d"."code_kala" = "g_rows"(i)."CODE_KALA"
                  AND "d"."IS_DELETED" = 'no'
                  AND "h"."IS_DELETED" = 'no'
                  AND NVL("h"."IS_MASTER", 'no') = 'no';

            END IF;

            SELECT
                NVL(SUM("t"."NUMBER_KALA"),0),
                NVL(SUM("t"."WEIGHTE"),0),
                NVL(SUM("t"."WEIGHTE_BASKOL"),0)
            INTO
                "v_tali_number",
                "v_tali_weight",
                "v_tali_weight_baskol"
            FROM "FA_TALI_DETAILES" "t"
            WHERE "t"."ID_HEADERS_TALI" = "v_tali_id"
              AND "t"."CODE_GROUPE_KALA" = "g_rows"(i)."CODE_KALA"
              AND "t"."IS_DELETED" = 'no';

            IF "v_tali_number" = 0
            AND "v_tali_weight" = 0
            AND "v_tali_weight_baskol" = 0 THEN
                RAISE_APPLICATION_ERROR(
                    -20011,
                    'برای کالا با کد ' || "g_rows"(i)."CODE_KALA" ||
                    ' در تالی هیچ مقدار مجازی تعریف نشده است'
                );
            END IF;

            IF "v_sum_number" > "v_tali_number" THEN
                RAISE_APPLICATION_ERROR(
                    -20001,
                    'تعداد ثبت شده برای کالا از مجموع مقدار مجاز در تالی بیشتر است'
                );
            END IF;

            IF "v_sum_weight" > "v_tali_weight" THEN
                RAISE_APPLICATION_ERROR(
                    -20002,
                    'وزن اسناد ثبت شده برای کالا از مجموع مقدار مجاز در تالی بیشتر است'
                );
            END IF;

            IF "v_sum_weight_baskol" > "v_tali_weight_baskol" THEN
                RAISE_APPLICATION_ERROR(
                    -20003,
                    'وزن باسکول ثبت شده برای کالا از مجموع مقدار مجاز در تالی بیشتر است'
                );
            END IF;

        END LOOP;

    END AFTER STATEMENT;

END "TRG_CHK_GHABZ_TALI_LIMIT";
"""


def _resolve_table(cursor, requested: str) -> str:
    cursor.execute("SELECT TABLE_NAME FROM USER_TABLES")
    known = {str(row[0]).casefold(): str(row[0]) for row in cursor.fetchall()}
    table = known.get(requested.casefold())
    if table is None:
        raise RuntimeError(f"Table {requested} does not exist")
    return table


def _column(cursor, table: str, column: str):
    cursor.execute(
        """
        SELECT COLUMN_NAME, DATA_TYPE, CHAR_LENGTH, NULLABLE
          FROM USER_TAB_COLUMNS
         WHERE TABLE_NAME = :t AND UPPER(COLUMN_NAME) = :c
        """,
        {"t": table, "c": column.upper()},
    )
    return cursor.fetchone()


def _add_master_column(cursor) -> int:
    """Add IS_MASTER, defaulting every existing receipt to a child."""
    table = _resolve_table(cursor, HEADER_TABLE)
    existing = _column(cursor, table, MASTER_COLUMN)

    if existing is None:
        cursor.execute(
            f'ALTER TABLE "{table}" ADD ("{MASTER_COLUMN}" '
            f"VARCHAR2(3 CHAR) DEFAULT 'no')"
        )
        print(f"OK  : added {table}.{MASTER_COLUMN}")
        changed = 1
    else:
        print(f"SKIP: {table}.{existing[0]} already exists ({existing[1]})")
        changed = 0

    # DEFAULT only applies to new rows, so existing receipts need the backfill.
    cursor.execute(
        f'UPDATE "{table}" SET "{MASTER_COLUMN}" = \'no\' '
        f'WHERE "{MASTER_COLUMN}" IS NULL'
    )
    if cursor.rowcount:
        print(f"OK  : marked {cursor.rowcount} existing receipt(s) as non-master")
        changed += 1

    cursor.execute(
        f"""
        SELECT COUNT(*) FROM "{table}"
         WHERE "{MASTER_COLUMN}" NOT IN ('yes', 'no')
        """
    )
    stray = int(cursor.fetchone()[0])
    if stray:
        raise RuntimeError(
            f"{stray} row(s) hold a value other than 'yes'/'no' in {MASTER_COLUMN}"
        )
    return changed


def _replace_trigger(cursor) -> None:
    cursor.execute(
        "SELECT STATUS FROM USER_TRIGGERS WHERE TRIGGER_NAME = :n",
        {"n": TRIGGER_NAME},
    )
    before = cursor.fetchone()
    if before is None:
        raise RuntimeError(
            f"{TRIGGER_NAME} does not exist -- refusing to create it blindly. "
            "Check that you are connected to the right schema."
        )
    print(f"before: {TRIGGER_NAME} is {before[0]}")

    cursor.execute(TRIGGER_SQL)

    cursor.execute(
        "SELECT LINE, POSITION, TEXT FROM USER_ERRORS "
        "WHERE NAME = :n AND TYPE = 'TRIGGER' ORDER BY SEQUENCE",
        {"n": TRIGGER_NAME},
    )
    errors = cursor.fetchall()
    if errors:
        for line, position, text in errors:
            print(f"  ERROR line {line}:{position} {text}")
        raise RuntimeError("the replacement trigger did not compile")

    cursor.execute(f'ALTER TRIGGER "{TRIGGER_NAME}" ENABLE')
    cursor.execute(
        "SELECT STATUS FROM USER_TRIGGERS WHERE TRIGGER_NAME = :n",
        {"n": TRIGGER_NAME},
    )
    print(f"after : {TRIGGER_NAME} is {cursor.fetchone()[0]}")


def main() -> None:
    with get_connection() as connection:
        with connection.cursor() as cursor:
            _add_master_column(cursor)
            # The trigger references IS_MASTER via %TYPE, so the column must
            # exist and be committed-visible before it will compile.
            connection.commit()
            _replace_trigger(cursor)
        connection.commit()

    print("done -- master receipts may now coexist with their child receipts")


if __name__ == "__main__":
    main()
