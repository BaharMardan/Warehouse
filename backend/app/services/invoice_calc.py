"""Invoice (صورتحساب) calculation port.

Pure, DB-free port of the original APEX ``set_process_details`` logic. Every function
takes already-fetched plain data and returns computed detail rows, so it is fully
unit-testable without Oracle. The router layer (invoice.py) fetches the inputs and
feeds them here.

Authoritative source: the real ``set_process_details``, reconciled against invoice
341's persisted rows (row 522 = 1 x 38,280 x 30 x 1000 = 1,148,400,000, matched to
the rial). See "Complete Invoice Specification" for the full derivation.

Two confirmed subtleties preserved verbatim:
  * NULL zarib_mahal -> NULL line price (the original has no NVL).
  * The tier MULTIPLIER is the fixed 30 / 60 / 90, NOT the real day count.

OPEN QUESTIONS (resolved only by the tally-547 golden case, spec section 4):
  * prior_invoice_count timing -> whether a first invoice is 30 (forced) or 60
    (hardcoded l_time_rest = 45). Encoded here as pick_tier(); flip when known.
  * exact service SELECTs / strip IS_DANGEROUS branch. compute_service_rows below
    implements the documented formulas but is marked PROVISIONAL until validated.
"""
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from typing import Optional

# --- charge labels (DESCRIPTION column on FA_SORA_HESAB_DETAILS) ---
# Exact strings, verified against the real set_process_details / set_cal
# (APEX app 112 page 57) and the tally-549 golden case. Storage is per-row:
#   'هزینه کد کالای ' || fa_kala_price.CODE
def storage_label(kala_code) -> str:
    return f"هزینه کد کالای {kala_code}"

SERVICE_LABELS = {
    "other_service": "هزینه کل سایر خدمات",
    "strip": "هزینه کل استریپ و استافینگ",
    "night_stop": "هزینه کل توقف شبانه",
    "diamound": "هزینه کل دیماند",
    "vehicle_enter": "هزینه کل حق ورودی (حق محوطه)",
}

# l_time_rest is HARDCODED to 45 inside set_process_details -> 60-day default tier
# whenever there is no prior invoice forcing the 30-day tier.
DEFAULT_TIME_REST = 45


@dataclass
class GoodsLine:
    """One FA_TALI_DETAILES row (the tally's goods line)."""
    code_groupe_kala: int          # -> joins fa_kala_price.id_kala_price (the PK, not id_kala)
    number_kala: Optional[int]
    weight: Optional[Decimal]
    zarib_mahal: Optional[Decimal]
    kala_code: Optional[str] = None  # fa_kala_price.CODE, drives the row label


@dataclass
class KalaPriceRate:
    """One fa_kala_price row (the storage rate for a goods group)."""
    id_kala_price: int
    price_30_day: Optional[Decimal]
    price_60_day: Optional[Decimal]
    price_90_day: Optional[Decimal]


@dataclass
class InvoiceDetailRow:
    """One computed FA_SORA_HESAB_DETAILS row (before manual TAKHFIF_* discounts)."""
    description: str
    number_kala: Optional[int]
    weight: Optional[Decimal]
    price: Optional[Decimal]


def to_decimal(v) -> Optional[Decimal]:
    """Coerce a value to Decimal, mirroring Oracle's implicit string->number in SUM().

    Service catalog prices are VARCHAR2; empty / non-numeric strings become None
    (contribute nothing), matching Oracle treating them as NULL in aggregation.
    """
    if v is None:
        return None
    if isinstance(v, Decimal):
        return v
    if isinstance(v, (int,)):
        return Decimal(v)
    if isinstance(v, float):
        return Decimal(str(v))
    s = str(v).strip()
    if s == "":
        return None
    try:
        return Decimal(s)
    except InvalidOperation:
        return None


def pick_tier(prior_invoice_count: int, l_time_rest: int = DEFAULT_TIME_REST) -> int:
    """Return the FIXED tier multiplier: 30, 60, or 90.

    Forced to 30 when a prior invoice exists; otherwise bucketed by l_time_rest
    (which set_process_details hardcodes to 45 -> the 60-day tier).
    """
    if prior_invoice_count > 0:
        return 30
    if l_time_rest <= 30:
        return 30
    if l_time_rest <= 60:
        return 60
    return 90


def _rate_for_tier(rate: KalaPriceRate, tier: int) -> Optional[Decimal]:
    return {
        30: rate.price_30_day,
        60: rate.price_60_day,
        90: rate.price_90_day,
    }[tier]


def compute_storage_rows(
    lines: list[GoodsLine],
    rates: dict[int, KalaPriceRate],
    prior_invoice_count: int,
    l_time_rest: int = DEFAULT_TIME_REST,
) -> tuple[list[InvoiceDetailRow], int]:
    """One storage detail row per goods line. Returns (rows, tier_used).

    line_price = zarib_mahal x (price_[tier] x tier) x weight
    NULL zarib (or missing rate / weight) -> NULL price row, preserved verbatim.
    """
    tier = pick_tier(prior_invoice_count, l_time_rest)
    mult = Decimal(tier)
    rows: list[InvoiceDetailRow] = []
    for ln in lines:
        price: Optional[Decimal] = None
        rate = rates.get(ln.code_groupe_kala)
        if rate is not None:
            base_rate = _rate_for_tier(rate, tier)
            # The quirk: any NULL input collapses the whole line price to NULL (no NVL).
            if ln.zarib_mahal is not None and base_rate is not None and ln.weight is not None:
                price = ln.zarib_mahal * (base_rate * mult) * ln.weight
        rows.append(InvoiceDetailRow(storage_label(ln.kala_code), ln.number_kala, ln.weight, price))
    return rows, tier


def _sum(values) -> Optional[Decimal]:
    """SUM() with Oracle-style NULL handling: None if nothing numeric, else the total."""
    total: Optional[Decimal] = None
    for v in values:
        d = to_decimal(v)
        if d is None:
            continue
        total = d if total is None else total + d
    return total


def compute_service_rows(
    *,
    other_service_prices=(),
    other_service_counts=(),
    strip_values=(),
    night_stop_prices=(),
    diamound_prices=(),
    vehicle_enter_prices=(),
) -> list[InvoiceDetailRow]:
    """The service detail rows, matching set_process_details verbatim (verified
    against the tally-549 golden case).

    Faithful-port quirks preserved:
      * NO other_service («سایر خدمات») row. set_cal computes SUM(price) x
        SUM(number_service) into the services grand total (P57_PRICE_ALL_SERVICESS)
        but never assigns the per-line item P57_PRICE_OTHER_SERVICE (source
        "Always Null"), so set_process_details' `if ... is not null` guard skips
        the insert. The persisted invoice has no such line. Looks like a latent
        bug — the rewrite decides whether to keep or fix it.
      * The other four rows are emitted UNCONDITIONALLY. Each price is
        NVL(SUM(...), 0), so an absent junction yields a 0 row (as seen on the
        strip line of invoice 341), not a suppressed one.
      * NUMBER_KALA is left NULL on service rows. (The source INSERT has a literal
        1, but every persisted service row in both golden invoices 341 and 361 has
        NULL — the data is authoritative, so we emit None.)
      * Junction soft-deletes are ignored (the caller must NOT filter IS_DELETED
        on the junctions — set_cal doesn't), so a soft-deleted junction still bills.

    strip:         SUM of the chosen normal|dangerous column (caller pre-selects)
    night_stop:    SUM(price)
    diamound:      SUM(priceـgher_edari)
    vehicle_enter: SUM(price)
    """
    # other_service is intentionally not emitted (see docstring); referenced to
    # keep the computable formula documented without producing a row.
    _ = (other_service_prices, other_service_counts)

    rows: list[InvoiceDetailRow] = []
    for key, values in (
        ("strip", strip_values),
        ("night_stop", night_stop_prices),
        ("diamound", diamound_prices),
        ("vehicle_enter", vehicle_enter_prices),
    ):
        total = _sum(values) or Decimal(0)     # NVL(SUM(...), 0)
        rows.append(InvoiceDetailRow(SERVICE_LABELS[key], None, None, total))

    return rows


# --- offline self-checks: reproduce the reconciled golden numbers -------------
if __name__ == "__main__":
    # Row 522 (invoice 341): prior invoice exists -> 30-day forced.
    # 1 x (38,280 x 30) x 1000 = 1,148,400,000
    lines = [GoodsLine(code_groupe_kala=7, number_kala=1, weight=Decimal(1000), zarib_mahal=Decimal(1))]
    rates = {7: KalaPriceRate(7, Decimal(38280), Decimal(10000), Decimal(20000))}
    rows, tier = compute_storage_rows(lines, rates, prior_invoice_count=1)
    assert tier == 30, tier
    assert rows[0].price == Decimal("1148400000"), rows[0].price

    # NULL zarib -> NULL price (the quirk).
    nz = [GoodsLine(7, 1, Decimal(1000), None)]
    rows2, _ = compute_storage_rows(nz, rates, prior_invoice_count=1)
    assert rows2[0].price is None

    # No prior invoice, hardcoded l_time_rest=45 -> 60-day tier.
    rows3, tier3 = compute_storage_rows(lines, rates, prior_invoice_count=0)
    assert tier3 == 60, tier3
    assert rows3[0].price == Decimal(1) * (Decimal(10000) * Decimal(60)) * Decimal(1000)

    # Services: exactly 4 rows (no other_service), unconditional, number_kala=1.
    svc = compute_service_rows(
        other_service_prices=["100", "200"], other_service_counts=["2", None],
        night_stop_prices=["910800"], diamound_prices=["2447500"],
    )
    assert [r.description for r in svc] == [
        SERVICE_LABELS[k] for k in ("strip", "night_stop", "diamound", "vehicle_enter")
    ], [r.description for r in svc]
    by = {r.description: r.price for r in svc}
    assert by[SERVICE_LABELS["night_stop"]] == Decimal("910800")
    assert by[SERVICE_LABELS["diamound"]] == Decimal("2447500")
    assert by[SERVICE_LABELS["strip"]] == Decimal(0)          # absent -> NVL 0 row
    assert by[SERVICE_LABELS["vehicle_enter"]] == Decimal(0)
    assert all(r.number_kala is None for r in svc)          # persisted data has NULL

    # Storage label uses fa_kala_price.CODE.
    lbl, _ = compute_storage_rows(
        [GoodsLine(7, 1, Decimal(1000), Decimal(1), kala_code="101")], rates, prior_invoice_count=1)
    assert lbl[0].description == "هزینه کد کالای 101", lbl[0].description

    print("invoice_calc self-checks passed")
