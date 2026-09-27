"""Receipt transitions and invoices, serialized by the existing tally header lock."""
from decimal import Decimal, ROUND_HALF_UP
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from app.auth.deps import require_permission
from app.core.db import get_connection
from app.services import receipt_db as db
from app.services.receipt_sources import allocate_sources, automatic_selections
from app.services.receipt_allocation import allocation_ratio, allocated_amount, decimal, EPS
from app.services.tally_handoff import return_to_operator_error
from app.services import receipt_invoice as ri
from app.services.storage_calc import billed_days
from app.services.insurance_cover import insurance_cover
from app.services import insurance_cover as cover_sql

router = APIRouter(prefix="/ghabz", tags=["receipt_workflow"])


class SourceSelection(BaseModel):
    tally_detail_id: int
    quantity: Decimal = Field(ge=0, allow_inf_nan=False)
    weight: Decimal = Field(ge=0, allow_inf_nan=False)
    baskol: Decimal = Field(ge=0, allow_inf_nan=False)


class SourceInput(BaseModel):
    lines: list[SourceSelection]


SOURCES_SQL = '''
SELECT d."ID_TALI_DETAILS" AS id, d."HSCODE" AS hscode,
       d."DESCRIPTION_KALA" AS description, d."CODE_GROUPE_KALA" AS goods_group,
       NVL(d."NUMBER_KALA", 0) AS quantity, NVL(d."WEIGHTE", 0) AS weight,
       NVL(d."WEIGHTE_BASKOL", 0) AS baskol,
       NVL(m."QUANTITY_SHARE", 0) AS quantity_share,
       NVL(m."WEIGHT_SHARE", 0) AS weight_share,
       NVL(m."BASKOL_SHARE", 0) AS baskol_share,
       NVL(u.quantity_share, 0) AS used_quantity,
       NVL(u.weight_share, 0) AS used_weight,
       NVL(u.baskol_share, 0) AS used_baskol
FROM "FA_TALI_DETAILES" d
LEFT JOIN "FA_GHABZ_TALLY_SOURCE" m
  ON m."TALLY_DETAIL_ID" = d."ID_TALI_DETAILS" AND m."RECEIPT_ID" = :rid
LEFT JOIN (
    SELECT s."TALLY_DETAIL_ID",
           SUM(s."QUANTITY_SHARE") AS quantity_share,
           SUM(s."WEIGHT_SHARE") AS weight_share,
           SUM(s."BASKOL_SHARE") AS baskol_share
    FROM "FA_GHABZ_TALLY_SOURCE" s
    JOIN "fa_ghabz_anbar_header" h ON h."ID_ghabz" = s."RECEIPT_ID"
    WHERE h."IS_DELETED" = 'no' AND NVL(h."IS_MASTER", 'no') = 'no'
      AND h."ID_ghabz" <> :rid
    GROUP BY s."TALLY_DETAIL_ID"
) u ON u."TALLY_DETAIL_ID" = d."ID_TALI_DETAILS"
WHERE d."ID_HEADERS_TALI" = :tid AND d."IS_DELETED" = 'no'
ORDER BY d."ID_TALI_DETAILS"
'''
EXPECTED_SQL = '''SELECT "HSCODE" AS hscode, "NUMBER_KALA" AS quantity,
    "WEIGHTE_asnad" AS weight, "WEIGHTE_BASKOL" AS baskol
    FROM "FA_ghabz_anbar_DETAILES"
    WHERE "ID_GHABZ_ANBAR_HEADAR" = :rid AND "IS_DELETED" = 'no' '''


def source_rows(cur, current):
    return db.rows(cur, SOURCES_SQL, {"rid": current["id"], "tid": current["tally_id"]})


def save_links(cur, current, selections):
    sources = source_rows(cur, current)
    if current["is_master"] == "yes":
        for row in sources:
            for key in ("quantity", "weight", "baskol"):
                row["used_" + key] = 0
    expected = db.rows(cur, EXPECTED_SQL, {"rid": current["id"]})
    try:
        links = allocate_sources(sources, selections, expected)
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc
    cur.execute('DELETE FROM "FA_GHABZ_TALLY_SOURCE" WHERE "RECEIPT_ID" = :rid',
                {"rid": current["id"]})
    cur.executemany('''INSERT INTO "FA_GHABZ_TALLY_SOURCE"
        ("RECEIPT_ID", "TALLY_DETAIL_ID", "QUANTITY_SHARE", "WEIGHT_SHARE", "BASKOL_SHARE")
        VALUES (:rid, :tally_detail_id, :quantity_share, :weight_share, :baskol_share)''',
        [{"rid": current["id"], **link} for link in links])


def verify_links(cur, current):
    sources = source_rows(cur, current)
    selections = []
    for row in sources:
        if any(row[key + "_share"] for key in ("quantity", "weight", "baskol")):
            selections.append({"tally_detail_id": row["id"], **{
                key: Decimal(str(row[key])) * Decimal(str(row[key + "_share"]))
                for key in ("quantity", "weight", "baskol")
            }})
    save_links(cur, current, selections)



RECEIPT_GOODS_SQL = """
SELECT d."CODE_GROUPE_KALA" AS code_groupe_kala,
       d."NUMBER_KALA" * m."QUANTITY_SHARE" AS number_kala,
       d."WEIGHTE" * m."WEIGHT_SHARE" AS weight,
       d."ZARIB_MAHAL" AS zarib_mahal, p."CODE" AS kala_price_code,
       p."price_30_day" AS price_30_day, p."price_60_day" AS price_60_day,
       p."price_90_day" AS price_90_day
FROM "FA_TALI_DETAILES" d
JOIN "FA_GHABZ_TALLY_SOURCE" m ON m."TALLY_DETAIL_ID" = d."ID_TALI_DETAILS"
    AND m."RECEIPT_ID" = :rid
LEFT JOIN "fa_kala_price" p ON p."id_kala_price" = d."CODE_GROUPE_KALA"
WHERE d."ID_HEADERS_TALI" = :tid AND d."IS_DELETED" = 'no'
ORDER BY d."ID_TALI_DETAILS"
"""

QUEUE_SQL = """
SELECT h."ID_ghabz" AS id, h."GHABZ_NUMBER" AS number_text, h."TALI_ID" AS tally_id
FROM "fa_ghabz_anbar_header" h
WHERE h."IS_DELETED" = 'no' AND h."WORKFLOW_STATUS" IN ('created', 'sent_to_keeper')
  AND EXISTS (SELECT 1 FROM "FA_ghabz_anbar_DETAILES" d
      WHERE d."ID_GHABZ_ANBAR_HEADAR" = h."ID_ghabz" AND d."IS_DELETED" = 'no')
  AND (NVL(h."IS_MASTER", 'no') = 'no' OR NOT EXISTS (
      SELECT 1 FROM "fa_ghabz_anbar_header" child
      WHERE child."TALI_ID" = h."TALI_ID" AND child."IS_DELETED" = 'no'
        AND NVL(child."IS_MASTER", 'no') = 'no'
        AND EXISTS (SELECT 1 FROM "FA_ghabz_anbar_DETAILES" cd
          WHERE cd."ID_GHABZ_ANBAR_HEADAR" = child."ID_ghabz" AND cd."IS_DELETED" = 'no')))
ORDER BY h."ID_ghabz"
"""


# --- 1405 invoice inputs ------------------------------------------------------
# Linked original tally rows with this receipt's share applied. Storage now uses
# fa_kala_price."storage_price"; the 30/60/90 columns are no longer read here.
RECEIPT_STORAGE_SQL = """
SELECT d."ID_TALI_DETAILS" AS id, d."HSCODE" AS hscode,
       d."DESCRIPTION_KALA" AS description, d."CODE_GROUPE_KALA" AS goods_group,
       p."CODE" AS kala_code, p."storage_price" AS storage_price,
       d."ZARIB_MAHAL" AS zarib_mahal, d."NUMBER_HAMEL" AS number_hamel,
       d."NUMBER_KALA" * m."QUANTITY_SHARE" AS quantity,
       d."WEIGHTE" * m."WEIGHT_SHARE" AS weight_kg
FROM "FA_TALI_DETAILES" d
JOIN "FA_GHABZ_TALLY_SOURCE" m ON m."TALLY_DETAIL_ID" = d."ID_TALI_DETAILS"
    AND m."RECEIPT_ID" = :rid
LEFT JOIN "fa_kala_price" p ON p."id_kala_price" = d."CODE_GROUPE_KALA"
WHERE d."ID_HEADERS_TALI" = :tid AND d."IS_DELETED" = 'no'
ORDER BY d."ID_TALI_DETAILS"
"""
CONTAINER_WEIGHTS_SQL = """
SELECT TRIM("NUMBER_HAMEL") AS number_hamel, SUM(NVL("WEIGHTE", 0)) AS weight_kg
FROM "FA_TALI_DETAILES"
WHERE "ID_HEADERS_TALI" = :tid AND "IS_DELETED" = 'no' AND "NUMBER_HAMEL" IS NOT NULL
GROUP BY TRIM("NUMBER_HAMEL")
"""
INVOICE_SETTINGS_SQL = """
SELECT "SETTING_KEY" AS setting_key, "VALUE_NUMBER" AS value_number
FROM "FA_APP_SETTINGS" WHERE "SETTING_KEY" IN ('tax_rate', 'system_service_rate')
"""
TEHRAN_TODAY_SQL = """SELECT CAST(SYSTIMESTAMP AT TIME ZONE 'Asia/Tehran' AS DATE) AS today FROM DUAL"""
# A tally's prepayment and discount are applied on exactly one of its invoices.
DEDUCTIONS_SQL = """
SELECT t."PREPAYMENT" AS prepayment, t."DISCOUNT" AS discount,
       (SELECT COUNT(*) FROM "FA_SORA_HESAB_DETAILS" d
          JOIN "FA_SORAT_HESAB_HEADER" i ON i."ID_SORAT" = d."ID_SORA_HEADER"
         WHERE i."TALI_ID_HEADER" = t."ID_TALI"
           AND NVL(i."SORAT_IS_DELETED", 'no') = 'no'
           AND NVL(d."IS_DELETED", 'N') NOT IN ('Y', 'yes')
           AND d."ROW_KIND" IN ('prepayment', 'discount')) AS applied_rows
FROM "FA_TALI_HEADER" t WHERE t."ID_TALI" = :tid
"""


# Insurance: every active tally's policies and totals, so the shared ceilings can
# be consumed in registration order (insurance_cover.py). Same SQL as the banner.
INSURANCE_HEADERS_SQL = cover_sql.HEADERS_SQL
INSURANCE_TOTALS_SQL = cover_sql.TOTALS_SQL
# Customs value linked to this receipt and to the tally's already-invoiced
# receipts. A row's value follows its declared-weight share. A row without
# weight follows the receipt's pallet share (receipt pallets / tally pallets; a
# general receipt takes all); only when no pallet count exists either does the
# linked quantity share apply.
RECEIPT_CUSTOMS_SQL = """
SELECT m."RECEIPT_ID" AS receipt_id,
       SUM(NVL(d."CUSTOMS_VALUE", 0) *
           CASE WHEN NVL(d."WEIGHTE", 0) > 0 THEN m."WEIGHT_SHARE"
                WHEN NVL(h."IS_MASTER", 'no') = 'yes' THEN 1
                WHEN NVL(t."VOLUMETRIC_PALLETS", 0) > 0 AND NVL(h."PALLET_QUANTITY", 0) > 0
                     THEN h."PALLET_QUANTITY" / t."VOLUMETRIC_PALLETS"
                ELSE m."QUANTITY_SHARE" END)
           AS customs_value
FROM "FA_GHABZ_TALLY_SOURCE" m
JOIN "FA_TALI_DETAILES" d ON d."ID_TALI_DETAILS" = m."TALLY_DETAIL_ID"
JOIN "fa_ghabz_anbar_header" h ON h."ID_ghabz" = m."RECEIPT_ID"
JOIN "FA_TALI_HEADER" t ON t."ID_TALI" = h."TALI_ID"
WHERE h."TALI_ID" = :tid AND h."IS_DELETED" = 'no' AND d."IS_DELETED" = 'no'
  AND (m."RECEIPT_ID" = :rid OR EXISTS (
        SELECT 1 FROM "FA_SORAT_HESAB_HEADER" i
        WHERE i."ID_GHABZ_ANBAR" = m."RECEIPT_ID" AND NVL(i."SORAT_IS_DELETED", 'no') = 'no'))
GROUP BY m."RECEIPT_ID"
"""


# Linked rows whose customs value is not recorded: insurance counts them as zero,
# so issuing requires the user to acknowledge them explicitly.
MISSING_CUSTOMS_SQL = """
SELECT d."ID_TALI_DETAILS" AS id, d."HSCODE" AS hscode, d."DESCRIPTION_KALA" AS description
FROM "FA_GHABZ_TALLY_SOURCE" m
JOIN "FA_TALI_DETAILES" d ON d."ID_TALI_DETAILS" = m."TALLY_DETAIL_ID"
WHERE m."RECEIPT_ID" = :rid AND d."IS_DELETED" = 'no' AND NVL(d."CUSTOMS_VALUE", 0) <= 0
ORDER BY d."ID_TALI_DETAILS"
"""


def missing_customs(cur, receipt_id):
    return [str(row["hscode"] or row["description"] or f"ردیف {row['id']}").strip()
            for row in db.rows(cur, MISSING_CUSTOMS_SQL, {"rid": receipt_id})]


def missing_customs_message(names):
    return (f"ارزش گمرکی ردیف‌های {'، '.join(names)} در تالی ثبت نشده است؛ "
            "هزینه بیمه این ردیف‌ها صفر محاسبه می‌شود. برای صدور صورتحساب این مورد را تأیید کنید.")


class InvoiceIssueInput(BaseModel):
    # Answer to «آیا مبلغ پیش‌پرداخت و تخفیف روی همین قبض اعمال شود؟»
    apply_deductions: bool | None = None
    # The user saw the missing-customs-value error and still issues the invoice.
    confirm_missing_customs: bool | None = None


def deductions_state(cur, current):
    row = db.one(cur, DEDUCTIONS_SQL, {"tid": current["tally_id"]}) or {}
    applied = int(row.get("applied_rows") or 0) > 0
    plan = ri.deduction_plan(is_general=current["is_master"] == "yes",
                             prepayment=row.get("prepayment"), discount=row.get("discount"),
                             already_applied=applied, answer=None)
    return {"prepayment": row.get("prepayment"), "discount": row.get("discount"),
            "applied": applied, "ask": plan == "ask"}


def get_pool(cur, tid):
    return db.rows(cur, """SELECT "LINE_NO" AS line_no, "DESCRIPTION" AS description,
        "TOTAL_PRICE" AS price FROM "FA_RECEIPT_SERVICE_POOL"
        WHERE "TALLY_ID" = :tid ORDER BY "LINE_NO" """, {"tid": tid})


def calculate(cur, current, include_services=False):
    from app.routers.invoice import compute_from_tally
    goods = db.rows(cur, RECEIPT_GOODS_SQL, {"tid": current["tally_id"], "rid": current["id"]})
    if not goods:
        db.conflict("ردیف‌های اصلی تالی متعلق به این قبض را انتخاب کنید")
    return compute_from_tally(current["tally_id"],
        read_all=lambda sql, params=None: db.rows(cur, sql, params),
        read_one=lambda sql, params=None: db.one(cur, sql, params),
        goods=goods, include_services=include_services, prior_invoice_count=0,
        strict_services=True)


@router.get("/keeper-queue", dependencies=[Depends(require_permission("tally.services"))])
def keeper_queue():
    with get_connection() as conn:
        with conn.cursor() as cur:
            return db.rows(cur, QUEUE_SQL)


@router.get("/{receipt_id}/workflow", dependencies=[Depends(require_permission("ghabz.view"))])
def get_workflow(receipt_id: int):
    with get_connection() as conn:
        with conn.cursor() as cur:
            current, siblings, _ = db.receipt(cur, receipt_id)
            invoice = db.one(cur, """SELECT MAX("ID_SORAT") AS id FROM "FA_SORAT_HESAB_HEADER"
                WHERE "ID_GHABZ_ANBAR" = :id AND NVL("SORAT_IS_DELETED", 'no') = 'no' """,
                {"id": receipt_id})
            return {**db.workflow(current, siblings), "invoice_id": invoice["id"],
                    "services_locked": any(r["status"] in ("finalized", "invoice_issued")
                                           for r in db.operational(siblings)),
                    "deductions": deductions_state(cur, current),
                    "missing_customs": missing_customs(cur, receipt_id)}


@router.get("/{receipt_id}/sources", dependencies=[Depends(require_permission("ghabz.view"))])
def get_sources(receipt_id: int):
    with get_connection() as conn:
        with conn.cursor() as cur:
            current, _, _ = db.receipt(cur, receipt_id)
            return source_rows(cur, current)


@router.put("/{receipt_id}/sources", dependencies=[Depends(require_permission("tally.services"))])
def set_sources(receipt_id: int, payload: SourceInput):
    with get_connection() as conn:
        with conn.cursor() as cur:
            current, siblings, _ = db.receipt(cur, receipt_id, lock=True)
            if not db.workflow(current, siblings)["can_finalize"]:
                db.conflict("پیوند کالاهای قبض نهایی یا خلاصه قابل تغییر نیست")
            save_links(cur, current, [line.model_dump() for line in payload.lines])
        conn.commit()
    return {"saved": True}


@router.post("/{receipt_id}/final-checklist")
def finalize(receipt_id: int, user: dict = Depends(require_permission("tally.services"))):
    with get_connection() as conn:
        with conn.cursor() as cur:
            current, siblings, tally = db.receipt(cur, receipt_id, lock=True)
            if not db.workflow(current, siblings)["can_finalize"]:
                db.conflict("ثبت نهایی این قبض مجاز نیست")
            if any(r["status"] == "invoice_issued" and r["allocation_ratio"] is None for r in siblings):
                db.conflict("تالی صورتحساب قدیمی دارد؛ پیش از تخصیص جدید، سوابق مالی باید بررسی شود")
            cargo = {"yes": "volumetric", "no": "weight"}.get(tally["is_volumetric"], tally["is_volumetric"])
            error = return_to_operator_error("keeper", cargo, tally["volumetric_pallets"])
            if error:
                db.conflict(error)
            missing = db.one(cur, """SELECT COUNT(*) AS cnt FROM (
                SELECT DISTINCT d."NUMBER_HAMEL" FROM "FA_TALI_DETAILES" d
                WHERE d."ID_HEADERS_TALI" = :tid AND d."IS_DELETED" = 'no'
                  AND d."NUMBER_HAMEL" IS NOT NULL AND NOT EXISTS (
                    SELECT 1 FROM "FA_TALI_CARRIER_TRANSPORTATION" t
                    WHERE t."TALI_ID" = d."ID_HEADERS_TALI" AND t."NUMBER_HAMEL" = d."NUMBER_HAMEL"
                      AND t."HAS_TRANSPORTATION" IN ('yes', 'no'))
                )""", {"tid": current["tally_id"]})
            if missing["cnt"]:
                db.conflict("اطلاعات باربری تمام حامل‌های تالی را تکمیل کنید")
            if current["is_master"] == "yes":
                save_links(cur, current, [{"tally_detail_id": row["id"],
                    **{key: row[key] for key in ("quantity", "weight", "baskol")}}
                    for row in source_rows(cur, current)
                    if any(decimal(row[key]) > 0 for key in ("quantity", "weight", "baskol"))])
            else:
                # Reserve older receipts first so allocation does not depend on
                # which receipt the keeper confirms first. Existing links win.
                for item in sorted(db.operational(siblings), key=lambda r: r["id"]):
                    if item["is_master"] == "yes" or item["id"] > current["id"]:
                        continue
                    rows = source_rows(cur, item)
                    if any(row[key + "_share"] for row in rows
                           for key in ("quantity", "weight", "baskol")):
                        continue
                    expected = db.rows(cur, EXPECTED_SQL, {"rid": item["id"]})
                    try:
                        selections = automatic_selections(rows, expected)
                    except ValueError as exc:
                        raise HTTPException(422, str(exc)) from exc
                    save_links(cur, item, selections)
                verify_links(cur, current)
            weights = db.one(cur, """SELECT
                SUM(NVL(d."WEIGHTE", 0)) AS total_weight,
                SUM(NVL(d."WEIGHTE", 0) * NVL(m."WEIGHT_SHARE", 0)) AS selected_weight
                FROM "FA_TALI_DETAILES" d
                LEFT JOIN "FA_GHABZ_TALLY_SOURCE" m
                  ON m."TALLY_DETAIL_ID" = d."ID_TALI_DETAILS" AND m."RECEIPT_ID" = :rid
                WHERE d."ID_HEADERS_TALI" = :tid AND d."IS_DELETED" = 'no' """,
                {"tid": current["tally_id"], "rid": receipt_id})
            try:
                ratio = allocation_ratio(current["is_master"] == "yes", cargo,
                    weights["selected_weight"], weights["total_weight"],
                    current["pallet_quantity"], tally["volumetric_pallets"])
            except ValueError as exc:
                raise HTTPException(422, str(exc)) from exc
            reserved = sum((decimal(r["allocation_ratio"]) for r in siblings
                            if r["status"] in ("finalized", "invoice_issued")), Decimal(0))
            if reserved + ratio > 1 + EPS:
                db.conflict("جمع وزن یا پالت تخصیص‌یافته به قبض‌های نهایی از کل تالی بیشتر است")
            # Snapshot all shared charges once, under the same tally lock. Later
            # tariff changes cannot change the pool between sibling invoices.
            if not get_pool(cur, current["tally_id"]):
                computed = calculate(cur, current, include_services=True)
                charges = [row for row in computed["service_rows"] if row["price"] is not None]
                cur.executemany("""INSERT INTO "FA_RECEIPT_SERVICE_POOL"
                    ("TALLY_ID", "LINE_NO", "DESCRIPTION", "TOTAL_PRICE")
                    VALUES (:tid, :line_no, :description, :price)""",
                    [{"tid": current["tally_id"], "line_no": 0, "description": "snapshot", "price": 0}]
                    + [{"tid": current["tally_id"], "line_no": i + 1, "description": row["description"],
                        "price": Decimal(row["price"])} for i, row in enumerate(charges)])
            cur.execute("""UPDATE "fa_ghabz_anbar_header"
                SET "WORKFLOW_STATUS" = 'finalized', "ALLOCATION_RATIO" = :ratio,
                    "FINALIZED_AT" = SYSDATE, "FINALIZED_BY" = :actor
                WHERE "ID_ghabz" = :rid""", {"ratio": ratio, "actor": user["id"], "rid": receipt_id})
            cur.execute("""UPDATE "FA_TALI_HEADER" SET "HANDOFF_STEP" = 'returned',
                "RETURNED_AT" = SYSDATE, "RETURNED_BY" = :actor WHERE "ID_TALI" = :tid""",
                {"actor": user["id"], "tid": current["tally_id"]})
        conn.commit()
    return get_workflow(receipt_id)


@router.post("/{receipt_id}/invoice", status_code=201)
def issue_invoice(receipt_id: int, user: dict = Depends(require_permission("invoice.issue")),
                  payload: InvoiceIssueInput | None = None):
    """Issue the receipt's invoice once, under the 1405 rules (receipt_invoice.py).

    Everything is read and written under the tally lock, so the prepayment and
    discount can only ever land on one invoice of the tally.
    """
    answer = payload.apply_deductions if payload else None
    with get_connection() as conn:
        with conn.cursor() as cur:
            current, siblings, tally = db.receipt(cur, receipt_id, lock=True)
            prior = db.one(cur, """SELECT "ID_SORAT" AS id FROM "FA_SORAT_HESAB_HEADER"
                WHERE "ID_GHABZ_ANBAR" = :id AND NVL("SORAT_IS_DELETED", 'no') = 'no' """,
                {"id": receipt_id})
            if prior and current["status"] == "invoice_issued":
                return {"invoice_id": prior["id"]}
            if prior or not db.workflow(current, siblings)["can_invoice"]:
                db.conflict("صدور صورتحساب فقط پس از ثبت نهایی قبض اصلی یا تفکیکی مجاز است")
            ratio = decimal(current["allocation_ratio"])
            pool = get_pool(cur, current["tally_id"])
            if not pool or ratio <= 0:
                db.conflict("تخصیص هزینه‌های این قبض تکمیل نشده است")

            # --- storage: cargo type, day count, linked rows -------------------------
            try:
                cargo = ri.cargo_type(tally["is_volumetric"])
            except ValueError as exc:
                db.conflict(str(exc))
            if tally["date_unloading"] is None:
                db.conflict("تاریخ تخلیه تالی ثبت نشده است")
            today = db.one(cur, TEHRAN_TODAY_SQL)["today"]
            try:
                days = billed_days(tally["date_unloading"], today)
            except ValueError as exc:
                db.conflict(str(exc))
            lines = db.rows(cur, RECEIPT_STORAGE_SQL,
                            {"tid": current["tally_id"], "rid": receipt_id})
            container_weights = None
            if cargo == "container":
                container_weights = {row["number_hamel"]: row["weight_kg"] for row in
                                     db.rows(cur, CONTAINER_WEIGHTS_SQL, {"tid": current["tally_id"]})}
            # Detailed receipt: its own pallet count. General receipt: the tally's.
            pallets = (tally["volumetric_pallets"] if current["is_master"] == "yes"
                       else current["pallet_quantity"])
            try:
                storage = ri.storage_rows(cargo, lines, days.billed, pallets=pallets,
                                          container_weights=container_weights)
            except ValueError as exc:
                raise HTTPException(422, str(exc)) from exc

            # --- shared services: this receipt's share of the frozen pool -------------
            previous_ratio = db.one(cur, """SELECT SUM(h."ALLOCATION_RATIO") AS ratio
                FROM "fa_ghabz_anbar_header" h
                WHERE h."TALI_ID" = :tid AND h."IS_DELETED" = 'no'
                  AND EXISTS (SELECT 1 FROM "FA_SORAT_HESAB_HEADER" i
                    WHERE i."ID_GHABZ_ANBAR" = h."ID_ghabz" AND NVL(i."SORAT_IS_DELETED", 'no') = 'no')
                """, {"tid": current["tally_id"]})["ratio"]
            previous = db.rows(cur, """SELECT d."SERVICE_POOL_LINE" AS line_no,
                SUM(d."PRICE_DETAILS") AS price FROM "FA_SORA_HESAB_DETAILS" d
                JOIN "FA_SORAT_HESAB_HEADER" i ON i."ID_SORAT" = d."ID_SORA_HEADER"
                WHERE i."TALI_ID_HEADER" = :tid AND NVL(i."SORAT_IS_DELETED", 'no') = 'no'
                  AND NVL(d."IS_DELETED", 'N') NOT IN ('Y', 'yes')
                  AND d."SERVICE_POOL_LINE" IS NOT NULL
                GROUP BY d."SERVICE_POOL_LINE" """, {"tid": current["tally_id"]})
            previous = {int(row["line_no"]): row["price"] for row in previous}
            allocated = []
            for charge in pool:
                if charge["line_no"] == 0:
                    continue
                try:
                    amount = allocated_amount(charge["price"], ratio, previous_ratio,
                                              previous.get(int(charge["line_no"]), 0))
                except ValueError as exc:
                    raise HTTPException(409, str(exc)) from exc
                allocated.append({"line_no": charge["line_no"], "description": charge["description"],
                                  "total": charge["price"], "amount": amount})
            services = ri.service_rows(allocated, ratio)

            # --- insurance: shared ceilings consumed in tally registration order ---------
            missing = missing_customs(cur, receipt_id)
            if missing and not (payload and payload.confirm_missing_customs):
                raise HTTPException(422, missing_customs_message(missing))
            cover = insurance_cover(
                current["tally_id"], db.rows(cur, INSURANCE_HEADERS_SQL),
                {int(row["id_tali"]): row for row in db.rows(cur, INSURANCE_TOTALS_SQL)})
            values = {int(row["receipt_id"]): row["customs_value"] for row in
                      db.rows(cur, RECEIPT_CUSTOMS_SQL, {"tid": current["tally_id"], "rid": receipt_id})}
            insurance = ri.insurance_row(
                values.pop(receipt_id, 0), cover,
                sum((decimal(value) for value in values.values()), Decimal(0)), days.billed,
                missing=missing)

            # --- settings, deductions, totals ------------------------------------------
            settings = {row["setting_key"]: row["value_number"]
                        for row in db.rows(cur, INVOICE_SETTINGS_SQL)}
            deductions = db.one(cur, DEDUCTIONS_SQL, {"tid": current["tally_id"]}) or {}
            plan = ri.deduction_plan(
                is_general=current["is_master"] == "yes",
                prepayment=deductions.get("prepayment"), discount=deductions.get("discount"),
                already_applied=int(deductions.get("applied_rows") or 0) > 0, answer=answer)
            if plan == "ask":
                raise HTTPException(422, "مشخص کنید پیش‌پرداخت و تخفیف روی همین قبض اعمال شود یا خیر")
            try:
                invoice_rows, _ = ri.build_invoice(
                    system_rate=settings.get("system_service_rate"), storage=storage,
                    services=services, tax_rate=settings.get("tax_rate") or 0,
                    prepayment=deductions.get("prepayment"), discount=deductions.get("discount"),
                    apply_deductions=plan == "apply",
                    receipt_label=str(current.get("number_text") or receipt_id),
                    insurance=insurance)
            except ValueError as exc:
                raise HTTPException(422, str(exc)) from exc

            buyer = db.one(cur, """SELECT "ADDRESS" AS address, "PHONE" AS phone,
                "ECONOMIC_CODE" AS economic_code, NVL("NATIONAL_ID", "NATIONAL_CODE") AS national_id
                FROM "FA_PRODUCT_OWNER" WHERE "ID_OWNER" = :id""",
                {"id": tally["id_product_ownear"]}) or {}
            output = cur.var(int)
            cur.execute("""INSERT INTO "FA_SORAT_HESAB_HEADER"
                ("TALI_ID_HEADER", "ID_GHABZ_ANBAR", "BUYER_COMPANY_ID",
                 "BUYER_COMPANY_ADDRESS", "BUYER_COMPANY_PHONE", "BUYER_EGHTESADI_CODE", "BUYER_SHENASE_MELLI",
                 "SORAT_CREATE_AT", "SORAT_CREATE_BY", "SORAT_IS_DELETED", "IS_ACCEPTED", "CALC_NOTE")
                VALUES (:tid, :rid, :buyer, :address, :phone, :economic, :national, SYSDATE, :actor,
                        'no', 'no', :calc_note)
                RETURNING "ID_SORAT" INTO :new_id""",
                {"tid": current["tally_id"], "rid": receipt_id, "buyer": tally["id_product_ownear"],
                 "address": buyer.get("address"), "phone": buyer.get("phone"),
                 "economic": buyer.get("economic_code"), "national": buyer.get("national_id"),
                 "actor": user["id"], "calc_note": ri.header_note(cargo, days), "new_id": output})
            invoice_id = output.getvalue()[0]
            cur.executemany("""INSERT INTO "FA_SORA_HESAB_DETAILS"
                ("ID_SORA_HEADER", "DESCRIPTION", "NUMBER_KALA", "WEIGHTE", "PRICE_DETAILS",
                 "SERVICE_POOL_LINE", "ROW_KIND", "CALC_NOTE",
                 "TAKHFIF_DETAILS", "TAKHFIF_ALL", "CREATE_AT", "CREATE_BY", "IS_DELETED")
                VALUES (:invoice_id, :description, :quantity, :weight, :price,
                        :service_line, :kind, :note, 0, :price, SYSDATE, :actor, 'N')""",
                [{"invoice_id": invoice_id, "description": row.description,
                  "quantity": row.quantity, "weight": row.weight, "price": row.price,
                  "service_line": row.service_line, "kind": row.kind, "note": row.note,
                  "actor": user["id"]} for row in invoice_rows])
            cur.execute("""UPDATE "fa_ghabz_anbar_header"
                SET "WORKFLOW_STATUS" = 'invoice_issued', "INVOICE_ISSUED_AT" = SYSDATE,
                    "INVOICE_ISSUED_BY" = :actor WHERE "ID_ghabz" = :id""",
                {"id": receipt_id, "actor": user["id"]})
        conn.commit()
    return {"invoice_id": invoice_id}
