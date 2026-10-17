"""Reports: income from saved invoices, and the goods now in the warehouse."""
from datetime import date, datetime, time, timedelta
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, Query

from app.auth.deps import require_permission
from app.core.db import get_connection
from app.routers.abandoned import STILL_IN_WAREHOUSE_SQL, goods_sql
from app.services import income_report, stock_report
from app.services import receipt_db as db
from app.services.abandoned_stock import attach_remaining_goods
from app.services.insurance_cover import TOTALS_SQL
from app.services.report_json import serializable

router = APIRouter(prefix="/reports", tags=["reports"])

# A year of invoices is a few thousand rows; refuse to ship an unbounded list.
MAX_LINES = 20000

INCOME_ROWS_SQL = """
SELECT s."ID_SORAT" AS invoice_id, s."SORAT_CREATE_AT" AS issued_at,
       s."TALI_ID_HEADER" AS tally_id, t."TALI_NUMBER" AS tally_number,
       g."GHABZ_NUMBER" AS receipt_number,
       COALESCE(NULLIF(TRIM(o."COMPANY_NAME"), ''),
                NULLIF(TRIM(o."NAME" || ' ' || o."FAMILY"), '')) AS buyer_name,
       d."ID_SORA_DETAILS" AS line_id, d."ROW_KIND" AS row_kind,
       d."DESCRIPTION" AS description, d."NUMBER_KALA" AS quantity, d."WEIGHTE" AS weight,
       NVL(d."PRICE_DETAILS", 0) - NVL(d."TAKHFIF_DETAILS", 0) AS amount,
       rem."ORIGINAL_INVOICE_ID" AS original_invoice_id
FROM "FA_SORAT_HESAB_HEADER" s
JOIN "FA_SORA_HESAB_DETAILS" d ON d."ID_SORA_HEADER" = s."ID_SORAT"
LEFT JOIN "FA_REMAINING_INVOICE" rem ON rem."INVOICE_ID" = s."ID_SORAT"
LEFT JOIN "FA_TALI_HEADER" t ON t."ID_TALI" = s."TALI_ID_HEADER"
LEFT JOIN "fa_ghabz_anbar_header" g ON g."ID_ghabz" = s."ID_GHABZ_ANBAR"
LEFT JOIN "FA_PRODUCT_OWNER" o ON o."ID_OWNER" = s."BUYER_COMPANY_ID"
WHERE NVL(s."SORAT_IS_DELETED", 'no') = 'no'
  AND NVL(d."IS_DELETED", 'N') NOT IN ('Y', 'yes')
  AND s."SORAT_CREATE_AT" >= :start_at AND s."SORAT_CREATE_AT" < :end_before
ORDER BY s."SORAT_CREATE_AT", s."ID_SORAT", d."ID_SORA_DETAILS"
"""

# Cancelling an invoice only marks its header deleted (routers/invoice.py), so the
# detail rows still hold its amounts. SORAT_MODIFY_AT is then the cancellation time.
CANCELLED_SQL = """
SELECT s."ID_SORAT" AS invoice_id, s."SORAT_CREATE_AT" AS issued_at,
       s."SORAT_MODIFY_AT" AS cancelled_at,
       s."TALI_ID_HEADER" AS tally_id, t."TALI_NUMBER" AS tally_number,
       g."GHABZ_NUMBER" AS receipt_number,
       COALESCE(NULLIF(TRIM(o."COMPANY_NAME"), ''),
                NULLIF(TRIM(o."NAME" || ' ' || o."FAMILY"), '')) AS buyer_name,
       (SELECT NVL(SUM(NVL(d."PRICE_DETAILS", 0) - NVL(d."TAKHFIF_DETAILS", 0)), 0)
          FROM "FA_SORA_HESAB_DETAILS" d
         WHERE d."ID_SORA_HEADER" = s."ID_SORAT"
           AND NVL(d."IS_DELETED", 'N') NOT IN ('Y', 'yes')) AS amount,
       CASE WHEN EXISTS (SELECT 1 FROM "FA_SORAT_HESAB_HEADER" n
                          WHERE n."ID_GHABZ_ANBAR" = s."ID_GHABZ_ANBAR"
                            AND n."ID_SORAT" > s."ID_SORAT"
                            AND NVL(n."SORAT_IS_DELETED", 'no') = 'no')
            THEN 1 ELSE 0 END AS reissued
FROM "FA_SORAT_HESAB_HEADER" s
LEFT JOIN "FA_TALI_HEADER" t ON t."ID_TALI" = s."TALI_ID_HEADER"
LEFT JOIN "fa_ghabz_anbar_header" g ON g."ID_ghabz" = s."ID_GHABZ_ANBAR"
LEFT JOIN "FA_PRODUCT_OWNER" o ON o."ID_OWNER" = s."BUYER_COMPANY_ID"
WHERE s."SORAT_IS_DELETED" = 'yes'
  AND s."SORAT_CREATE_AT" >= :start_at AND s."SORAT_CREATE_AT" < :end_before
ORDER BY s."SORAT_CREATE_AT", s."ID_SORAT"
"""

STOCK_TALLIES_SQL = f"""
SELECT h."ID_TALI" AS id, h."TALI_NUMBER" AS tally_number, h."DATE_UNLOADING" AS unloaded_at,
       h."ID_PRODUCT_OWNEAR" AS owner_id,
       COALESCE(NULLIF(TRIM(o."COMPANY_NAME"), ''),
                NULLIF(TRIM(o."NAME" || ' ' || o."FAMILY"), '')) AS owner_name,
       h."IS_VOLUMETRIC" AS cargo_type,
       h."IS_BIMEH" AS is_bimeh, h."NUMBER_BIMEH" AS policy_numbers,
       h."COMPANY_BIMEH" AS insurance_company
FROM "FA_TALI_HEADER" h
LEFT JOIN "FA_PRODUCT_OWNER" o ON o."ID_OWNER" = h."ID_PRODUCT_OWNEAR"
WHERE h."IS_DELETED" = 'no'
  {STILL_IN_WAREHOUSE_SQL}
ORDER BY h."DATE_UNLOADING", h."ID_TALI"
"""

# Package type is stored either as text or as the id of an FA_SYS_TERMS row.
STOCK_DETAILS_SQL = f"""
WITH eligible AS ({STOCK_TALLIES_SQL})
SELECT d."ID_TALI_DETAILS" AS detail_id,
       COALESCE(TO_CHAR(pt."SYS_TERM_VALUE"), d."TYPE_BASTEM") AS package_type,
       d."ID_ANBAR" AS anbar_id, a."NAME_ANBAR" AS anbar_name, tg."NAME_TAGH" AS tagh_name,
       d."ZARIB_MAHAL" AS zarib_mahal,
       COALESCE(d."ROW_PALLETS", d."NUMBER_PALLET") AS pallets,
       (SELECT NVL(SUM(p."PALLETS"), 0)
          FROM "FA_RECEIPT_PALLETS" p
          JOIN "fa_ghabz_anbar_header" r ON r."ID_ghabz" = p."RECEIPT_ID"
         WHERE p."TALLY_DETAIL_ID" = d."ID_TALI_DETAILS"
           AND r."IS_DELETED" = 'no' AND NVL(r."IS_MASTER", 'no') = 'no'
           AND EXISTS (SELECT 1 FROM "FA_SORAT_HESAB_HEADER" i
                        WHERE i."ID_GHABZ_ANBAR" = r."ID_ghabz"
                          AND NVL(i."SORAT_IS_DELETED", 'no') = 'no'
                          AND NOT EXISTS (SELECT 1 FROM "FA_REMAINING_INVOICE" extra
                                           WHERE extra."INVOICE_ID" = i."ID_SORAT"))) AS released_pallets,
       d."VALUE_KALA" AS value_kala, d."INSURANCE_EXPIRY_DATE" AS insurance_expiry_date,
       d."NUMBER_HAMEL" AS number_hamel, d."CONTAINER_TYPE" AS container_type,
       d."CONTAINER_NUMBER" AS container_number
FROM "FA_TALI_DETAILES" d
JOIN eligible h ON h.id = d."ID_HEADERS_TALI"
LEFT JOIN "FA_ANBAR" a ON a."ID_ANBAR" = d."ID_ANBAR"
LEFT JOIN "FA_TAGH_ANBAR" tg ON tg."ID_TAGH" = d."ID_TAGH_ANBAR"
LEFT JOIN "FA_SYS_TERMS" pt ON TO_CHAR(pt."SYS_TERM_ID") = d."TYPE_BASTEM"
WHERE d."IS_DELETED" = 'no'
"""


def report_period(date_from: date = Query(alias="from"), date_to: date = Query(alias="to")):
    if date_to < date_from:
        raise HTTPException(422, "تاریخ پایان نمی‌تواند پیش از تاریخ شروع باشد")
    return date_from, date_to


def _period_rows(sql, period):
    start, end = period
    with get_connection() as conn:
        with conn.cursor() as cur:
            return db.rows(cur, sql, {
                "start_at": datetime.combine(start, time.min),
                "end_before": datetime.combine(end + timedelta(days=1), time.min)})


def income_rows(period):
    return _period_rows(INCOME_ROWS_SQL, period)


def cancelled_rows(period):
    return _period_rows(CANCELLED_SQL, period)


@router.get("/income")
def income_summary(period=Depends(report_period),
                   user: dict = Depends(require_permission("reports.income"))):
    """Income per invoice-row category and the grand totals, by invoice issue date.

    Income counts active invoices only. An invoice that was cancelled and issued
    again counts once, under the new invoice; cancelled ones are listed apart.
    Prepayment is a payment, not income: it only reduces the payable balance.
    """
    result = income_report.summarize(income_rows(period))
    cancelled = income_report.summarize_cancelled(cancelled_rows(period))
    return serializable({"from": period[0], "to": period[1], **result, "cancelled": cancelled})


@router.get("/income/lines")
def income_lines(period=Depends(report_period), category: str | None = None,
                 user: dict = Depends(require_permission("reports.income"))):
    """Every invoice row in the period, optionally of one category."""
    if category is not None and category not in income_report.CATEGORY_LABELS:
        raise HTTPException(422, "دستهٔ درخواستی نامعتبر است")
    lines = [line for line in income_report.classified(income_rows(period))
             if category is None or line["category"] == category]
    total = sum((line["amount"] for line in lines), Decimal(0))
    shown = [{**line, "category_label": income_report.CATEGORY_LABELS[line["category"]]}
             for line in lines[:MAX_LINES]]
    return serializable({"from": period[0], "to": period[1], "category": category,
                         "total": total, "truncated": len(lines) > MAX_LINES, "lines": shown})


@router.get("/stock")
def stock(group_by: str = "hscode", hscode: str | None = None, owner_id: int | None = None,
          anbar_id: int | None = None, location: str | None = None,
          unloaded_from: date | None = None, unloaded_to: date | None = None,
          user: dict = Depends(require_permission("reports.stock"))):
    """The goods in the warehouse now: one row per tally goods row still in stock,
    plus totals and groups (by HS code, owner, warehouse, location type or tally)."""
    if group_by not in stock_report.GROUP_BY:
        raise HTTPException(422, "نوع گروه‌بندی نامعتبر است")
    if location and location not in stock_report.LOCATION_LABELS:
        raise HTTPException(422, "نوع محل نامعتبر است")
    with get_connection() as conn:
        with conn.cursor() as cur:
            tallies = db.rows(cur, STOCK_TALLIES_SQL)
            goods_rows = db.rows(cur, goods_sql(STOCK_TALLIES_SQL)) if tallies else []
            details = db.rows(cur, STOCK_DETAILS_SQL) if tallies else []
            # insured_ceiling is MAX(INSURED_VALUE) over a tally's rows: the policy
            # value repeated on each row, read once.
            ceilings = {int(row["id_tali"]): row["insured_ceiling"]
                        for row in db.rows(cur, TOTALS_SQL)}

    in_stock = attach_remaining_goods(tallies, goods_rows, detailed=True)
    insured = {tally["id"]: stock_report.tally_insured_value(
                   tally.get("is_bimeh"), ceilings.get(tally["id"]))
               for tally in in_stock}
    all_rows = stock_report.build_rows(
        in_stock, {row["detail_id"]: row for row in details}, insured)
    rows = stock_report.filter_rows(
        all_rows, hscode=hscode, owner_id=owner_id, anbar_id=anbar_id, location=location,
        unloaded_from=unloaded_from.isoformat() if unloaded_from else None,
        unloaded_to=unloaded_to.isoformat() if unloaded_to else None)

    totals_row, groups = stock_report.summarize(rows, group_by)
    if group_by != "none":
        for row in rows:
            row["group_key"] = stock_report.group_key(row, group_by)[0]
    return serializable({
        "as_of": datetime.now(), "group_by": group_by, "totals": totals_row,
        "groups": groups, "rows": rows,
        "facets": {
            "owners": _facet(all_rows, "owner_id", "owner_name"),
            "anbars": _facet(all_rows, "anbar_id", "anbar_name"),
            "locations": [{"id": key, "name": stock_report.LOCATION_LABELS[key]}
                          for key in stock_report.LOCATION_LABELS
                          if any(row["location"] == key for row in all_rows)],
        },
    })


def _facet(rows, id_field, name_field):
    seen = {row[id_field]: row[name_field] for row in rows if row[id_field] is not None}
    return [{"id": key, "name": name} for key, name in sorted(seen.items(), key=lambda kv: str(kv[1]))]
