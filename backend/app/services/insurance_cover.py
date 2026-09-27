"""How much insurance cover one tally has left, consuming shared ceilings in
tally registration order.

Business rule (confirmed): tallies that share an insurance use its ceiling in
the order they were registered. Earlier tallies draw first and only the real
shortfall of a later tally is charged, so no shortfall is ever charged twice.

An insurance is one aligned (NUMBER_BIMEH, SABT_SEFARESH_NUMBER) line pair,
parsed exactly as the tally warning banner does (insurance_check.py). Its
ceiling is the largest INSURED_VALUE recorded on any participating tally
(INSURED_VALUE is the policy value repeated on rows, never summed).

Details that follow from the rule:
  * Registration order is ID_TALI (identity, increasing with registration).
  * Only tallies marked IS_BIMEH = 'بله' take part; a tally without insurance
    neither draws on nor contributes to a ceiling.
  * An earlier tally consumes its full customs value (sum of active rows),
    whether or not it has been invoiced. Later tallies never affect it.
  * A tally with several insurances fills them in the order they are listed on
    its header.
  * An insured tally without any policy number uses only its own ceiling.

DB-free. The router passes plain fetch_all dicts.
"""
from dataclasses import dataclass
from decimal import Decimal
from typing import Optional

from app.services.insurance_check import normalize_number_text, parse_insurance_pairs
from app.services.storage_calc import ltr

INSURED = "بله"

# Inputs shared by the tally warning banner and the invoice, so both always
# see the same tallies and totals.
HEADERS_SQL = """
SELECT h."ID_TALI" AS id_tali, h."TALI_NUMBER" AS tali_number, h."IS_BIMEH" AS is_bimeh,
       h."NUMBER_BIMEH" AS number_bimeh, h."SABT_SEFARESH_NUMBER" AS sabt_sefaresh_number
FROM "FA_TALI_HEADER" h
WHERE h."IS_DELETED" = 'no'
"""
TOTALS_SQL = """
SELECT d."ID_HEADERS_TALI" AS id_tali,
       SUM(NVL(d."CUSTOMS_VALUE", 0)) AS customs_value,
       MAX(d."INSURED_VALUE") AS insured_ceiling
FROM "FA_TALI_DETAILES" d
WHERE d."IS_DELETED" = 'no'
GROUP BY d."ID_HEADERS_TALI"
"""


OWN = "__tally__"   # pseudo-policy of an insured tally without policy numbers


@dataclass(frozen=True)
class InsuranceCover:
    insured: bool
    customs: Decimal                 # the tally's total customs value
    ceiling: Optional[Decimal]       # sum of its insurances' ceilings; None when none is recorded
    used_before: Decimal             # drawn from those ceilings by earlier tallies
    cover: Decimal                   # cover available to this tally's goods (<= customs)
    policies: tuple = ()             # the tally's (بیمه‌نامه, ثبت سفارش) pairs, in listed order
    drawn_by: tuple = ()             # earlier tallies (ID_TALI) that drew on those ceilings

    @property
    def missing_ceiling(self) -> bool:
        return self.insured and self.ceiling is None

    @property
    def shortfall(self) -> Decimal:
        """The tally's real shortfall; zero without a known ceiling."""
        return max(Decimal(0), self.customs - self.cover) if self.ceiling is not None else Decimal(0)

    @property
    def policy_text(self) -> str:
        parts = []
        for bimeh, sabt in self.policies:
            if bimeh == OWN:
                parts.append("بدون شماره بیمه‌نامه")
            else:
                parts.append(f"بیمه‌نامه «{ltr(bimeh or '—')}»"
                             + (f" / ثبت سفارش «{ltr(sabt)}»" if sabt else ""))
        return "، ".join(parts)


def _dec(value) -> Decimal:
    return Decimal(0) if value is None else Decimal(str(value))


def _pairs(header) -> list:
    pairs = parse_insurance_pairs(header.get("number_bimeh"), header.get("sabt_sefaresh_number"))
    # No policy number: the tally's own ceiling, shared with nobody.
    return pairs or [(OWN, str(header["id_tali"]))]


def _is_insured(header) -> bool:
    return normalize_number_text(header.get("is_bimeh")) == INSURED


def insurance_cover(tally_id: int, headers: list[dict], totals: dict) -> InsuranceCover:
    """headers: active tally headers (id_tali, is_bimeh, number_bimeh, sabt_sefaresh_number).
    totals:  {id_tali: {"customs_value": sum, "insured_ceiling": max}} over active rows."""
    tally_id = int(tally_id)
    by_id = {int(h["id_tali"]): h for h in headers}
    target = by_id.get(tally_id)
    customs = _dec((totals.get(tally_id) or {}).get("customs_value"))
    if target is None or not _is_insured(target):
        return InsuranceCover(False, customs, None, Decimal(0), Decimal(0))

    insured = sorted((i for i, h in by_id.items() if _is_insured(h)))
    pairs_of = {i: _pairs(by_id[i]) for i in insured}

    # Ceiling per insurance: largest value recorded on any participating tally.
    ceilings: dict = {}
    for i in insured:
        value = (totals.get(i) or {}).get("insured_ceiling")
        if value is None:
            continue
        for pair in pairs_of[i]:
            ceilings[pair] = max(ceilings.get(pair, _dec(value)), _dec(value))

    target_pairs = pairs_of[tally_id]
    if not any(pair in ceilings for pair in target_pairs):
        return InsuranceCover(True, customs, None, Decimal(0), Decimal(0), tuple(target_pairs))

    # Earlier tallies draw first, each filling its insurances in listed order.
    remaining = dict(ceilings)
    drawn_by = []
    for i in insured:
        if i >= tally_id:
            break
        need = _dec((totals.get(i) or {}).get("customs_value"))
        for pair in pairs_of[i]:
            if need <= 0:
                break
            if pair in remaining:
                take = min(need, remaining[pair])
                remaining[pair] -= take
                need -= take
                if take > 0 and pair in target_pairs and i not in drawn_by:
                    drawn_by.append(i)

    ceiling = sum((ceilings[p] for p in target_pairs if p in ceilings), Decimal(0))
    available = sum((remaining[p] for p in target_pairs if p in remaining), Decimal(0))
    return InsuranceCover(True, customs, ceiling, ceiling - available, min(customs, available),
                          tuple(target_pairs), tuple(drawn_by))
