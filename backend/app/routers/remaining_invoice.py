"""Preview and issue independent remaining-cargo invoices under the tally lock."""
import json
from fastapi import APIRouter, Depends, HTTPException
from app.auth.deps import require_permission
from app.core.db import get_connection
from app.services import receipt_db as db
from app.services.remaining_invoice import RemainingInput, RemainingIssue, calculate, serializable
from app.routers.receipt_workflow import INVOICE_SETTINGS_SQL

router = APIRouter(prefix="/ghabz", tags=["remaining-invoice"])
SERVICE_CATALOG_SQL = """SELECT "id_kala_other_service" AS id, "title" AS title, "price" AS price
FROM "fa_kala_other_service" WHERE "IS_DELETED" = 'no' ORDER BY "id_kala_other_service"
"""
ORIGINAL_SQL = '''SELECT h."ID_SORAT" AS id FROM "FA_SORAT_HESAB_HEADER" h
WHERE h."ID_GHABZ_ANBAR" = :rid AND NVL(h."SORAT_IS_DELETED", 'no') = 'no'
AND NOT EXISTS (SELECT 1 FROM "FA_REMAINING_INVOICE" r WHERE r."INVOICE_ID" = h."ID_SORAT")
ORDER BY h."ID_SORAT"'''
GOODS_SQL = '''SELECT d."ID_TALI_DETAILS" AS id, d."DESCRIPTION_KALA" AS description,
 d."HSCODE" AS hscode, p."CODE" AS kala_code, d."ZARIB_MAHAL" AS zarib_mahal,
 d."NUMBER_HAMEL" AS number_hamel, d."WEIGHTE" AS weight_kg
FROM "FA_TALI_DETAILES" d LEFT JOIN "fa_kala_price" p ON p."id_kala_price" = d."CODE_GROUPE_KALA"
WHERE d."ID_HEADERS_TALI" = :tid AND d."IS_DELETED" = 'no' ORDER BY d."ID_TALI_DETAILS"'''
TARIFF_SQL = '''SELECT p."id_kala_price" AS id, p."CODE" AS kala_code, p."goods_group" AS title,
 p."storage_price" AS storage_price,
 (SELECT e."storage_price" FROM "fa_kala_price" e WHERE e."CODE" =
 CASE p."CODE" WHEN '118' THEN '119' WHEN '120' THEN '121' END AND e."IS_DELETED" = 'no') AS excess_storage_price
FROM "fa_kala_price" p WHERE p."CODE" = :code AND p."IS_DELETED" = 'no'
'''
INSURANCE_SQL = '''SELECT NVL(SUM(NVL("PRICE_DETAILS", 0) - NVL("TAKHFIF_DETAILS", 0)), 0) AS amount
FROM "FA_SORA_HESAB_DETAILS" WHERE "ID_SORA_HEADER" = :iid AND "ROW_KIND" = 'insurance'
AND NVL("IS_DELETED", 'N') NOT IN ('Y', 'yes')'''


def original(cur, rid):
    rows = db.rows(cur, ORIGINAL_SQL, {"rid": rid})
    if len(rows) != 1:
        raise HTTPException(409, "برای صدور باقی‌مانده باید یک صورتحساب اصلی فعال برای قبض وجود داشته باشد")
    return rows[0]["id"]


def preview(cur, current, tally, payload):
    iid = original(cur, current["id"])
    goods = db.rows(cur, GOODS_SQL, {"tid": current["tally_id"]})
    source = next((row for row in goods if row["id"] == payload.source_id), None)
    if source is None:
        raise HTTPException(422, "کالا باید از ردیف‌های همین تالی انتخاب شود")
    tariffs = db.rows(cur, TARIFF_SQL, {"code": payload.kala_code.strip()})
    if len(tariffs) != 1:
        raise HTTPException(422, "کد گروه کالا دارای تعرفهٔ یکتا و فعال نیست")
    settings = {row["setting_key"]: row["value_number"] for row in db.rows(cur, INVOICE_SETTINGS_SQL)}
    insurance = db.one(cur, INSURANCE_SQL, {"iid": iid})["amount"]
    try:
        return calculate(payload=payload, source=source, tariff=tariffs[0], cargo=tally.get("is_volumetric"),
            settings=settings, original_id=iid,
            service_catalog=db.rows(cur, SERVICE_CATALOG_SQL) if payload.other_services else [],
            original_insurance=insurance, receipt_id=current["id"], tally_id=current["tally_id"])
    except (ValueError, ArithmeticError, TypeError) as exc:
        raise HTTPException(422, str(exc)) from exc


@router.get("/{receipt_id}/remaining-invoice", dependencies=[Depends(require_permission("invoice.issue"))])
def options(receipt_id: int):
    with get_connection() as conn:
        with conn.cursor() as cur:
            current, _, tally = db.receipt(cur, receipt_id, lock=True)
            iid = original(cur, receipt_id)
            return serializable({"original_invoice_id": iid, "cargo": tally["is_volumetric"],
                "other_services": db.rows(cur, SERVICE_CATALOG_SQL),
                "goods": db.rows(cur, GOODS_SQL, {"tid": current["tally_id"]}),
                "original_insurance": db.one(cur, INSURANCE_SQL, {"iid": iid})["amount"]})


@router.post("/{receipt_id}/remaining-invoice/preview", dependencies=[Depends(require_permission("invoice.issue"))])
def preview_invoice(receipt_id: int, payload: RemainingInput):
    with get_connection() as conn:
        with conn.cursor() as cur:
            current, _, tally = db.receipt(cur, receipt_id, lock=True)
            return preview(cur, current, tally, payload)


@router.post("/{receipt_id}/remaining-invoice", status_code=201)
def issue_invoice(receipt_id: int, payload: RemainingIssue, user: dict = Depends(require_permission("invoice.issue"))):
    with get_connection() as conn:
        with conn.cursor() as cur:
            current, _, tally = db.receipt(cur, receipt_id, lock=True)
            prior = db.one(cur, '''SELECT r."INVOICE_ID" AS id, r."RECEIPT_ID" AS receipt_id,
                r."PREVIEW_HASH" AS preview_hash, h."SORAT_IS_DELETED" AS deleted
                FROM "FA_REMAINING_INVOICE" r JOIN "FA_SORAT_HESAB_HEADER" h ON h."ID_SORAT" = r."INVOICE_ID"
                WHERE r."REQUEST_ID" = :request_id''', {"request_id": str(payload.request_id)})
            if prior:
                if prior["receipt_id"] != receipt_id or prior["preview_hash"] != payload.preview_hash or prior["deleted"] == 'yes':
                    raise HTTPException(409, "درخواست قبلاً استفاده شده است؛ پنجره را دوباره باز کنید")
                return {"invoice_id": prior["id"]}
            result = preview(cur, current, tally, payload)
            if result["preview_hash"] != payload.preview_hash:
                raise HTTPException(409, "مقادیر یا تعرفه‌ها تغییر کرده‌اند؛ پیش‌نمایش را دوباره محاسبه کنید")
            cur.execute('''INSERT INTO "FA_SORAT_HESAB_HEADER"
                ("TALI_ID_HEADER", "ID_GHABZ_ANBAR", "BUYER_COMPANY_ID", "BUYER_COMPANY_ADDRESS",
                 "BUYER_COMPANY_PHONE", "BUYER_EGHTESADI_CODE", "BUYER_SHENASE_MELLI",
                 "SORAT_CREATE_AT", "SORAT_CREATE_BY", "SORAT_IS_DELETED", "IS_ACCEPTED", "CALC_NOTE",
                 "COMPANY_NAME", "SELLER_COMPANY_ADDRESS", "SELLER_SHENASE_MELLI")
                SELECT "TALI_ID_HEADER", "ID_GHABZ_ANBAR", "BUYER_COMPANY_ID", "BUYER_COMPANY_ADDRESS",
                 "BUYER_COMPANY_PHONE", "BUYER_EGHTESADI_CODE", "BUYER_SHENASE_MELLI",
                 CAST(SYSTIMESTAMP AT TIME ZONE 'Asia/Tehran' AS DATE), :actor, 'no', 'no', :note, "COMPANY_NAME", "SELLER_COMPANY_ADDRESS", "SELLER_SHENASE_MELLI"
                FROM "FA_SORAT_HESAB_HEADER" WHERE "ID_SORAT" = :original_id''',
                {"actor": user["id"], "note": result["calc_note"], "original_id": result["snapshot"]["original_invoice_id"]})
            # Read the identity of this inserted row, never MAX(id) across concurrent sessions.
            cur.execute('SELECT "ID_SORAT" FROM "FA_SORAT_HESAB_HEADER" WHERE ROWID = :rid', {"rid": cur.lastrowid})
            invoice_id = cur.fetchone()[0]
            cur.executemany('''INSERT INTO "FA_SORA_HESAB_DETAILS"
                ("ID_SORA_HEADER", "DESCRIPTION", "NUMBER_KALA", "WEIGHTE", "PRICE_DETAILS",
                 "ROW_KIND", "CALC_NOTE", "TAKHFIF_DETAILS", "TAKHFIF_ALL", "CREATE_AT", "CREATE_BY", "IS_DELETED")
                VALUES (:iid, :description, :quantity, :weight, :price, :kind, :note, 0, :price, SYSDATE, :actor, 'N')''',
                [{"iid": invoice_id, "actor": user["id"], **{key: row[key] for key in
                  ("description", "quantity", "weight", "price", "kind", "note")}} for row in result["rows"]])
            cur.execute('''INSERT INTO "FA_REMAINING_INVOICE"
                ("INVOICE_ID", "ORIGINAL_INVOICE_ID", "RECEIPT_ID", "REQUEST_ID", "SNAPSHOT_JSON", "PREVIEW_HASH")
                VALUES (:iid, :original_id, :rid, :request_id, :snapshot, :preview_hash)''',
                {"iid": invoice_id, "original_id": result["snapshot"]["original_invoice_id"], "rid": receipt_id,
                 "request_id": str(payload.request_id), "snapshot": json.dumps(result["snapshot"], ensure_ascii=False),
                 "preview_hash": result["preview_hash"]})
        conn.commit()
    return {"invoice_id": invoice_id}
