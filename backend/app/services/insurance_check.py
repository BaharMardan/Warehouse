"""Cross-tally insurance ceiling arithmetic for the tally module.

A tally header stores its insurance identities in two newline-separated
columns that are aligned line-by-line: NUMBER_BIMEH (شماره بیمه نامه) and
SABT_SEFARESH_NUMBER (شماره ثبت سفارش). The pair on one line identifies one
insurance, and several tallies may carry the same pair.

Per insurance, the ceiling is the policy's insured goods value
(INSURED_VALUE). That single number is repeated on the goods rows rather than
split across them, so it must NEVER be summed: the row values are collapsed
with MAX per header, and the largest recorded value across the pair's headers
is the ceiling. The usage is the sum of CUSTOMS_VALUE over the active goods
rows (IS_DELETED = 'no') of every active tally that carries the pair. When
usage exceeds the ceiling, the difference must be charged on the invoice, so
the check reports the overage and the UI warns the operator.

Deliberately free of database and router imports so it can be tested directly.
The router feeds it plain fetch_all dicts (lowercased keys) and per-header
value totals.
"""

from decimal import Decimal, InvalidOperation


# Persian (U+06F0..U+06F9) and Arabic-Indic (U+0660..U+0669) digits map to
# ASCII, mirroring normalizeDigits() in the frontend so legacy rows saved with
# Persian digits still match rows saved after the frontend normalization.
_DIGIT_TRANSLATION = {}
for _offset in range(10):
    _DIGIT_TRANSLATION[0x06F0 + _offset] = ord("0") + _offset
    _DIGIT_TRANSLATION[0x0660 + _offset] = ord("0") + _offset


def normalize_number_text(value) -> str:
    """Trim a stored number-like text and unify Persian/Arabic digits."""
    return str(value or "").translate(_DIGIT_TRANSLATION).strip()


def parse_insurance_pairs(number_bimeh, sabt_sefaresh_number) -> list[tuple[str, str]]:
    """Read one header's aligned (بیمه نامه, ثبت سفارش) pairs.

    The two columns are split on newlines and matched by line index; the
    shorter side is padded with empty strings so a legacy header whose
    SABT_SEFARESH_NUMBER is NULL still yields its policy numbers. Pairs with
    both sides empty are dropped, and a pair listed twice on one header counts
    once — repeating a line must not double that tally's values in the sums.
    """
    bimeh_lines = str(number_bimeh or "").splitlines()
    sabt_lines = str(sabt_sefaresh_number or "").splitlines()
    length = max(len(bimeh_lines), len(sabt_lines))

    pairs: list[tuple[str, str]] = []
    seen: set[tuple[str, str]] = set()
    for index in range(length):
        bimeh = normalize_number_text(bimeh_lines[index] if index < len(bimeh_lines) else "")
        sabt = normalize_number_text(sabt_lines[index] if index < len(sabt_lines) else "")
        pair = (bimeh, sabt)
        if pair == ("", "") or pair in seen:
            continue
        seen.add(pair)
        pairs.append(pair)
    return pairs


def _as_decimal(value) -> Decimal:
    if value is None:
        return Decimal(0)
    if isinstance(value, Decimal):
        return value
    try:
        return Decimal(str(value))
    except (InvalidOperation, ValueError):
        return Decimal(0)


def check_insurance_ceilings(header_id: int, headers, totals_by_header) -> list[dict]:
    """Report ceiling usage for every insurance pair of one tally header.

    headers          — active FA_TALI_HEADER rows as fetch_all dicts with the
                       keys id_tali, tali_number, number_bimeh and
                       sabt_sefaresh_number (soft-deleted headers already
                       filtered out by the caller's SQL).
    totals_by_header — {id_tali: {"customs_value": x, "insured_ceiling": y}}
                       where customs_value is summed over that header's active
                       goods rows and insured_ceiling is the MAX INSURED_VALUE
                       of those rows (None when no row records it).

    Returns one entry per pair, in the header's own order. ``insured_ceiling``
    is the largest policy value recorded across the pair's headers, ``overage``
    is the signed difference (usage - ceiling) or None when no ceiling is
    recorded anywhere, and ``is_over`` flags the entries the UI must warn
    about.
    """
    parsed = [
        (
            int(row["id_tali"]),
            row.get("tali_number"),
            parse_insurance_pairs(
                row.get("number_bimeh"), row.get("sabt_sefaresh_number")
            ),
        )
        for row in headers
    ]

    current_pairs: list[tuple[str, str]] = []
    for row_id, _tali_number, pairs in parsed:
        if row_id == header_id:
            current_pairs = pairs
            break

    results: list[dict] = []
    for pair in current_pairs:
        bimeh, sabt = pair
        total_customs = Decimal(0)
        insured_ceiling: Decimal | None = None
        tally_numbers: list[str] = []
        for row_id, tali_number, pairs in parsed:
            if pair not in pairs:
                continue
            totals = totals_by_header.get(row_id, {})
            total_customs += _as_decimal(totals.get("customs_value"))
            header_ceiling = totals.get("insured_ceiling")
            if header_ceiling is not None:
                value = _as_decimal(header_ceiling)
                insured_ceiling = (
                    value if insured_ceiling is None else max(insured_ceiling, value)
                )
            if tali_number is not None and str(tali_number).strip() != "":
                tally_numbers.append(str(tali_number))

        overage = None if insured_ceiling is None else total_customs - insured_ceiling
        results.append(
            {
                "number_bimeh": bimeh,
                "sabt_sefaresh_number": sabt,
                "total_customs_value": total_customs,
                "insured_ceiling": insured_ceiling,
                "overage": overage,
                "is_over": overage is not None and overage > 0,
                "tally_numbers": tally_numbers,
            }
        )
    return results
