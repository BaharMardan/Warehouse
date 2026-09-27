"""Validate explicit links to original tally rows, preserving partial allocations."""
from collections import defaultdict
from decimal import Decimal

ZERO = Decimal(0)
EPS = Decimal("0.000001")
FIELDS = ("quantity", "weight", "baskol")


def decimal(value):
    return ZERO if value is None else Decimal(str(value))


def allocate_sources(sources, selections, expected):
    """Return only keys and shares; descriptions, rates and amounts stay on tally."""
    by_id = {int(row["id"]): row for row in sources}
    totals = defaultdict(lambda: {key: ZERO for key in FIELDS})
    links = []
    seen = set()
    for selection in selections:
        sid = int(selection["tally_detail_id"])
        if sid in seen or sid not in by_id:
            raise ValueError("ردیف تالی نامعتبر یا تکراری است")
        seen.add(sid)
        source = by_id[sid]
        link = {"tally_detail_id": sid}
        positive = False
        for key in FIELDS:
            value = decimal(selection.get(key))
            base = decimal(source.get(key))
            available = base * (Decimal(1) - decimal(source.get("used_" + key)))
            if not value.is_finite() or value < 0 or value > available + EPS:
                raise ValueError("مقدار انتخاب‌شده از مانده ردیف تالی بیشتر است")
            link[key + "_share"] = value / base if base else ZERO
            totals[(source.get("hscode") or "").strip().upper()][key] += value
            positive = positive or value > 0
        if not positive:
            raise ValueError("ردیف انتخاب‌شده باید مقدار داشته باشد")
        links.append(link)
    wanted = defaultdict(lambda: {key: ZERO for key in FIELDS})
    for row in expected:
        for key in FIELDS:
            wanted[(row.get("hscode") or "").strip().upper()][key] += decimal(row.get(key))
    if not links or set(totals) != set(wanted):
        raise ValueError("ردیف‌های تالی باید تمام کالاهای قبض را پوشش دهند")
    for hs in wanted:
        for key in FIELDS:
            if abs(totals[hs][key] - wanted[hs][key]) > EPS:
                raise ValueError("جمع تعداد و وزن ردیف‌های انتخابی باید با قبض برابر باشد")
    return links


def automatic_selections(sources, expected):
    """Allocate remaining original amounts in tally-row order within each HS."""
    wanted = defaultdict(lambda: {key: ZERO for key in FIELDS})
    for row in expected:
        for key in FIELDS:
            wanted[(row.get("hscode") or "").strip().upper()][key] += decimal(row.get(key))
    selections = []
    for row in sorted(sources, key=lambda item: int(item["id"])):
        remaining = wanted.get((row.get("hscode") or "").strip().upper())
        if remaining is None:
            continue
        selection = {"tally_detail_id": row["id"]}
        for key in FIELDS:
            available = max(ZERO, decimal(row.get(key)) * (1 - decimal(row.get("used_" + key))))
            value = min(available, remaining[key])
            selection[key] = value
            remaining[key] -= value
        if any(selection[key] > 0 for key in FIELDS):
            selections.append(selection)
    # Validate coverage and capacity using the same rules as explicit links.
    allocate_sources(sources, selections, expected)
    return selections
