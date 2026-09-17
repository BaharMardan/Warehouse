"""Add the operator / warehouse-keeper handoff to FA_TALI_HEADER.

    HANDOFF_STEP        'operator' | 'keeper' | 'returned'; NOT NULL, default 'operator'
    SENT_TO_KEEPER_AT   when the operator sent it       SENT_TO_KEEPER_BY  FA_USERS.ID
    RETURNED_AT         when the keeper sent it back    RETURNED_BY        FA_USERS.ID
    IS_VOLUMETRIC       «آیا کالا حجمی است؟»: 'yes' | 'no'; NULL until answered
    VOLUMETRIC_PALLETS  pallet count; only with 'yes', a whole number from 1

Existing tallies: a tally with an active receipt or invoice starts as 'returned',
so issuing and invoicing keep working for it. RETURNED_AT stays NULL for those,
which is how the screens tell a pre-handoff tally from one a keeper returned.
Every other tally starts at 'operator' and follows the new flow.

Safe to re-run: columns and constraints are added only when missing, and the
backfill only touches tallies at 'operator' that were never sent or returned.
Under the new rules such a tally cannot have a receipt, so a re-run changes
nothing that went through the handoff.

Last, a smoke test inserts a throwaway tally and goods row (negative ids consume
no identity values), walks them through send, answer, return and the receipt
guard with the exact SQL the API runs, checks that the constraints reject bad
values, and rolls everything back.

Run once with the API stopped:

    python add_tally_handoff.py
"""

import oracledb

from app.core.db import get_connection
from app.routers import tally_handoff as handoff
from app.routers.ghabz import FROM_TALLY_READ
from app.routers.kartabl import KEEPER_QUEUE_SQL
from app.services import tally_handoff as rules

TABLE = "FA_TALI_HEADER"

# (column, definition, expected DATA_TYPE)
COLUMNS: list[tuple[str, str, str]] = [
    ("HANDOFF_STEP", "VARCHAR2(20 CHAR) DEFAULT 'operator' NOT NULL", "VARCHAR2"),
    ("SENT_TO_KEEPER_AT", "DATE", "DATE"),
    ("SENT_TO_KEEPER_BY", "NUMBER", "NUMBER"),
    ("RETURNED_AT", "DATE", "DATE"),
    ("RETURNED_BY", "NUMBER", "NUMBER"),
    ("IS_VOLUMETRIC", "VARCHAR2(3 CHAR)", "VARCHAR2"),
    ("VOLUMETRIC_PALLETS", "NUMBER", "NUMBER"),
]

CONSTRAINTS: list[tuple[str, str]] = [
    ("CK_FA_TALI_HANDOFF_STEP", "\"HANDOFF_STEP\" IN ('operator', 'keeper', 'returned')"),
    ("CK_FA_TALI_IS_VOLUMETRIC", "\"IS_VOLUMETRIC\" IN ('yes', 'no')"),
    (
        "CK_FA_TALI_VOLUMETRIC_PALLETS",
        "\"VOLUMETRIC_PALLETS\" IS NULL OR (\"IS_VOLUMETRIC\" = 'yes' "
        "AND \"VOLUMETRIC_PALLETS\" >= 1 AND \"VOLUMETRIC_PALLETS\" = TRUNC(\"VOLUMETRIC_PALLETS\"))",
    ),
]

BACKFILL_SQL = """
UPDATE "FA_TALI_HEADER" h
   SET h."HANDOFF_STEP" = 'returned'
 WHERE h."HANDOFF_STEP" = 'operator'
   AND h."SENT_TO_KEEPER_AT" IS NULL
   AND h."RETURNED_AT" IS NULL
   AND (
        EXISTS (SELECT 1 FROM "fa_ghabz_anbar_header" g
                 WHERE g."TALI_ID" = h."ID_TALI" AND g."IS_DELETED" = 'no')
     OR EXISTS (SELECT 1 FROM "FA_SORAT_HESAB_HEADER" i
                 WHERE i."TALI_ID_HEADER" = h."ID_TALI" AND i."SORAT_IS_DELETED" = 'no')
   )
"""

STEP_COUNTS_SQL = """
SELECT "HANDOFF_STEP", COUNT(*)
  FROM "FA_TALI_HEADER"
 WHERE "IS_DELETED" = 'no'
 GROUP BY "HANDOFF_STEP"
 ORDER BY "HANDOFF_STEP"
"""

SMOKE_ID = -1
failed: list[str] = []


def ok(label: str) -> None:
    print(f"OK  : {label}")


def fail(label: str, detail: object = "") -> None:
    print(f"FAIL: {label}" + (f" ({detail})" if detail != "" else ""))
    failed.append(label)


def check(label: str, condition: bool, detail: object = "") -> None:
    ok(label) if condition else fail(label, detail)


def _existing_columns(cursor) -> dict[str, str]:
    cursor.execute(
        "SELECT COLUMN_NAME, DATA_TYPE FROM USER_TAB_COLUMNS WHERE TABLE_NAME = :t", {"t": TABLE}
    )
    return {str(name): str(kind) for name, kind in cursor.fetchall()}


def add_columns(cursor) -> None:
    existing = _existing_columns(cursor)
    for column, definition, data_type in COLUMNS:
        if column in existing:
            check(f"{TABLE}.{column} already exists as {existing[column]}",
                  existing[column] == data_type, f"expected {data_type}")
            continue
        try:
            cursor.execute(f'ALTER TABLE "{TABLE}" ADD ("{column}" {definition})')
            ok(f"added {TABLE}.{column} {definition}")
        except oracledb.DatabaseError as exc:
            fail(f"{TABLE}.{column}", exc)
            return  # later steps need every column


def add_constraints(cursor) -> None:
    cursor.execute(
        "SELECT CONSTRAINT_NAME, STATUS FROM USER_CONSTRAINTS "
        "WHERE TABLE_NAME = :t AND CONSTRAINT_TYPE = 'C'",
        {"t": TABLE},
    )
    existing = {str(name): str(status) for name, status in cursor.fetchall()}
    for name, condition in CONSTRAINTS:
        if name in existing:
            check(f"constraint {name} already exists", existing[name] == "ENABLED", existing[name])
            continue
        try:
            cursor.execute(f'ALTER TABLE "{TABLE}" ADD CONSTRAINT "{name}" CHECK ({condition})')
            ok(f"added constraint {name}")
        except oracledb.DatabaseError as exc:
            fail(f"constraint {name}", exc)


def backfill(connection, cursor) -> None:
    cursor.execute(BACKFILL_SQL)
    ok(f"backfill: {cursor.rowcount} tally(ies) with a receipt or invoice set to 'returned'")
    connection.commit()
    cursor.execute(STEP_COUNTS_SQL)
    counts = ", ".join(f"{step}={count}" for step, count in cursor.fetchall()) or "no active tallies"
    ok(f"active tallies by step: {counts}")


def _rejected(cursor, label: str, sql: str) -> None:
    """The statement must fail on a check constraint; Oracle undoes just that statement."""
    try:
        cursor.execute(sql, {"id": SMOKE_ID})
        fail(f"constraint rejects {label}", "statement succeeded")
    except oracledb.DatabaseError as exc:
        check(f"constraint rejects {label}", "ORA-02290" in str(exc), str(exc).splitlines()[0])


def smoke_test(connection) -> None:
    with connection.cursor() as cursor:
        try:
            cursor.execute('INSERT INTO "FA_TALI_HEADER" ("ID_TALI", "IS_DELETED") VALUES (:id, \'no\')',
                           {"id": SMOKE_ID})
            state = handoff.read_handoff(cursor, SMOKE_ID)
            check("a new tally starts with the operator", state["step"] == "operator", state["step"])
            check("sending without goods rows is refused",
                  rules.send_to_keeper_error(state["step"], int(state["goods_rows"])) is not None)

            cursor.execute('INSERT INTO "FA_TALI_DETAILES" ("ID_TALI_DETAILS", "ID_HEADERS_TALI", "IS_DELETED") '
                           "VALUES (:id, :id, 'no')", {"id": SMOKE_ID})
            step, _, _ = handoff.lock_tally(cursor, SMOKE_ID)
            cursor.execute(handoff.GOODS_ROWS_SQL, {"tali_id": SMOKE_ID})
            goods = int(cursor.fetchone()[0])
            check("with a goods row the tally may be sent", rules.send_to_keeper_error(step, goods) is None, goods)

            cursor.execute(handoff.SEND_TO_KEEPER_SQL, {"tali_id": SMOKE_ID, "actor_id": 0})
            check("send moved one row", cursor.rowcount == 1, cursor.rowcount)
            state = handoff.read_handoff(cursor, SMOKE_ID)
            check("the tally is with the keeper, time recorded",
                  state["step"] == "keeper" and state["sent_to_keeper_at"] is not None, state)
            cursor.execute(handoff.SEND_TO_KEEPER_SQL, {"tali_id": SMOKE_ID, "actor_id": 0})
            check("sending twice moves nothing", cursor.rowcount == 0, cursor.rowcount)
            cursor.execute(KEEPER_QUEUE_SQL)
            check("the keeper queue counts it", int(cursor.fetchone()[0]) >= 1)

            cursor.execute(FROM_TALLY_READ, {"tid": SMOKE_ID})
            columns = [d[0].lower() for d in cursor.description]
            tally = dict(zip(columns, cursor.fetchone()))
            check("receipts are refused while the keeper holds it",
                  rules.issue_receipt_error(tally.get("handoff_step")) is not None, tally.get("handoff_step"))

            cursor.execute(handoff.SAVE_VOLUMETRIC_SQL,
                           {"tali_id": SMOKE_ID, "is_volumetric": "yes", "volumetric_pallets": None, "actor_id": 0})
            check("«بله» saved before the pallet count", cursor.rowcount == 1, cursor.rowcount)
            step, answer, pallets = handoff.lock_tally(cursor, SMOKE_ID)
            check("returning without pallets is refused",
                  rules.return_to_operator_error(step, answer, pallets) is not None)

            _rejected(cursor, "an unknown step",
                      'UPDATE "FA_TALI_HEADER" SET "HANDOFF_STEP" = \'archived\' WHERE "ID_TALI" = :id')
            _rejected(cursor, "an answer other than yes/no",
                      'UPDATE "FA_TALI_HEADER" SET "IS_VOLUMETRIC" = \'hm\' WHERE "ID_TALI" = :id')
            _rejected(cursor, "pallets on non-volumetric cargo",
                      'UPDATE "FA_TALI_HEADER" SET "IS_VOLUMETRIC" = \'no\', "VOLUMETRIC_PALLETS" = 5 WHERE "ID_TALI" = :id')
            _rejected(cursor, "a fractional pallet count",
                      'UPDATE "FA_TALI_HEADER" SET "VOLUMETRIC_PALLETS" = 2.5 WHERE "ID_TALI" = :id')

            cursor.execute(handoff.SAVE_VOLUMETRIC_SQL,
                           {"tali_id": SMOKE_ID, "is_volumetric": "yes", "volumetric_pallets": 12, "actor_id": 0})
            step, answer, pallets = handoff.lock_tally(cursor, SMOKE_ID)
            check("pallet count saved and return allowed",
                  pallets == 12 and rules.return_to_operator_error(step, answer, pallets) is None, (answer, pallets))

            cursor.execute(handoff.RETURN_TO_OPERATOR_SQL, {"tali_id": SMOKE_ID, "actor_id": 0})
            check("return moved one row", cursor.rowcount == 1, cursor.rowcount)
            state = handoff.read_handoff(cursor, SMOKE_ID)
            check("returned, time recorded, answer kept",
                  state["step"] == "returned" and state["returned_at"] is not None
                  and state["is_volumetric"] == "yes" and int(state["volumetric_pallets"]) == 12, state)
            cursor.execute(FROM_TALLY_READ, {"tid": SMOKE_ID})
            tally = dict(zip([d[0].lower() for d in cursor.description], cursor.fetchone()))
            check("receipts are allowed once returned", rules.issue_receipt_error(tally.get("handoff_step")) is None)
        except Exception as exc:
            fail("smoke test stopped", exc)
        finally:
            connection.rollback()
            cursor.execute('SELECT COUNT(*) FROM "FA_TALI_HEADER" WHERE "ID_TALI" = :id', {"id": SMOKE_ID})
            check("smoke test rows rolled back", int(cursor.fetchone()[0]) == 0)


def main() -> None:
    with get_connection() as connection:
        # Oracle commits DDL immediately, so a failure below cannot be rolled back;
        # re-running picks up where it stopped.
        with connection.cursor() as cursor:
            add_columns(cursor)
            if not failed:
                add_constraints(cursor)
            if not failed:
                backfill(connection, cursor)
        if not failed:
            smoke_test(connection)

    print(f"Summary: failed={len(failed)}")
    if failed:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
