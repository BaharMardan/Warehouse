"""Make HS Code the only Ghabz allotment/grouping key.

Run once with the API stopped, after the existing Ghabz numbering/master
migrations:

    python migrate_ghabz_hscode_groups.py

The migration validates existing active receipt lines before changing any
constraint. It refuses to continue when one receipt already contains multiple
active rows for the same normalized HS Code; those historical conflicts need a
business decision and must not be merged silently.
"""

import oracledb

from app.core.config import settings


DETAILS_TABLE = "FA_ghabz_anbar_DETAILES"
TRIGGER_NAME = "TRG_CHK_GHABZ_TALI_LIMIT"
HS_INDEX = "UQ_GHABZ_HEADER_HSCODE"


TRIGGER_SQL = r'''
CREATE OR REPLACE EDITIONABLE TRIGGER "TRG_CHK_GHABZ_TALI_LIMIT"
FOR INSERT OR UPDATE ON "FA_ghabz_anbar_DETAILES"
COMPOUND TRIGGER

    TYPE "t_row" IS RECORD (
        "ID_GHABZ_ANBAR_HEADAR" "FA_ghabz_anbar_DETAILES"."ID_GHABZ_ANBAR_HEADAR"%TYPE,
        "HSCODE"                "FA_ghabz_anbar_DETAILES"."HSCODE"%TYPE
    );
    TYPE "t_rows" IS TABLE OF "t_row";
    "g_rows" "t_rows" := "t_rows"();

    BEFORE EACH ROW IS
    BEGIN
        IF NVL(:NEW."IS_DELETED", 'no') = 'no' THEN
            IF TRIM(:NEW."HSCODE") IS NULL THEN
                RAISE_APPLICATION_ERROR(
                    -20012,
                    'برای صدور قبض انبار، HS Code الزامی است'
                );
            END IF;

            "g_rows".EXTEND;
            "g_rows"("g_rows".COUNT)."ID_GHABZ_ANBAR_HEADAR" :=
                :NEW."ID_GHABZ_ANBAR_HEADAR";
            "g_rows"("g_rows".COUNT)."HSCODE" := UPPER(TRIM(:NEW."HSCODE"));
        END IF;
    END BEFORE EACH ROW;

    AFTER STATEMENT IS
        "v_tali_id"             "FA_TALI_HEADER"."ID_TALI"%TYPE;
        "v_is_master"           "fa_ghabz_anbar_header"."IS_MASTER"%TYPE;
        "v_sum_number"          NUMBER;
        "v_sum_weight"          NUMBER;
        "v_sum_weight_baskol"   NUMBER;
        "v_tali_number"         NUMBER;
        "v_tali_weight"         NUMBER;
        "v_tali_weight_baskol"  NUMBER;
    BEGIN
        IF "g_rows".COUNT > 0 THEN
            FOR i IN 1 .. "g_rows".COUNT LOOP
                BEGIN
                    SELECT "h"."TALI_ID", NVL("h"."IS_MASTER", 'no')
                      INTO "v_tali_id", "v_is_master"
                      FROM "fa_ghabz_anbar_header" "h"
                     WHERE "h"."ID_ghabz" =
                           "g_rows"(i)."ID_GHABZ_ANBAR_HEADAR";
                EXCEPTION WHEN NO_DATA_FOUND THEN
                    RAISE_APPLICATION_ERROR(
                        -20010,
                        'برای قبض انبار با ID = ' ||
                        "g_rows"(i)."ID_GHABZ_ANBAR_HEADAR" ||
                        ' هیچ رکورد هدر یافت نشد'
                    );
                END;

                IF "v_is_master" = 'yes' THEN
                    SELECT NVL(SUM("d"."NUMBER_KALA"), 0),
                           NVL(SUM("d"."WEIGHTE_asnad"), 0),
                           NVL(SUM("d"."WEIGHTE_BASKOL"), 0)
                      INTO "v_sum_number", "v_sum_weight", "v_sum_weight_baskol"
                      FROM "FA_ghabz_anbar_DETAILES" "d"
                     WHERE "d"."ID_GHABZ_ANBAR_HEADAR" =
                           "g_rows"(i)."ID_GHABZ_ANBAR_HEADAR"
                       AND UPPER(TRIM("d"."HSCODE")) = "g_rows"(i)."HSCODE"
                       AND "d"."IS_DELETED" = 'no';
                ELSE
                    SELECT NVL(SUM("d"."NUMBER_KALA"), 0),
                           NVL(SUM("d"."WEIGHTE_asnad"), 0),
                           NVL(SUM("d"."WEIGHTE_BASKOL"), 0)
                      INTO "v_sum_number", "v_sum_weight", "v_sum_weight_baskol"
                      FROM "FA_ghabz_anbar_DETAILES" "d"
                      JOIN "fa_ghabz_anbar_header" "h"
                        ON "h"."ID_ghabz" = "d"."ID_GHABZ_ANBAR_HEADAR"
                     WHERE "h"."TALI_ID" = "v_tali_id"
                       AND UPPER(TRIM("d"."HSCODE")) = "g_rows"(i)."HSCODE"
                       AND "d"."IS_DELETED" = 'no'
                       AND "h"."IS_DELETED" = 'no'
                       AND NVL("h"."IS_MASTER", 'no') = 'no';
                END IF;

                SELECT NVL(SUM("t"."NUMBER_KALA"), 0),
                       NVL(SUM("t"."WEIGHTE"), 0),
                       NVL(SUM("t"."WEIGHTE_BASKOL"), 0)
                  INTO "v_tali_number", "v_tali_weight", "v_tali_weight_baskol"
                  FROM "FA_TALI_DETAILES" "t"
                 WHERE "t"."ID_HEADERS_TALI" = "v_tali_id"
                   AND UPPER(TRIM("t"."HSCODE")) = "g_rows"(i)."HSCODE"
                   AND "t"."IS_DELETED" = 'no';

                IF "v_tali_number" = 0
                   AND "v_tali_weight" = 0
                   AND "v_tali_weight_baskol" = 0 THEN
                    RAISE_APPLICATION_ERROR(
                        -20011,
                        'برای HS Code ' || "g_rows"(i)."HSCODE" ||
                        ' در تالی هیچ مقدار مجازی تعریف نشده است'
                    );
                END IF;
                IF "v_sum_number" > "v_tali_number" THEN
                    RAISE_APPLICATION_ERROR(-20001,
                        'تعداد ثبت شده برای HS Code از مجموع مقدار مجاز در تالی بیشتر است');
                END IF;
                IF "v_sum_weight" > "v_tali_weight" THEN
                    RAISE_APPLICATION_ERROR(-20002,
                        'وزن اسناد ثبت شده برای HS Code از مجموع مقدار مجاز در تالی بیشتر است');
                END IF;
                IF "v_sum_weight_baskol" > "v_tali_weight_baskol" THEN
                    RAISE_APPLICATION_ERROR(-20003,
                        'وزن باسکول ثبت شده برای HS Code از مجموع مقدار مجاز در تالی بیشتر است');
                END IF;
            END LOOP;
        END IF;
    END AFTER STATEMENT;
END "TRG_CHK_GHABZ_TALI_LIMIT";
'''


def _code(exc: oracledb.DatabaseError) -> int | None:
    return getattr(exc.args[0], "code", None)


def _drop_constraint_if_present(cursor, name: str) -> None:
    cursor.execute(
        "SELECT COUNT(*) FROM USER_CONSTRAINTS WHERE CONSTRAINT_NAME = :name",
        {"name": name},
    )
    if cursor.fetchone()[0]:
        cursor.execute(
            f'ALTER TABLE "{DETAILS_TABLE}" DROP CONSTRAINT "{name}"'
        )
        print(f"OK  : dropped {name}")


def _validate_existing_rows(cursor) -> None:
    cursor.execute(
        f'''
        SELECT "ID_GHABZ_ANBAR_HEADAR", UPPER(TRIM("HSCODE")), COUNT(*)
          FROM "{DETAILS_TABLE}"
         WHERE "IS_DELETED" = 'no'
           AND TRIM("HSCODE") IS NOT NULL
         GROUP BY "ID_GHABZ_ANBAR_HEADAR", UPPER(TRIM("HSCODE"))
        HAVING COUNT(*) > 1
         ORDER BY "ID_GHABZ_ANBAR_HEADAR", UPPER(TRIM("HSCODE"))
        '''
    )
    conflicts = cursor.fetchmany(20)
    if conflicts:
        sample = ", ".join(
            f"receipt={header}, HS={hs}, rows={count}"
            for header, hs, count in conflicts
        )
        raise RuntimeError(
            "Existing active Ghabz rows conflict with HS-Code grouping. "
            "Resolve them before retrying: " + sample
        )


def _create_unique_index(cursor) -> None:
    cursor.execute(
        "SELECT COUNT(*) FROM USER_INDEXES WHERE INDEX_NAME = :name",
        {"name": HS_INDEX},
    )
    if cursor.fetchone()[0]:
        print(f"SKIP: {HS_INDEX} already exists")
        return
    cursor.execute(
        f'''
        CREATE UNIQUE INDEX "{HS_INDEX}"
            ON "{DETAILS_TABLE}" (
                CASE WHEN "IS_DELETED" = 'no'
                        AND TRIM("HSCODE") IS NOT NULL
                    THEN "ID_GHABZ_ANBAR_HEADAR" END,
                CASE WHEN "IS_DELETED" = 'no'
                        AND TRIM("HSCODE") IS NOT NULL
                    THEN UPPER(TRIM("HSCODE")) END
            )
        '''
    )
    print(f"OK  : created {HS_INDEX}")


def main() -> None:
    with oracledb.connect(
        user=settings.oracle_user,
        password=settings.oracle_password,
        dsn=settings.oracle_dsn,
    ) as conn:
        with conn.cursor() as cursor:
            cursor.execute(
                "SELECT COUNT(*) FROM USER_TAB_COLUMNS "
                "WHERE TABLE_NAME = :table_name AND COLUMN_NAME = 'HSCODE'",
                {"table_name": DETAILS_TABLE},
            )
            if not cursor.fetchone()[0]:
                raise RuntimeError(
                    f"{DETAILS_TABLE}.HSCODE is missing; run migrate_ghabz_numbering.py first"
                )

            _validate_existing_rows(cursor)
            _create_unique_index(cursor)
            _drop_constraint_if_present(cursor, "FA_CON_تکرار_کدکلا")
            _drop_constraint_if_present(cursor, "UQ_GHABZ_CODE_PACKAGE")

            cursor.execute(TRIGGER_SQL)
            cursor.execute(
                "SELECT LINE, POSITION, TEXT FROM USER_ERRORS "
                "WHERE NAME = :name AND TYPE = 'TRIGGER' ORDER BY SEQUENCE",
                {"name": TRIGGER_NAME},
            )
            errors = cursor.fetchall()
            if errors:
                rendered = "\n".join(
                    f"line {line}:{position} {message}" for line, position, message in errors
                )
                raise RuntimeError("Trigger compilation failed:\n" + rendered)
            cursor.execute(f'ALTER TRIGGER "{TRIGGER_NAME}" ENABLE')

        conn.commit()
    print("done -- Ghabz rows now group and validate only by normalized HS Code")


if __name__ == "__main__":
    main()
