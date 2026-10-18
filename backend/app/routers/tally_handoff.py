"""Operator / warehouse-keeper handoff endpoints for one tally.

    GET  /tally/{id}/handoff                     current step, who moved it and when, the answer
    POST /tally/{id}/handoff/send-to-keeper      operator: needs tally.edit and a goods row
    PUT  /tally/{id}/handoff/volumetric          keeper: «آیا کالا حجمی است؟» and the pallet count
    POST /tally/{id}/handoff/return-to-operator  keeper: needs the answer (and pallets for «بله»)

The rules live in app/services/tally_handoff.py. Every change locks the tally row
with SELECT ... FOR UPDATE first, the same lock receipt numbering takes, so a
double click or two users acting at once cannot move a tally twice.

The SQL is kept in module constants so add_tally_handoff.py runs the exact same
statements against the real schema in its rollback-only smoke test.
"""

from typing import Literal

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from app.services import row_pallets as rp

from app.auth.deps import require_permission
from app.core.db import get_connection
from app.services import tally_handoff as rules
from app.services import receipt_db, handoff_notifications

router = APIRouter(prefix="/tally", tags=["tally_handoff"])


class CargoTypeInput(BaseModel):
    cargo_type: Literal["weight", "volumetric", "container"]
    volumetric_pallets: int | None = None


HANDOFF_SQL = """
SELECT h."ID_TALI" AS id_tali,
       h."HANDOFF_STEP" AS step,
       h."SENT_TO_KEEPER_AT" AS sent_to_keeper_at,
       TO_CHAR(
         FROM_TZ(CAST(h."SENT_TO_KEEPER_AT" AS TIMESTAMP), 'UTC') AT TIME ZONE 'Asia/Tehran',
         'YYYY/MM/DD "ساعت" HH24:MI',
         'NLS_CALENDAR = Persian'
       ) AS sent_to_keeper_at_display,
       NVL(TRIM(sender."FULL_NAME"), sender."USERNAME") AS sent_to_keeper_by,
       h."RETURNED_AT" AS returned_at,
       TO_CHAR(
         FROM_TZ(CAST(h."RETURNED_AT" AS TIMESTAMP), 'UTC') AT TIME ZONE 'Asia/Tehran',
         'YYYY/MM/DD "ساعت" HH24:MI',
         'NLS_CALENDAR = Persian'
       ) AS returned_at_display,
       NVL(TRIM(returner."FULL_NAME"), returner."USERNAME") AS returned_by,
       CASE h."IS_VOLUMETRIC"
         WHEN 'yes' THEN 'volumetric'
         WHEN 'no' THEN 'weight'
         ELSE h."IS_VOLUMETRIC"
       END AS cargo_type,
       h."VOLUMETRIC_PALLETS" AS volumetric_pallets,
       (SELECT COUNT(*)
          FROM "FA_TALI_DETAILES" d
         WHERE d."ID_HEADERS_TALI" = h."ID_TALI"
           AND d."IS_DELETED" = 'no') AS goods_rows
  FROM "FA_TALI_HEADER" h
  LEFT JOIN "FA_USERS" sender ON sender."ID" = h."SENT_TO_KEEPER_BY"
  LEFT JOIN "FA_USERS" returner ON returner."ID" = h."RETURNED_BY"
 WHERE h."ID_TALI" = :tali_id
   AND h."IS_DELETED" = 'no'
"""

LOCK_SQL = """
SELECT "HANDOFF_STEP", "IS_VOLUMETRIC", "VOLUMETRIC_PALLETS"
  FROM "FA_TALI_HEADER"
 WHERE "ID_TALI" = :tali_id
   AND "IS_DELETED" = 'no'
   FOR UPDATE
"""

GOODS_ROWS_SQL = """
SELECT COUNT(*)
  FROM "FA_TALI_DETAILES"
 WHERE "ID_HEADERS_TALI" = :tali_id
   AND "IS_DELETED" = 'no'
"""

# Each UPDATE repeats the step it expects, so even without the lock it could
# only ever move a tally forward from the right place.
SEND_TO_KEEPER_SQL = """
UPDATE "FA_TALI_HEADER"
   SET "HANDOFF_STEP" = 'keeper',
       "SENT_TO_KEEPER_AT" = CAST(SYS_EXTRACT_UTC(SYSTIMESTAMP) AS DATE),
       "SENT_TO_KEEPER_BY" = :actor_id,
       "MODIFY_AT" = SYSDATE,
       "MODIFY_BY" = :actor_id
 WHERE "ID_TALI" = :tali_id
   AND "HANDOFF_STEP" = 'operator'
"""

SAVE_VOLUMETRIC_SQL = """
UPDATE "FA_TALI_HEADER"
   SET "IS_VOLUMETRIC" = :is_volumetric,
       "VOLUMETRIC_PALLETS" = :volumetric_pallets,
       "MODIFY_AT" = SYSDATE,
       "MODIFY_BY" = :actor_id
 WHERE "ID_TALI" = :tali_id

"""

RETURN_TO_OPERATOR_SQL = """
UPDATE "FA_TALI_HEADER"
   SET "HANDOFF_STEP" = 'returned',
       "RETURNED_AT" = CAST(SYS_EXTRACT_UTC(SYSTIMESTAMP) AS DATE),
       "RETURNED_BY" = :actor_id,
       "MODIFY_AT" = SYSDATE,
       "MODIFY_BY" = :actor_id
 WHERE "ID_TALI" = :tali_id
   AND "HANDOFF_STEP" = 'keeper'
"""


def read_handoff(cursor, tali_id: int) -> dict:
    cursor.execute(HANDOFF_SQL, {"tali_id": tali_id})
    columns = [column[0].lower() for column in cursor.description]
    row = cursor.fetchone()
    if row is None:
        raise HTTPException(status_code=404, detail="تالی یافت نشد")
    state = dict(zip(columns, row))
    docs = receipt_db.receipts(cursor, tali_id)
    active = receipt_db.operational(docs)
    locked = any(r["status"] in ("finalized", "invoice_issued") for r in active)
    pending = any(r["status"] in ("created", "sent_to_keeper") for r in active)
    state["pallet_rows"] = rp.tally_rows(cursor, tali_id)
    invoiced = receipt_db.one(cursor, '''SELECT COUNT(*) AS cnt FROM "FA_SORAT_HESAB_HEADER"
        WHERE "TALI_ID_HEADER" = :tid AND NVL("SORAT_IS_DELETED", 'no') = 'no' ''', {'tid': tali_id})
    state["can_edit_pallets"] = not invoiced['cnt'] and not any(r["status"] == "invoice_issued" for r in docs) and (
        locked or pending or state["step"] == "keeper")
    state["active_invoice_count"] = invoiced["cnt"]
    state["can_edit_goods"] = not docs or receipt_db.correction_open(state["step"], docs, invoiced["cnt"])
    state["has_receipts"] = bool(docs)
    state["can_edit_services"] = not locked and (pending if docs else state["step"] == "keeper")
    state["receipt_checklists"] = [
        {"id": r["id"], "number": r["number_text"], "status": r["status"]} for r in active]
    if docs:
        state["step"] = "keeper" if state["can_edit_services"] else "returned"
    return state


def lock_tally(cursor, tali_id: int) -> tuple[str, str | None, int | None]:
    """(step, is_volumetric, pallets) of an active tally, locked until commit; 404 if missing."""
    cursor.execute(LOCK_SQL, {"tali_id": tali_id})
    row = cursor.fetchone()
    if row is None:
        raise HTTPException(status_code=404, detail="تالی یافت نشد")
    step, is_volumetric, pallets = row
    return step, is_volumetric, None if pallets is None else int(pallets)


def _conflict(message: str | None) -> None:
    if message:
        raise HTTPException(status_code=409, detail=message)


@router.get("/{tali_id}/handoff", dependencies=[Depends(require_permission("tally.view"))])
def get_handoff(tali_id: int):
    with get_connection() as connection:
        with connection.cursor() as cursor:
            return read_handoff(cursor, tali_id)


@router.post("/{tali_id}/handoff/send-to-keeper")
def send_to_keeper(tali_id: int, current_user: dict = Depends(require_permission("tally.edit"))):
    with get_connection() as connection:
        with connection.cursor() as cursor:
            step, _, _ = lock_tally(cursor, tali_id)
            cursor.execute(GOODS_ROWS_SQL, {"tali_id": tali_id})
            _conflict(rules.send_to_keeper_error(step, int(cursor.fetchone()[0])))
            if receipt_db.receipts(cursor, tali_id):
                receipt_db.conflict("قبض‌ها به طور خودکار در چک‌لیست نهایی انباردار قرار می‌گیرند")
            cursor.execute(SEND_TO_KEEPER_SQL, {"tali_id": tali_id, "actor_id": int(current_user["id"])})
            handoff_notifications.record(cursor, "keeper", tali_id, int(current_user["id"]))
            connection.commit()
            return read_handoff(cursor, tali_id)


@router.put("/{tali_id}/handoff/volumetric")
def save_volumetric(
    tali_id: int,
    item: CargoTypeInput,
    current_user: dict = Depends(require_permission("tally.services")),
):
    with get_connection() as connection:
        with connection.cursor() as cursor:
            step, _, _ = lock_tally(cursor, tali_id)
            receipt_db.guard_services(cursor, tali_id)
            item.volumetric_pallets = (rp.complete_total(rp.tally_rows(cursor, tali_id))
                                       if item.cargo_type == "volumetric" else None)
            message = rules.cargo_type_error("keeper", item.cargo_type, item.volumetric_pallets)
            if message:
                # Workflow conflicts are handled by guard_services above.
                raise HTTPException(status_code=400, detail=message)
            cursor.execute(SAVE_VOLUMETRIC_SQL, {
                "tali_id": tali_id,
                "is_volumetric": item.cargo_type,
                "volumetric_pallets": item.volumetric_pallets,
                "actor_id": int(current_user["id"]),
            })
            connection.commit()
            return read_handoff(cursor, tali_id)


@router.post("/{tali_id}/handoff/return-to-operator")
def return_to_operator(tali_id: int, current_user: dict = Depends(require_permission("tally.services"))):
    with get_connection() as connection:
        with connection.cursor() as cursor:
            step, is_volumetric, pallets = lock_tally(cursor, tali_id)
            if receipt_db.receipts(cursor, tali_id):
                receipt_db.conflict("ثبت نهایی را از چک‌لیست قبض انجام دهید")
            if is_volumetric in ("yes", "volumetric"):
                if rp.complete_total(rp.tally_rows(cursor, tali_id)) != pallets or not pallets:
                    receipt_db.conflict("تعداد پالت تمام ردیف‌های تالی را تکمیل کنید")
            _conflict(rules.return_to_operator_error(step, is_volumetric, pallets))
            cursor.execute(RETURN_TO_OPERATOR_SQL, {"tali_id": tali_id, "actor_id": int(current_user["id"])})
            handoff_notifications.record(cursor, "operator", tali_id, int(current_user["id"]))
            connection.commit()
            return read_handoff(cursor, tali_id)


class PalletEntry(BaseModel):
    tally_detail_id: int
    pallets: int = Field(strict=True, ge=1, le=100000)


class PalletInput(BaseModel):
    lines: list[PalletEntry]


@router.put("/{tali_id}/handoff/pallets")
def save_row_pallets(tali_id: int, item: PalletInput,
                     current_user: dict = Depends(require_permission("tally.services"))):
    with get_connection() as conn:
        with conn.cursor() as cur:
            _, cargo, total = lock_tally(cur, tali_id)
            state = read_handoff(cur, tali_id)
            if cargo not in ("yes", "volumetric") or not state["can_edit_pallets"]:
                receipt_db.conflict("ویرایش پالت‌های این تالی مجاز نیست")
            locked = any(r['status'] == 'finalized' for r in state['receipt_checklists'])
            try:
                values = rp.validate_counts(state['pallet_rows'],
                    [r.model_dump() for r in item.lines], expected=total if locked else None)
            except ValueError as exc:
                raise HTTPException(422, str(exc)) from exc
            docs = receipt_db.receipts(cur, tali_id)
            if sum((r['pallet_quantity'] or 0) for r in docs if r['is_master'] != 'yes') > sum(values.values()):
                receipt_db.conflict('جمع پالت تالی نباید از پالت قبض‌های تفکیکی کمتر باشد')
            # Existing detailed allocations must still fit their source row.
            used = receipt_db.rows(cur, '''SELECT p."TALLY_DETAIL_ID" AS id, SUM(p."PALLETS") AS pallets
                FROM "FA_RECEIPT_PALLETS" p JOIN "fa_ghabz_anbar_header" h ON h."ID_ghabz" = p."RECEIPT_ID"
                WHERE h."TALI_ID" = :tid AND h."IS_DELETED" = 'no' AND NVL(h."IS_MASTER", 'no') = 'no'
                GROUP BY p."TALLY_DETAIL_ID"''', {'tid': tali_id})
            if any(values.get(int(r['id']), 0) < r['pallets'] for r in used):
                receipt_db.conflict('پالت ردیف نباید از مقدار تخصیص‌یافته به قبض‌ها کمتر شود')
            cur.executemany('''UPDATE "FA_TALI_DETAILES" SET "ROW_PALLETS" = :pallets
                WHERE "ID_TALI_DETAILS" = :id AND "ID_HEADERS_TALI" = :tid''',
                [{'id': k, 'pallets': v, 'tid': tali_id} for k, v in values.items()])
            cur.execute(SAVE_VOLUMETRIC_SQL, {'tali_id': tali_id, 'is_volumetric': 'volumetric',
                'volumetric_pallets': sum(values.values()), 'actor_id': int(current_user['id'])})
            conn.commit()
            return read_handoff(cur, tali_id)


@router.post("/{tali_id}/handoff/previous")
def previous_step(tali_id: int, user: dict = Depends(require_permission("workflow.return"))):
    with get_connection() as conn:
        with conn.cursor() as cur:
            step, _, _ = lock_tally(cur, tali_id)
            if receipt_db.receipts(cur, tali_id):
                receipt_db.conflict("برای بازگشت، از چک‌لیست قبض استفاده کنید")
            target = {"keeper": "operator", "returned": "keeper"}.get(step)
            if target is None:
                receipt_db.conflict("تالی در نخستین مرحله است")
            cur.execute("""UPDATE "FA_TALI_HEADER" SET "HANDOFF_STEP" = :step,
                "RETURNED_AT" = NULL, "RETURNED_BY" = NULL,
                "MODIFY_AT" = SYSDATE, "MODIFY_BY" = :actor WHERE "ID_TALI" = :tid""",
                {"step": target, "actor": user["id"], "tid": tali_id})
            handoff_notifications.record(cur, target, tali_id, int(user["id"]))
            conn.commit()
            return read_handoff(cur, tali_id)
