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
                                           for r in db.operational(siblings))}


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
def issue_invoice(receipt_id: int, user: dict = Depends(require_permission("invoice.issue"))):
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
            computed = calculate(cur, current)
            if any(row["price"] is None for row in computed["storage_rows"]):
                db.conflict("تعرفه یا ضریب انبارداری کالاهای اصلی تالی ناقص است")
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
            invoice_rows = [{**row, "service_line": None} for row in computed["storage_rows"]]
            for charge in pool:
                if charge["line_no"] == 0:
                    continue
                try:
                    amount = allocated_amount(charge["price"], ratio, previous_ratio,
                                              previous.get(int(charge["line_no"]), 0))
                except ValueError as exc:
                    raise HTTPException(409, str(exc)) from exc
                invoice_rows.append({"description": charge["description"], "number_kala": None,
                    "weight": None, "price": str(amount), "service_line": charge["line_no"]})
            subtotal = sum((Decimal(row["price"]) for row in invoice_rows), Decimal(0))
            tax = (subtotal * Decimal(computed["tax_rate"]) / 100).quantize(Decimal(1), rounding=ROUND_HALF_UP)
            if tax:
                invoice_rows.append({"description": "مالیات بر ارزش افزوده", "number_kala": None,
                                     "weight": None, "price": str(tax), "service_line": None})
            buyer = db.one(cur, """SELECT "ADDRESS" AS address, "PHONE" AS phone,
                "ECONOMIC_CODE" AS economic_code, NVL("NATIONAL_ID", "NATIONAL_CODE") AS national_id
                FROM "FA_PRODUCT_OWNER" WHERE "ID_OWNER" = :id""",
                {"id": tally["id_product_ownear"]}) or {}
            output = cur.var(int)
            cur.execute("""INSERT INTO "FA_SORAT_HESAB_HEADER"
                ("TALI_ID_HEADER", "ID_GHABZ_ANBAR", "BUYER_COMPANY_ID",
                 "BUYER_COMPANY_ADDRESS", "BUYER_COMPANY_PHONE", "BUYER_EGHTESADI_CODE", "BUYER_SHENASE_MELLI",
                 "SORAT_CREATE_AT", "SORAT_CREATE_BY", "SORAT_IS_DELETED", "IS_ACCEPTED")
                VALUES (:tid, :rid, :buyer, :address, :phone, :economic, :national, SYSDATE, :actor, 'no', 'no')
                RETURNING "ID_SORAT" INTO :new_id""",
                {"tid": current["tally_id"], "rid": receipt_id, "buyer": tally["id_product_ownear"],
                 "address": buyer.get("address"), "phone": buyer.get("phone"),
                 "economic": buyer.get("economic_code"), "national": buyer.get("national_id"),
                 "actor": user["id"], "new_id": output})
            invoice_id = output.getvalue()[0]
            cur.executemany("""INSERT INTO "FA_SORA_HESAB_DETAILS"
                ("ID_SORA_HEADER", "DESCRIPTION", "NUMBER_KALA", "WEIGHTE", "PRICE_DETAILS",
                 "SERVICE_POOL_LINE", "TAKHFIF_DETAILS", "TAKHFIF_ALL", "CREATE_AT", "CREATE_BY", "IS_DELETED")
                VALUES (:invoice_id, :description, :quantity, :weight, :price,
                        :service_line, 0, :price, SYSDATE, :actor, 'N')""",
                [{"invoice_id": invoice_id, "description": row["description"],
                  "quantity": row["number_kala"],
                  "weight": None if row["weight"] is None else Decimal(row["weight"]),
                  "price": Decimal(row["price"]), "service_line": row["service_line"],
                  "actor": user["id"]} for row in invoice_rows])
            cur.execute("""UPDATE "fa_ghabz_anbar_header"
                SET "WORKFLOW_STATUS" = 'invoice_issued', "INVOICE_ISSUED_AT" = SYSDATE,
                    "INVOICE_ISSUED_BY" = :actor WHERE "ID_ghabz" = :id""",
                {"id": receipt_id, "actor": user["id"]})
        conn.commit()
    return {"invoice_id": invoice_id}
