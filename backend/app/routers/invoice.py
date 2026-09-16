# """Invoice (صورتحساب) endpoints.

# For now: a COMPUTE-ONLY preview. It reads a tally's real inputs (goods lines +
# storage rates + the five service junctions), runs the ported set_process_details
# logic in app.services.invoice_calc, and returns the computed detail rows WITHOUT
# persisting anything. Purpose: validate the port against the APEX golden case
# (generate 547 in APEX, compare the numbers) before we build the persisting
# generate/list/get endpoints.

# Storage numbers are confirmed (reconciled to the rial). Service numbers and the
# first-invoice tier timing are PROVISIONAL until the 547 golden case lands.
# """
# from decimal import Decimal

# from fastapi import APIRouter, Depends, HTTPException

# from app.auth.deps import get_current_user
# from app.services.base import fetch_all, fetch_one
# from app.services import invoice_calc as calc

# router = APIRouter(prefix="/invoice", tags=["invoice"])

# # --- storage inputs: goods lines LEFT JOIN their storage rate (CODE_GROUPE_KALA = id_kala_price) ---
# GOODS_SQL = """
# SELECT
#     d."CODE_GROUPE_KALA"  AS code_groupe_kala,
#     d."NUMBER_KALA"       AS number_kala,
#     d."WEIGHTE"           AS weight,
#     d."ZARIB_MAHAL"       AS zarib_mahal,
#     p."CODE"              AS kala_price_code,
#     p."price_30_day"      AS price_30_day,
#     p."price_60_day"      AS price_60_day,
#     p."price_90_day"      AS price_90_day
# FROM "FA_TALI_DETAILES" d
# LEFT JOIN "fa_kala_price" p ON p."id_kala_price" = d."CODE_GROUPE_KALA"
# WHERE d."ID_HEADERS_TALI" = :tid AND d."IS_DELETED" = 'no'
# ORDER BY d."ID_TALI_DETAILS"
# """

# # prior invoices force the 30-day tier; this counts them (timing unknown -> golden case)
# PRIOR_INVOICE_SQL = """
# SELECT COUNT(*) AS cnt FROM "FA_SORAT_HESAB_HEADER"
# WHERE "TALI_ID_HEADER" = :tid AND "SORAT_IS_DELETED" = 'no'
# """

# # the save gate: an invoice requires a receipt (قبض انبار) to exist for the tally
# RECEIPT_SQL = """
# SELECT COUNT(*) AS cnt FROM "fa_ghabz_anbar_header"
# WHERE "TALI_ID" = :tid AND "IS_DELETED" = 'no'
# """

# # --- the five service junctions, each joined to its rate catalog (raw values; summed in Python) ---
# OTHER_SERVICE_SQL = """
# SELECT c."price" AS price, j."NUMBER_SERVICE" AS number_service
# FROM "fa_tali_kala_other_service" j
# JOIN "fa_kala_other_service" c ON c."id_kala_other_service" = j."kala_other_service_id"
# WHERE j."tali_id" = :tid  -- NB: set_cal does NOT filter junction IS_DELETED (soft-deleted junctions still bill)
# """
# STRIP_SQL = """
# SELECT j."pricing_type" AS pricing_type,
#        j."NUMBER_SERVICE" AS number_service,
#        c."normal" AS normal, c."non_standard" AS non_standard, c."dangerous" AS dangerous
# FROM "fa_tali_kala_strip" j
# JOIN "fa_kala_strip" c ON c."id_kala_strip" = j."kala_strip_id"
# WHERE j."tali_id" = :tid  -- NB: set_cal does NOT filter junction IS_DELETED (soft-deleted junctions still bill)
# """
# NIGHT_STOP_SQL = """
# SELECT c."price" AS price, j."NUMBER_SERVICE" AS number_service
# FROM "fa_tali_kala_time_stop_vehicle" j
# JOIN "fa_kala_time_stop_vehicle" c ON c."id_kala_time_stop_vehicle" = j."kala_time_stop_vehicle_id"
# WHERE j."tali_id" = :tid  -- NB: set_cal does NOT filter junction IS_DELETED (soft-deleted junctions still bill)
# """
# DIAMOUND_SQL = """
# SELECT CASE NVL(j."pricing_type", 'off_hours')
#            WHEN 'holiday' THEN c."price_holiday"
#            ELSE c."price_gher_edari"
#        END AS price
#        , j."NUMBER_SERVICE" AS number_service
# FROM "fa_tali_kala_diamound" j
# JOIN "fa_kala_diamound" c ON c."id_kala_diamound" = j."kala_diamound_id"
# WHERE j."tali_id" = :tid  -- NB: set_cal does NOT filter junction IS_DELETED (soft-deleted junctions still bill)
# """
# VEHICLE_ENTER_SQL = """
# SELECT c."price" AS price, j."NUMBER_SERVICE" AS number_service
# FROM "fa_tali_kala_vehicle_enter_price" j
# JOIN "fa_kala_vehicle_enter_price" c ON c."id_kala_vehicle_enter_price" = j."kala_vehicle_enter_price_id"
# WHERE j."tali_id" = :tid  -- NB: set_cal does NOT filter junction IS_DELETED (soft-deleted junctions still bill)
# """


# # Pricing Type on the strip junction selects which rate column bills. NULL/unknown ->
# # "normal", so pre-existing junctions (and the tally-549 golden case) are unchanged.
# _STRIP_COLUMN = {"normal": "normal", "non_standard": "non_standard", "dangerous": "dangerous"}


# def _strip_price(row: dict):
#     col = _STRIP_COLUMN.get((row.get("pricing_type") or "normal"), "normal")
#     return row[col]


# def _row_json(r: calc.InvoiceDetailRow) -> dict:
#     # Decimals -> strings so big rial values keep exact precision over JSON.
#     return {
#         "description": r.description,
#         "number_kala": r.number_kala,
#         "weight": None if r.weight is None else str(r.weight),
#         "price": None if r.price is None else str(r.price),
#     }


# @router.get("/from-tally/{tali_id}/preview", dependencies=[Depends(get_current_user)])
# def preview_from_tally(tali_id: int):
#     """Compute a tally's invoice detail rows without saving. Returns storage rows,
#     service rows, the tier used, and the grand total. Does not persist."""
#     goods = fetch_all(GOODS_SQL, {"tid": tali_id})
#     if not goods:
#         raise HTTPException(status_code=404, detail="تالی یا ردیف‌های کالا یافت نشد")

#     prior = fetch_one(PRIOR_INVOICE_SQL, {"tid": tali_id}) or {"cnt": 0}
#     has_receipt = (fetch_one(RECEIPT_SQL, {"tid": tali_id}) or {"cnt": 0})["cnt"] > 0

#     # build storage inputs
#     lines: list[calc.GoodsLine] = []
#     rates: dict[int, calc.KalaPriceRate] = {}
#     for g in goods:
#         code = g["code_groupe_kala"]
#         lines.append(calc.GoodsLine(
#             code_groupe_kala=code,
#             number_kala=g["number_kala"],
#             weight=calc.to_decimal(g["weight"]),
#             zarib_mahal=calc.to_decimal(g["zarib_mahal"]),
#             kala_code=g["kala_price_code"],
#         ))
#         if code not in rates and g["price_30_day"] is not None:
#             rates[code] = calc.KalaPriceRate(
#                 id_kala_price=code,
#                 price_30_day=calc.to_decimal(g["price_30_day"]),
#                 price_60_day=calc.to_decimal(g["price_60_day"]),
#                 price_90_day=calc.to_decimal(g["price_90_day"]),
#             )

#     storage_rows, tier = calc.compute_storage_rows(lines, rates, prior_invoice_count=prior["cnt"])

#     # services. strip: each junction's pricing_type picks normal|non_standard|dangerous.
#     other = fetch_all(OTHER_SERVICE_SQL, {"tid": tali_id})
#     strip = fetch_all(STRIP_SQL, {"tid": tali_id})
#     night = fetch_all(NIGHT_STOP_SQL, {"tid": tali_id})
#     diamound = fetch_all(DIAMOUND_SQL, {"tid": tali_id})
#     vehicle = fetch_all(VEHICLE_ENTER_SQL, {"tid": tali_id})

#     service_rows = calc.compute_service_rows(
#         other_service_prices=[r["price"] for r in other],
#         other_service_counts=[r["number_service"] for r in other],
#         strip_values=[_strip_price(r) for r in strip],
#         strip_counts=[r["number_service"] for r in strip],
#         night_stop_prices=[r["price"] for r in night],
#         night_stop_counts=[r["number_service"] for r in night],
#         diamound_prices=[r["price"] for r in diamound],
#         diamound_counts=[r["number_service"] for r in diamound],
#         vehicle_enter_prices=[r["price"] for r in vehicle],
#         vehicle_enter_counts=[r["number_service"] for r in vehicle],
#     )

#     all_rows = storage_rows + service_rows
#     grand_total = sum((r.price for r in all_rows if r.price is not None), Decimal(0))

#     return {
#         "tali_id": tali_id,
#         "has_receipt": has_receipt,          # save gate: an invoice needs a receipt
#         "prior_invoice_count": prior["cnt"],
#         "tier_used": tier,                   # 30 / 60 / 90 (fixed multiplier)
#         "storage_rows": [_row_json(r) for r in storage_rows],
#         "service_rows": [_row_json(r) for r in service_rows],
#         "grand_total": str(grand_total),
#         "provisional": {
#             "services": "Each service amount is its selected rate multiplied by its optional quantity; blank quantity defaults to one",
#             "strip": "column chosen per junction via pricing_type (normal|non_standard|dangerous); NULL -> normal, so prior data is unchanged",
#             "tier_timing": "VERIFIED: first invoice -> l_time_rest=45 -> 60-day tier; a prior invoice forces 30-day",
#         },
#     }


"""Invoice (صورتحساب) endpoints.

For now: a COMPUTE-ONLY preview. It reads a tally's real inputs (goods lines +
storage rates + the five service junctions), runs the ported set_process_details
logic in app.services.invoice_calc, and returns the computed detail rows WITHOUT
persisting anything. Purpose: validate the port against the APEX golden case
(generate 547 in APEX, compare the numbers) before we build the persisting
generate/list/get endpoints.

Storage numbers are confirmed (reconciled to the rial). Service numbers and the
first-invoice tier timing are PROVISIONAL until the 547 golden case lands.
"""
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException

from app.auth.deps import get_current_user
from app.services.base import fetch_all, fetch_one
from app.services import invoice_calc as calc

router = APIRouter(prefix="/invoice", tags=["invoice"])

# --- storage inputs: goods lines LEFT JOIN their storage rate (CODE_GROUPE_KALA = id_kala_price) ---
GOODS_SQL = """
SELECT
    d."CODE_GROUPE_KALA"  AS code_groupe_kala,
    d."NUMBER_KALA"       AS number_kala,
    d."WEIGHTE"           AS weight,
    d."ZARIB_MAHAL"       AS zarib_mahal,
    p."CODE"              AS kala_price_code,
    p."price_30_day"      AS price_30_day,
    p."price_60_day"      AS price_60_day,
    p."price_90_day"      AS price_90_day
FROM "FA_TALI_DETAILES" d
LEFT JOIN "fa_kala_price" p ON p."id_kala_price" = d."CODE_GROUPE_KALA"
WHERE d."ID_HEADERS_TALI" = :tid AND d."IS_DELETED" = 'no'
ORDER BY d."ID_TALI_DETAILS"
"""

# prior invoices force the 30-day tier; this counts them (timing unknown -> golden case)
PRIOR_INVOICE_SQL = """
SELECT COUNT(*) AS cnt FROM "FA_SORAT_HESAB_HEADER"
WHERE "TALI_ID_HEADER" = :tid AND "SORAT_IS_DELETED" = 'no'
"""

# the save gate: an invoice requires a receipt (قبض انبار) to exist for the tally
RECEIPT_SQL = """
SELECT COUNT(*) AS cnt FROM "fa_ghabz_anbar_header"
WHERE "TALI_ID" = :tid AND "IS_DELETED" = 'no'
"""

# --- the five service junctions, each joined to its rate catalog (raw values; summed in Python) ---
OTHER_SERVICE_SQL = """
SELECT c."price" AS price, j."NUMBER_SERVICE" AS number_service
FROM "fa_tali_kala_other_service" j
JOIN "fa_kala_other_service" c ON c."id_kala_other_service" = j."kala_other_service_id"
WHERE j."tali_id" = :tid  -- NB: set_cal does NOT filter junction IS_DELETED (soft-deleted junctions still bill)
"""
STRIP_SQL = """
SELECT j."pricing_type" AS pricing_type,
       j."NUMBER_SERVICE" AS number_service,
       c."normal" AS normal, c."non_standard" AS non_standard, c."dangerous" AS dangerous
FROM "fa_tali_kala_strip" j
JOIN "fa_kala_strip" c ON c."id_kala_strip" = j."kala_strip_id"
WHERE j."tali_id" = :tid  -- NB: set_cal does NOT filter junction IS_DELETED (soft-deleted junctions still bill)
"""
NIGHT_STOP_SQL = """
SELECT c."price" AS price, j."NUMBER_SERVICE" AS number_service
FROM "fa_tali_kala_time_stop_vehicle" j
JOIN "fa_kala_time_stop_vehicle" c ON c."id_kala_time_stop_vehicle" = j."kala_time_stop_vehicle_id"
WHERE j."tali_id" = :tid  -- NB: set_cal does NOT filter junction IS_DELETED (soft-deleted junctions still bill)
"""
DIAMOUND_SQL = """
SELECT CASE NVL(j."pricing_type", 'off_hours')
           WHEN 'holiday' THEN c."price_holiday"
           ELSE c."price_gher_edari"
       END AS price
       , j."NUMBER_SERVICE" AS number_service
FROM "fa_tali_kala_diamound" j
JOIN "fa_kala_diamound" c ON c."id_kala_diamound" = j."kala_diamound_id"
WHERE j."tali_id" = :tid  -- NB: set_cal does NOT filter junction IS_DELETED (soft-deleted junctions still bill)
"""
VEHICLE_ENTER_SQL = """
SELECT c."price" AS price, j."NUMBER_SERVICE" AS number_service
FROM "fa_tali_kala_vehicle_enter_price" j
JOIN "fa_kala_vehicle_enter_price" c ON c."id_kala_vehicle_enter_price" = j."kala_vehicle_enter_price_id"
WHERE j."tali_id" = :tid  -- NB: set_cal does NOT filter junction IS_DELETED (soft-deleted junctions still bill)
"""


# Pricing Type on the strip junction selects which rate column bills. NULL/unknown ->
# "normal", so pre-existing junctions (and the tally-549 golden case) are unchanged.
_STRIP_COLUMN = {"normal": "normal", "non_standard": "non_standard", "dangerous": "dangerous"}


def _strip_price(row: dict):
    col = _STRIP_COLUMN.get((row.get("pricing_type") or "normal"), "normal")
    return row[col]


def _row_json(r: calc.InvoiceDetailRow) -> dict:
    # Decimals -> strings so big rial values keep exact precision over JSON.
    return {
        "description": r.description,
        "number_kala": r.number_kala,
        "weight": None if r.weight is None else str(r.weight),
        "price": None if r.price is None else str(r.price),
    }


@router.get("/from-tally/{tali_id}/preview", dependencies=[Depends(get_current_user)])
def preview_from_tally(tali_id: int):
    """Compute a tally's invoice detail rows without saving. Returns storage rows,
    service rows, the tier used, and the grand total. Does not persist."""
    goods = fetch_all(GOODS_SQL, {"tid": tali_id})
    if not goods:
        raise HTTPException(status_code=404, detail="تالی یا ردیف‌های کالا یافت نشد")

    prior = fetch_one(PRIOR_INVOICE_SQL, {"tid": tali_id}) or {"cnt": 0}
    has_receipt = (fetch_one(RECEIPT_SQL, {"tid": tali_id}) or {"cnt": 0})["cnt"] > 0

    # build storage inputs
    lines: list[calc.GoodsLine] = []
    rates: dict[int, calc.KalaPriceRate] = {}
    for g in goods:
        code = g["code_groupe_kala"]
        lines.append(calc.GoodsLine(
            code_groupe_kala=code,
            number_kala=g["number_kala"],
            weight=calc.to_decimal(g["weight"]),
            zarib_mahal=calc.to_decimal(g["zarib_mahal"]),
            kala_code=g["kala_price_code"],
        ))
        if code not in rates and g["price_30_day"] is not None:
            rates[code] = calc.KalaPriceRate(
                id_kala_price=code,
                price_30_day=calc.to_decimal(g["price_30_day"]),
                price_60_day=calc.to_decimal(g["price_60_day"]),
                price_90_day=calc.to_decimal(g["price_90_day"]),
            )

    storage_rows, tier = calc.compute_storage_rows(lines, rates, prior_invoice_count=prior["cnt"])

    # services. strip: each junction's pricing_type picks normal|non_standard|dangerous.
    other = fetch_all(OTHER_SERVICE_SQL, {"tid": tali_id})
    strip = fetch_all(STRIP_SQL, {"tid": tali_id})
    night = fetch_all(NIGHT_STOP_SQL, {"tid": tali_id})
    diamound = fetch_all(DIAMOUND_SQL, {"tid": tali_id})
    vehicle = fetch_all(VEHICLE_ENTER_SQL, {"tid": tali_id})

    service_rows = calc.compute_service_rows(
        other_service_prices=[r["price"] for r in other],
        other_service_counts=[r["number_service"] for r in other],
        strip_values=[_strip_price(r) for r in strip],
        strip_counts=[r["number_service"] for r in strip],
        night_stop_prices=[r["price"] for r in night],
        night_stop_counts=[r["number_service"] for r in night],
        diamound_prices=[r["price"] for r in diamound],
        diamound_counts=[r["number_service"] for r in diamound],
        vehicle_enter_prices=[r["price"] for r in vehicle],
        vehicle_enter_counts=[r["number_service"] for r in vehicle],
    )

    all_rows = storage_rows + service_rows
    grand_total = sum((r.price for r in all_rows if r.price is not None), Decimal(0))

    return {
        "tali_id": tali_id,
        "has_receipt": has_receipt,          # save gate: an invoice needs a receipt
        "prior_invoice_count": prior["cnt"],
        "tier_used": tier,                   # 30 / 60 / 90 (fixed multiplier)
        "storage_rows": [_row_json(r) for r in storage_rows],
        "service_rows": [_row_json(r) for r in service_rows],
        "grand_total": str(grand_total),
        "provisional": {
            "services": "Each service amount is its selected rate multiplied by its optional quantity; blank quantity defaults to one",
            "strip": "column chosen per junction via pricing_type (normal|non_standard|dangerous); NULL -> normal, so prior data is unchanged",
            "tier_timing": "VERIFIED: first invoice -> l_time_rest=45 -> 60-day tier; a prior invoice forces 30-day",
        },
    }


# Saved invoices must be read from their persisted rows, not recalculated using
# today's tariffs. Keep these routes separate from the compute-only preview.
INVOICE_LIST_SQL = """
SELECT s."ID_SORAT" AS id_sorat, s."SORAT_CREATE_AT" AS created_at,
       s."COMPANY_NAME" AS seller_name, s."BUYER_COMPANY_ID" AS buyer_id,
       COALESCE(NULLIF(TRIM(o."COMPANY_NAME"), ''),
                NULLIF(TRIM(o."NAME" || ' ' || o."FAMILY"), '')) AS buyer_name,
       s."TALI_ID_HEADER" AS tali_id, t."TALI_NUMBER" AS tali_number,
       s."ID_GHABZ_ANBAR" AS ghabz_id, s."IS_ACCEPTED" AS is_accepted,
       (SELECT SUM(NVL(d."PRICE_DETAILS", 0) - NVL(d."TAKHFIF_DETAILS", 0))
          FROM "FA_SORA_HESAB_DETAILS" d
         WHERE d."ID_SORA_HEADER" = s."ID_SORAT"
           AND NVL(d."IS_DELETED", 'N') NOT IN ('Y', 'yes')) AS grand_total
FROM "FA_SORAT_HESAB_HEADER" s
LEFT JOIN "FA_PRODUCT_OWNER" o ON o."ID_OWNER" = s."BUYER_COMPANY_ID"
LEFT JOIN "FA_TALI_HEADER" t ON t."ID_TALI" = s."TALI_ID_HEADER"
WHERE NVL(s."SORAT_IS_DELETED", 'no') = 'no'
ORDER BY s."ID_SORAT" DESC
"""

INVOICE_HEADER_SQL = """
SELECT s."ID_SORAT" AS id_sorat, s."SORAT_CREATE_AT" AS created_at,
       s."COMPANY_NAME" AS seller_name,
       s."SELLER_COMPANY_ADDRESS" AS seller_address,
       s."SELLER_COMPANY_PHONE" AS seller_phone,
       s."SELLER_EGHTESADI_CODE" AS seller_economic_code,
       s."SELLER_SHENASE_MELLI" AS seller_national_id,
       s."SELLER_CODE_POSTI" AS seller_postal_code,
       s."BUYER_COMPANY_ID" AS buyer_id,
       COALESCE(NULLIF(TRIM(o."COMPANY_NAME"), ''),
                NULLIF(TRIM(o."NAME" || ' ' || o."FAMILY"), '')) AS buyer_name,
       s."BUYER_COMPANY_ADDRESS" AS buyer_address,
       s."BUYER_COMPANY_PHONE" AS buyer_phone,
       s."BUYER_EGHTESADI_CODE" AS buyer_economic_code,
       s."BUYER_SHENASE_MELLI" AS buyer_national_id,
       s."BUYER_CODE_POSTI" AS buyer_postal_code,
       s."BUYER_KOTATH_CODE" AS buyer_kotath_code,
       s."BUYER_GHABZ_ID" AS buyer_ghabz_number,
       DBMS_LOB.SUBSTR(s."DESCRIPTION", 4000, 1) AS description,
       s."NAME_MANEGER" AS manager_name,
       s."VAHED_MALIE" AS finance_name,
       s."NAMAYANDEH_COMPANY" AS representative_name,
       s."TALI_ID_HEADER" AS tali_id, t."TALI_NUMBER" AS tali_number,
       s."ID_GHABZ_ANBAR" AS ghabz_id, s."IS_ACCEPTED" AS is_accepted
FROM "FA_SORAT_HESAB_HEADER" s
LEFT JOIN "FA_PRODUCT_OWNER" o ON o."ID_OWNER" = s."BUYER_COMPANY_ID"
LEFT JOIN "FA_TALI_HEADER" t ON t."ID_TALI" = s."TALI_ID_HEADER"
WHERE s."ID_SORAT" = :invoice_id AND NVL(s."SORAT_IS_DELETED", 'no') = 'no'
"""

INVOICE_DETAILS_SQL = """
SELECT "ID_SORA_DETAILS" AS id_detail, "DESCRIPTION" AS description,
       "NUMBER_KALA" AS quantity, "WEIGHTE" AS weight,
       "PRICE_DETAILS" AS price, "TAKHFIF_DETAILS" AS discount,
       "TAKHFIF_ALL" AS amount
FROM "FA_SORA_HESAB_DETAILS"
WHERE "ID_SORA_HEADER" = :invoice_id
  AND NVL("IS_DELETED", 'N') NOT IN ('Y', 'yes')
ORDER BY "ID_SORA_DETAILS"
"""


def _serialize_saved(row: dict) -> dict:
    from datetime import date, datetime
    return {key: (value.isoformat() if isinstance(value, (date, datetime))
                  else str(value) if isinstance(value, Decimal) else value)
            for key, value in row.items()}


@router.get('/list', dependencies=[Depends(get_current_user)])
def list_invoices():
    return [_serialize_saved(row) for row in fetch_all(INVOICE_LIST_SQL)]


@router.get('/{invoice_id}', dependencies=[Depends(get_current_user)])
def get_invoice(invoice_id: int):
    header = fetch_one(INVOICE_HEADER_SQL, {'invoice_id': invoice_id})
    if header is None:
        raise HTTPException(status_code=404, detail='صورتحساب یافت نشد')
    details = fetch_all(INVOICE_DETAILS_SQL, {'invoice_id': invoice_id})
    total = sum(((calc.to_decimal(row['price']) or Decimal(0))
                 - (calc.to_decimal(row['discount']) or Decimal(0)) for row in details), Decimal(0))
    return {'header': _serialize_saved(header),
            'details': [_serialize_saved(row) for row in details],
            'grand_total': str(total)}
