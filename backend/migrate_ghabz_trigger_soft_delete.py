"""Make TRG_CHK_GHABZ_TALI_LIMIT respect soft deletes.

As shipped by the APEX system, the trigger sums receipt quantities per goods
code with no IS_DELETED filter on either side. Two consequences:

* Deleting a receipt line does NOT return its quantity to the tally. The goods
  never left the warehouse, but the allotment stays consumed forever, so the
  quantity can never be re-issued on a corrected receipt.
* Deleting a tally row does not reduce the allotment either, so the trigger
  keeps honouring quantities the tally no longer lists.

This replaces the trigger with the same logic plus three filters:

    receipt lines    AND "d"."IS_DELETED" = 'no'
    receipt headers  AND "h"."IS_DELETED" = 'no'
    tally rows       AND "t"."IS_DELETED" = 'no'

Everything else -- the compound structure, the error codes, the Persian
messages -- is byte-identical to the extracted source, so the only behaviour
that changes is which rows count.

IMPORTANT: this alters a legacy object. If the APEX application still writes to
these tables, its behaviour changes too, in the same direction. Read the diff
before running.

Run once with the API stopped (safe to re-run -- CREATE OR REPLACE is idempotent):

    python migrate_ghabz_trigger_soft_delete.py

To go back, re-run the original DDL from sql/schema/06_triggers.sql.
"""

from app.core.db import get_connection


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

        "v_sum_number"            NUMBER;
        "v_sum_weight"            NUMBER;
        "v_sum_weight_baskol"     NUMBER;

        "v_tali_number"           NUMBER;
        "v_tali_weight"           NUMBER;
        "v_tali_weight_baskol"    NUMBER;

    BEGIN
        FOR i IN 1 .. "g_rows".COUNT LOOP

            BEGIN
                SELECT "h"."TALI_ID"
                INTO "v_tali_id"
                FROM "fa_ghabz_anbar_header" "h"
                WHERE "h"."ID_ghabz" = "g_rows"(i)."ID_GHABZ_ANBAR_HEADAR";

            EXCEPTION WHEN NO_DATA_FOUND THEN
                RAISE_APPLICATION_ERROR(
                    -20010,
                    'برای قبض انبار با ID = ' || "g_rows"(i)."ID_GHABZ_ANBAR_HEADAR" ||
                    ' هیچ رکورد هدر یافت نشد'
                );
            END;

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
              AND "h"."IS_DELETED" = 'no';

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


def _trigger_state(cursor) -> tuple[str, str] | None:
    cursor.execute(
        """
        SELECT STATUS, TRIGGERING_EVENT
          FROM USER_TRIGGERS
         WHERE TRIGGER_NAME = :name
        """,
        {"name": TRIGGER_NAME},
    )
    row = cursor.fetchone()
    return (str(row[0]), str(row[1])) if row else None


def main() -> None:
    with get_connection() as connection:
        with connection.cursor() as cursor:
            before = _trigger_state(cursor)
            if before is None:
                raise RuntimeError(
                    f"{TRIGGER_NAME} does not exist -- refusing to create it blindly. "
                    "Check that you are connected to the right schema."
                )
            print(f"before: {TRIGGER_NAME} is {before[0]} on {before[1]}")

            cursor.execute(TRIGGER_SQL)

            cursor.execute(
                """
                SELECT COUNT(*) FROM USER_ERRORS
                 WHERE NAME = :name AND TYPE = 'TRIGGER'
                """,
                {"name": TRIGGER_NAME},
            )
            errors = int(cursor.fetchone()[0])
            if errors:
                cursor.execute(
                    """
                    SELECT LINE, POSITION, TEXT FROM USER_ERRORS
                     WHERE NAME = :name AND TYPE = 'TRIGGER' ORDER BY SEQUENCE
                    """,
                    {"name": TRIGGER_NAME},
                )
                for line, position, text in cursor.fetchall():
                    print(f"  ERROR line {line}:{position} {text}")
                raise RuntimeError("the replacement trigger did not compile")

            cursor.execute(f'ALTER TRIGGER "{TRIGGER_NAME}" ENABLE')
            after = _trigger_state(cursor)
            print(f"after : {TRIGGER_NAME} is {after[0]} on {after[1]}")

        connection.commit()

    print("done -- soft-deleted receipt lines and tally rows no longer count")


if __name__ == "__main__":
    main()
