"""Non-customs stock is already excluded from the customs stock report."""
from datetime import date, datetime, timezone, timedelta
from collections import Counter
from fastapi import APIRouter, Depends, HTTPException
from app.auth.deps import require_permission
from app.core.db import get_connection
from app.services import receipt_db as db
from app.services.non_customs import Registration, BatchRegistration, Exit, validate_amounts
from app.services.report_json import serializable
from app.services import stock_report
from app.services.non_customs_stock import build_rows

router = APIRouter(prefix="/non-customs", tags=["non-customs"],
                   dependencies=[Depends(require_permission("non_customs.view"))])
# Only explicit receipt/source allocations are accepted. Legacy ambiguous rows
# cannot safely establish stock that is disjoint from the customs report.
CANDIDATES_SQL = """SELECT r."ID_ghabz" AS receipt_id, r."TALI_ID" AS tally_id,
 t."TALI_NUMBER" AS tally_number, r."GHABZ_NUMBER" AS receipt_number,
 s."TALLY_DETAIL_ID" AS source_id, d."DESCRIPTION_KALA" AS description,
 (SELECT COUNT(*) FROM "FA_TALI_DETAILES" numbered
  WHERE numbered."ID_HEADERS_TALI" = d."ID_HEADERS_TALI"
    AND numbered."IS_DELETED" = 'no'
    AND numbered."ID_TALI_DETAILS" <= d."ID_TALI_DETAILS") AS row_number,
 d."ZARIB_MAHAL" AS zarib_mahal,
 d."HSCODE" AS hscode, d."NUMBER_HAMEL" AS number_hamel,
 t."IS_VOLUMETRIC" AS cargo, i."ID_SORAT" AS invoice_id,
 TRUNC(i."SORAT_CREATE_AT") AS invoice_date,
 COALESCE(o."COMPANY_NAME", TRIM(o."NAME" || ' ' || o."FAMILY")) AS owner_name,
 NVL(d."WEIGHTE",0) * NVL(s."WEIGHT_SHARE",0) AS weight,
 NVL(d."NUMBER_KALA",0) * NVL(s."QUANTITY_SHARE",0) AS quantity,
 CASE WHEN r."IS_MASTER" = 'yes'
      THEN COALESCE(d."ROW_PALLETS", d."NUMBER_PALLET", 0)
      ELSE NVL(p."PALLETS", 0) END AS pallets
 FROM "fa_ghabz_anbar_header" r
 JOIN "FA_TALI_HEADER" t ON t."ID_TALI" = r."TALI_ID" AND t."IS_DELETED" = 'no'
 JOIN "FA_GHABZ_TALLY_SOURCE" s ON s."RECEIPT_ID" = r."ID_ghabz"
 JOIN "FA_TALI_DETAILES" d ON d."ID_TALI_DETAILS" = s."TALLY_DETAIL_ID"
   AND d."ID_HEADERS_TALI" = t."ID_TALI" AND d."IS_DELETED" = 'no'
 JOIN "FA_SORAT_HESAB_HEADER" i ON i."ID_GHABZ_ANBAR" = r."ID_ghabz"
   AND NVL(i."SORAT_IS_DELETED", 'no') = 'no'
 LEFT JOIN "FA_RECEIPT_PALLETS" p ON p."RECEIPT_ID" = r."ID_ghabz"
   AND p."TALLY_DETAIL_ID" = d."ID_TALI_DETAILS"
 LEFT JOIN "FA_PRODUCT_OWNER" o ON o."ID_OWNER" = t."ID_PRODUCT_OWNEAR"
 WHERE r."IS_DELETED" = 'no'
 AND (NVL(r."IS_MASTER", 'no') = 'no' OR NOT EXISTS (
 SELECT 1 FROM "fa_ghabz_anbar_header" child WHERE child."TALI_ID" = r."TALI_ID"
 AND child."IS_DELETED" = 'no' AND NVL(child."IS_MASTER", 'no') = 'no'
 AND EXISTS (SELECT 1 FROM "FA_ghabz_anbar_DETAILES" cd
 WHERE cd."ID_GHABZ_ANBAR_HEADAR" = child."ID_ghabz" AND cd."IS_DELETED" = 'no')))
 AND NOT EXISTS (SELECT 1 FROM "FA_REMAINING_INVOICE" x WHERE x."INVOICE_ID" = i."ID_SORAT")
 ORDER BY t."ID_TALI", r."ID_ghabz", d."ID_TALI_DETAILS"
"""
STOCK_SQL = """SELECT n."RECEIPT_ID" AS receipt_id, n."SOURCE_ID" AS source_id,
 n."ORIGINAL_INVOICE_ID" AS invoice_id, n."START_DATE" AS start_date,
 t."DATE_UNLOADING" AS unloaded_at, t."ID_PRODUCT_OWNEAR" AS owner_id,
 t."IS_BIMEH" AS is_insured, t."COMPANY_BIMEH" AS insurance_company,
 t."NUMBER_BIMEH" AS policy_numbers,
 (SELECT MAX(v."INSURED_VALUE") FROM "FA_TALI_DETAILES" v
  WHERE v."ID_HEADERS_TALI" = t."ID_TALI" AND v."IS_DELETED" = 'no') AS insured_ceiling,
 d."WEIGHTE" AS original_weight, d."NUMBER_KALA" AS original_quantity,
 COALESCE(d."ROW_PALLETS", d."NUMBER_PALLET") AS original_pallets,
 d."WEIGHTE_BASKOL" AS original_baskol, d."CUSTOMS_VALUE" AS original_customs_value,
 d."ID_ANBAR" AS anbar_id, a."NAME_ANBAR" AS anbar_name, tg."NAME_TAGH" AS tagh_name,
 COALESCE(TO_CHAR(pt."SYS_TERM_VALUE"), d."TYPE_BASTEM") AS package_type,
 d."ZARIB_MAHAL" AS zarib_mahal, d."NUMBER_HAMEL" AS carrier,
 d."CONTAINER_TYPE" AS container_type, d."CONTAINER_NUMBER" AS container_number,
 d."INSURANCE_EXPIRY_DATE" AS insurance_expiry,
 r."TALI_ID" AS tally_id, t."TALI_NUMBER" AS tally_number,
 r."GHABZ_NUMBER" AS receipt_number, t."IS_VOLUMETRIC" AS cargo,
 d."DESCRIPTION_KALA" AS description, d."HSCODE" AS hscode,
 COALESCE(o."COMPANY_NAME", TRIM(o."NAME" || ' ' || o."FAMILY")) AS owner_name,
 CASE WHEN NVL(i."SORAT_IS_DELETED",'no') = 'no' THEN 1 ELSE 0 END AS invoice_active,
 n."WEIGHT" - NVL(e.weight,0) AS weight,
 n."QUANTITY" - NVL(e.quantity,0) AS quantity,
 n."PALLETS" - NVL(e.pallets,0) AS pallets
 FROM "FA_NON_CUSTOMS" n
 JOIN "fa_ghabz_anbar_header" r ON r."ID_ghabz" = n."RECEIPT_ID"
 JOIN "FA_TALI_HEADER" t ON t."ID_TALI" = r."TALI_ID"
 JOIN "FA_TALI_DETAILES" d ON d."ID_TALI_DETAILS" = n."SOURCE_ID"
 JOIN "FA_SORAT_HESAB_HEADER" i ON i."ID_SORAT" = n."ORIGINAL_INVOICE_ID"
 LEFT JOIN "FA_ANBAR" a ON a."ID_ANBAR" = d."ID_ANBAR"
 LEFT JOIN "FA_TAGH_ANBAR" tg ON tg."ID_TAGH" = d."ID_TAGH_ANBAR"
 LEFT JOIN "FA_SYS_TERMS" pt ON TO_CHAR(pt."SYS_TERM_ID") = d."TYPE_BASTEM"
 LEFT JOIN "FA_PRODUCT_OWNER" o ON o."ID_OWNER" = t."ID_PRODUCT_OWNEAR"
 LEFT JOIN (SELECT "RECEIPT_ID", "SOURCE_ID", SUM("WEIGHT") AS weight,
 SUM("QUANTITY") AS quantity, SUM("PALLETS") AS pallets
 FROM "FA_NON_CUSTOMS_EXIT" GROUP BY "RECEIPT_ID", "SOURCE_ID") e
 ON e."RECEIPT_ID" = n."RECEIPT_ID" AND e."SOURCE_ID" = n."SOURCE_ID"
 ORDER BY n."START_DATE", n."RECEIPT_ID", n."SOURCE_ID"
"""

def stock(cur, receipt_id=None):
    return [r for r in db.rows(cur, STOCK_SQL)
            if (receipt_id is None or r["receipt_id"] == receipt_id)
            and any(r[k] > 0 for k in ("weight", "quantity", "pallets"))]

@router.get("", dependencies=[Depends(require_permission("non_customs.operations"))])
def inventory():
    with get_connection() as conn:
        with conn.cursor() as cur:
            items = stock(cur)
    return serializable({"items": items, "totals": {k: sum(r[k] for r in items)
        for k in ("weight", "quantity", "pallets")}})

@router.get("/stock", dependencies=[Depends(require_permission("non_customs.stock"))])
def stock_inventory(group_by: str = "hscode", hscode: str | None = None,
                    owner_id: int | None = None, anbar_id: int | None = None,
                    location: str | None = None, unloaded_from: date | None = None,
                    unloaded_to: date | None = None):
    if group_by not in stock_report.GROUP_BY:
        raise HTTPException(422, "نوع گروه‌بندی نامعتبر است")
    if location and location not in stock_report.LOCATION_LABELS:
        raise HTTPException(422, "نوع محل نامعتبر است")
    if unloaded_from and unloaded_to and unloaded_from > unloaded_to:
        raise HTTPException(422, "تاریخ پایان نمی‌تواند قبل از تاریخ شروع باشد")
    with get_connection() as conn:
        with conn.cursor() as cur:
            all_rows = build_rows(stock(cur))
    rows = stock_report.filter_rows(all_rows, hscode=hscode, owner_id=owner_id,
        anbar_id=anbar_id, location=location,
        unloaded_from=unloaded_from.isoformat() if unloaded_from else None,
        unloaded_to=unloaded_to.isoformat() if unloaded_to else None)
    totals, groups = stock_report.summarize(rows, group_by)
    if group_by != "none":
        for row in rows:
            row["group_key"] = stock_report.group_key(row, group_by)[0]
    def facet(id_key, name_key):
        values = {r[id_key]: r[name_key] for r in all_rows if r[id_key] is not None}
        return [{"id": key, "name": name} for key, name in sorted(values.items(), key=lambda item: str(item[1]))]
    return serializable({"as_of": datetime.now(timezone.utc), "group_by": group_by,
        "totals": totals, "groups": groups, "rows": rows, "facets": {
            "owners": facet("owner_id", "owner_name"), "anbars": facet("anbar_id", "anbar_name"),
            "locations": [{"id": key, "name": name} for key, name in stock_report.LOCATION_LABELS.items()
                          if any(r["location"] == key for r in all_rows)]}})


@router.get("/today", dependencies=[Depends(require_permission("non_customs.operations"))])
def server_today():
    with get_connection() as conn:
        with conn.cursor() as cur:
            return db.one(cur, "SELECT TO_CHAR(SYSDATE, 'YYYY-MM-DD') AS today FROM dual")


@router.get("/candidates", dependencies=[Depends(require_permission("non_customs.operations"))])
def candidates():
    with get_connection() as conn:
        with conn.cursor() as cur:
            used = {(r["receipt_id"], r["source_id"]) for r in db.rows(cur,
                'SELECT "RECEIPT_ID" AS receipt_id, "SOURCE_ID" AS source_id FROM "FA_NON_CUSTOMS"')}
            available = db.rows(cur, CANDIDATES_SQL)
            counts = Counter((r["receipt_id"], r["source_id"]) for r in available)
            items = [r for r in available if counts[(r["receipt_id"], r["source_id"])] == 1
                     and (r["receipt_id"], r["source_id"]) not in used]
    return serializable(items)

def validate_registration_date(start_date, settlement_confirmed):
    today = datetime.now(timezone(timedelta(hours=3, minutes=30))).date()
    if not settlement_confirmed or start_date > today:
        raise HTTPException(422, "تأیید تسویه و تاریخ شروع معتبر الزامی است")


def insert_registrations(cur, selections, start_date, actor, tally_id=None):
    """Caller holds the tally lock. Validate the entire batch before any insert."""
    available = db.rows(cur, CANDIDATES_SQL)
    seen, pending = set(), []
    for receipt_id, row in selections:
        key = (receipt_id, row.source_id)
        if key in seen:
            raise HTTPException(422, "یک ردیف از یک قبض را نمی‌توان دوبار انتخاب کرد")
        seen.add(key)
        if db.one(cur, 'SELECT 1 AS found FROM "FA_NON_CUSTOMS" WHERE "RECEIPT_ID"=:rid AND "SOURCE_ID"=:sid',
                  {"rid": receipt_id, "sid": row.source_id}):
            raise HTTPException(409, "این ردیف قبلاً ثبت شده است")
        matches = [r for r in available if r["receipt_id"] == receipt_id
                   and r["source_id"] == row.source_id
                   and (tally_id is None or r["tally_id"] == tally_id)]
        if len(matches) != 1:
            raise HTTPException(409, "ردیف باید متعلق به تالی انتخاب‌شده و دارای صورتحساب اصلی فعال و یکتا باشد")
        source = matches[0]
        if start_date < source["invoice_date"].date():
            raise HTTPException(422, "تاریخ شروع نمی‌تواند قبل از صدور صورتحساب اصلی باشد")
        values = validate_amounts(row, source, source["cargo"])
        pending.append({"rid": receipt_id, "sid": row.source_id, "iid": source["invoice_id"],
                        **values, "start_date": start_date, "actor": actor})
    for values in pending:
        cur.execute("""INSERT INTO "FA_NON_CUSTOMS"
            ("RECEIPT_ID","SOURCE_ID","ORIGINAL_INVOICE_ID","WEIGHT","QUANTITY","PALLETS","START_DATE","CREATED_BY")
            VALUES (:rid,:sid,:iid,:weight,:quantity,:pallets,:start_date,:actor)""", values)


@router.post("/tallies/{tally_id}/rows", status_code=201)
def register_many(tally_id: int, payload: BatchRegistration, user=Depends(require_permission("non_customs.operations"))):
    validate_registration_date(payload.start_date, payload.settlement_confirmed)
    with get_connection() as conn:
        with conn.cursor() as cur:
            db.lock_tally(cur, tally_id)
            insert_registrations(cur, [(row.receipt_id, row) for row in payload.rows],
                                 payload.start_date, user["id"], tally_id=tally_id)
        conn.commit()
    return {"registered": True, "count": len(payload.rows)}


@router.post("/receipts/{receipt_id}", status_code=201)
def register(receipt_id: int, payload: Registration, user=Depends(require_permission("non_customs.operations"))):
    validate_registration_date(payload.start_date, payload.settlement_confirmed)
    with get_connection() as conn:
        with conn.cursor() as cur:
            db.receipt(cur, receipt_id, lock=True)
            insert_registrations(cur, [(receipt_id, payload)], payload.start_date, user["id"])
        conn.commit()
    return {"registered": True}

@router.post("/receipts/{receipt_id}/rows/{source_id}/exit")
def record_exit(receipt_id: int, source_id: int, payload: Exit, user=Depends(require_permission("non_customs.operations"))):
    with get_connection() as conn:
        with conn.cursor() as cur:
            db.receipt(cur, receipt_id, lock=True)
            prior = db.one(cur, 'SELECT * FROM "FA_NON_CUSTOMS_EXIT" WHERE "REQUEST_ID"=:id', {"id": str(payload.request_id)})
            if prior:
                if prior["receipt_id"] != receipt_id or prior["source_id"] != source_id or any(prior[k] != getattr(payload,k) for k in ("weight","quantity","pallets")):
                    raise HTTPException(409, "شناسه درخواست قبلاً استفاده شده است")
                return {"recorded": True}
            source = next((r for r in stock(cur, receipt_id) if r["source_id"] == source_id), None)
            if source is None:
                raise HTTPException(404, "ردیف موجودی یافت نشد")
            values = validate_amounts(payload, source, source["cargo"])
            cur.execute("""INSERT INTO "FA_NON_CUSTOMS_EXIT"
                ("REQUEST_ID","RECEIPT_ID","SOURCE_ID","WEIGHT","QUANTITY","PALLETS","CREATED_BY")
                VALUES (:request_id,:rid,:sid,:weight,:quantity,:pallets,:actor)""",
                {"request_id": str(payload.request_id), "rid": receipt_id, "sid": source_id, **values, "actor": user["id"]})
        conn.commit()
    return {"recorded": True}
