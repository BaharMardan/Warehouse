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
# SELECT c."normal" AS normal, c."dangerous" AS dangerous
# FROM "fa_tali_kala_strip" j
# JOIN "fa_kala_strip" c ON c."id_kala_strip" = j."kala_strip_id"
# WHERE j."tali_id" = :tid  -- NB: set_cal does NOT filter junction IS_DELETED (soft-deleted junctions still bill)
# """
# NIGHT_STOP_SQL = """
# SELECT c."price" AS price
# FROM "fa_tali_kala_time_stop_vehicle" j
# JOIN "fa_kala_time_stop_vehicle" c ON c."id_kala_time_stop_vehicle" = j."kala_time_stop_vehicle_id"
# WHERE j."tali_id" = :tid  -- NB: set_cal does NOT filter junction IS_DELETED (soft-deleted junctions still bill)
# """
# DIAMOUND_SQL = """
# SELECT c."price_gher_edari" AS price
# FROM "fa_tali_kala_diamound" j
# JOIN "fa_kala_diamound" c ON c."id_kala_diamound" = j."kala_diamound_id"
# WHERE j."tali_id" = :tid  -- NB: set_cal does NOT filter junction IS_DELETED (soft-deleted junctions still bill)
# """
# VEHICLE_ENTER_SQL = """
# SELECT c."price" AS price
# FROM "fa_tali_kala_vehicle_enter_price" j
# JOIN "fa_kala_vehicle_enter_price" c ON c."id_kala_vehicle_enter_price" = j."kala_vehicle_enter_price_id"
# WHERE j."tali_id" = :tid  -- NB: set_cal does NOT filter junction IS_DELETED (soft-deleted junctions still bill)
# """


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

#     # services (PROVISIONAL). strip: uses the `normal` column pending the IS_DANGEROUS branch.
#     other = fetch_all(OTHER_SERVICE_SQL, {"tid": tali_id})
#     strip = fetch_all(STRIP_SQL, {"tid": tali_id})
#     night = fetch_all(NIGHT_STOP_SQL, {"tid": tali_id})
#     diamound = fetch_all(DIAMOUND_SQL, {"tid": tali_id})
#     vehicle = fetch_all(VEHICLE_ENTER_SQL, {"tid": tali_id})

#     service_rows = calc.compute_service_rows(
#         other_service_prices=[r["price"] for r in other],
#         other_service_counts=[r["number_service"] for r in other],
#         strip_values=[r["normal"] for r in strip],
#         night_stop_prices=[r["price"] for r in night],
#         diamound_prices=[r["price"] for r in diamound],
#         vehicle_enter_prices=[r["price"] for r in vehicle],
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
#             "services": "VERIFIED byte-identical vs tally-549 golden (storage + strip + night + diamound + vehicle); other_service intentionally omitted (see invoice_calc)",
#             "strip": "using the `normal` column; IS_DANGEROUS='yes' branch (dangerous column) still unexercised",
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
       c."normal" AS normal, c."non_standard" AS non_standard, c."dangerous" AS dangerous
FROM "fa_tali_kala_strip" j
JOIN "fa_kala_strip" c ON c."id_kala_strip" = j."kala_strip_id"
WHERE j."tali_id" = :tid  -- NB: set_cal does NOT filter junction IS_DELETED (soft-deleted junctions still bill)
"""
NIGHT_STOP_SQL = """
SELECT c."price" AS price
FROM "fa_tali_kala_time_stop_vehicle" j
JOIN "fa_kala_time_stop_vehicle" c ON c."id_kala_time_stop_vehicle" = j."kala_time_stop_vehicle_id"
WHERE j."tali_id" = :tid  -- NB: set_cal does NOT filter junction IS_DELETED (soft-deleted junctions still bill)
"""
DIAMOUND_SQL = """
SELECT c."price_gher_edari" AS price
FROM "fa_tali_kala_diamound" j
JOIN "fa_kala_diamound" c ON c."id_kala_diamound" = j."kala_diamound_id"
WHERE j."tali_id" = :tid  -- NB: set_cal does NOT filter junction IS_DELETED (soft-deleted junctions still bill)
"""
VEHICLE_ENTER_SQL = """
SELECT c."price" AS price
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
        night_stop_prices=[r["price"] for r in night],
        diamound_prices=[r["price"] for r in diamound],
        vehicle_enter_prices=[r["price"] for r in vehicle],
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
            "services": "VERIFIED byte-identical vs tally-549 golden (storage + strip + night + diamound + vehicle); other_service intentionally omitted (see invoice_calc)",
            "strip": "column chosen per junction via pricing_type (normal|non_standard|dangerous); NULL -> normal, so prior data is unchanged",
            "tier_timing": "VERIFIED: first invoice -> l_time_rest=45 -> 60-day tier; a prior invoice forces 30-day",
        },
    }