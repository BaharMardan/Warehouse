"""Warehouse stock report rows and groupings. DB-free, so the rules are unit-tested.

Stock is what abandoned_stock.attach_remaining_goods leaves of each tally goods
row after invoiced receipts are taken off. This module only describes those rows:
where they are, who owns them, what they weigh and what they are worth.

Where the numbers come from:
  * goods value  - the row's «ارزش کالای گمرکی» (CUSTOMS_VALUE), scaled by the
                   share of the row still in stock.
  * insured value - the tally's «ارزش کالای بیمه‌شده» (INSURED_VALUE). It is the
                   policy's total, repeated on every row of the tally, so it is taken
                   once per tally (the largest recorded value) and never summed over
                   rows. A group or total adds it once for each tally it contains.
  * pallets      - the pallet count entered for each carrier (tally row). A partly
                   released row loses the pallets of its invoiced receipts.
"""
from collections import OrderedDict
from datetime import date, datetime
from decimal import Decimal
from typing import Optional

ZERO = Decimal(0)
UNKNOWN = "نامشخص"

# keyword (as stored in the location label) -> (key, label); same keywords as
# storage_calc.LOCATION_PERCENT, including the stored misspelling «هنگار».
LOCATIONS = (
    ("مسقف", "covered", "مسقف"),
    ("هانگار", "hangar", "هانگار"),
    ("هنگار", "hangar", "هانگار"),
    ("بارانداز", "dock", "بارانداز"),
    ("محوطه", "yard", "محوطه (روباز)"),
)
LOCATION_LABELS = {"covered": "مسقف", "hangar": "هانگار", "dock": "بارانداز",
                   "yard": "محوطه (روباز)", "unknown": UNKNOWN}

GROUP_BY = ("none", "hscode", "owner", "anbar", "location", "tally")

INSURED_FLAGS = ("بله", "yes")
VOLUMETRIC = ("volumetric", "yes")


def dec(value) -> Decimal:
    return ZERO if value is None else Decimal(str(value))


def location_of(zarib_mahal) -> tuple[str, str]:
    """(key, label) of a goods row's storage location; old numeric coefficients are unknown."""
    text = str(zarib_mahal or "").replace("ي", "ی").replace("ك", "ک")
    for keyword, key, label in LOCATIONS:
        if keyword in text:
            return key, label
    return "unknown", UNKNOWN


def normalize_hscode(value) -> str:
    return "".join(str(value or "").split()).upper()


def tally_insured_value(is_bimeh, recorded) -> Optional[Decimal]:
    """The tally's insured value: zero when it is not insured, None when it is insured
    but no value was recorded on any of its goods rows."""
    if str(is_bimeh or "").strip() not in INSURED_FLAGS:
        return ZERO
    return None if recorded is None else dec(recorded)


def _day(value) -> Optional[str]:
    if isinstance(value, datetime):
        return value.date().isoformat()
    if isinstance(value, date):
        return value.isoformat()
    return str(value)[:10] if value else None


def remaining_pallets(pallets, released, ratio) -> Optional[Decimal]:
    """Pallets of a row still in stock.

    Receipts that were invoiced carry their exact pallet counts; those are taken
    off. Without any (older receipts) the row's remaining ratio is applied.
    """
    if pallets is None:
        return None
    pallets, released = dec(pallets), dec(released)
    if released > 0:
        return max(ZERO, pallets - released)
    return pallets * ratio


def build_rows(tallies, details, insured) -> list[dict]:
    """One row per tally goods row still in stock.

    tallies: attach_remaining_goods(..., detailed=True) output, each with owner and
             insurance header fields; details: {detail_id: row metadata};
    insured: {tally_id: tally_insured_value(...)}.
    """
    rows = []
    for tally in tallies:
        for goods in tally["goods"]:
            meta = details.get(goods["detail_id"], {})
            ratio = dec(goods.get("remaining_ratio"))
            location_key, location_label = location_of(meta.get("zarib_mahal"))
            has_container = bool(meta.get("container_type") or meta.get("container_number"))
            rows.append({
                "tally_id": tally["id"],
                "tally_number": tally.get("tally_number"),
                "detail_id": goods["detail_id"],
                "unloaded_at": _day(tally.get("unloaded_at")),
                "cargo_type": tally.get("cargo_type"),
                "owner_id": tally.get("owner_id"),
                "owner_name": tally.get("owner_name") or UNKNOWN,
                "hscode": (goods.get("hscode") or "").strip() or None,
                "description": goods.get("description"),
                "package_type": meta.get("package_type"),
                "anbar_id": meta.get("anbar_id"),
                "anbar_name": meta.get("anbar_name") or UNKNOWN,
                "tagh_name": meta.get("tagh_name"),
                "location": location_key,
                "location_label": location_label,
                "carrier": meta.get("number_hamel"),
                "container_type": meta.get("container_type"),
                "container_number": meta.get("container_number"),
                "containers": 1 if has_container else 0,
                "remaining_ratio": ratio,
                "weight": dec(goods.get("remaining_weight")),
                "baskol": dec(goods.get("remaining_baskol")),
                "quantity": dec(goods.get("remaining_quantity")),
                "pallets": remaining_pallets(meta.get("pallets"), meta.get("released_pallets"), ratio),
                "customs_value": dec(goods.get("customs_value")) * ratio,
                "insured_value": insured.get(tally["id"]),
                "is_insured": tally.get("is_bimeh"),
                "insurance_company": tally.get("insurance_company"),
                "policy_numbers": tally.get("policy_numbers"),
                "insurance_expiry": _day(meta.get("insurance_expiry_date")),
            })
    return rows


def filter_rows(rows, *, hscode=None, owner_id=None, anbar_id=None, location=None,
                unloaded_from=None, unloaded_to=None) -> list[dict]:
    wanted_hs = normalize_hscode(hscode)
    result = []
    for row in rows:
        if wanted_hs and wanted_hs not in normalize_hscode(row["hscode"]):
            continue
        if owner_id is not None and row["owner_id"] != owner_id:
            continue
        if anbar_id is not None and row["anbar_id"] != anbar_id:
            continue
        if location and row["location"] != location:
            continue
        day = row["unloaded_at"]
        if unloaded_from and (day is None or day < unloaded_from):
            continue
        if unloaded_to and (day is None or day > unloaded_to):
            continue
        result.append(row)
    return result


def group_key(row, group_by) -> tuple:
    """(key, label) of the group a row belongs to."""
    if group_by == "hscode":
        code = normalize_hscode(row["hscode"])
        return code or "-", code or "بدون HS Code"
    if group_by == "owner":
        return row["owner_id"] or 0, row["owner_name"]
    if group_by == "anbar":
        return row["anbar_id"] or 0, row["anbar_name"]
    if group_by == "location":
        return row["location"], row["location_label"]
    if group_by == "tally":
        return row["tally_id"], str(row["tally_number"] or row["tally_id"])
    raise ValueError(f"unknown grouping {group_by!r}")


_SUMS = ("weight", "baskol", "quantity", "pallets", "containers", "customs_value")
_LISTS = (("descriptions", "description"), ("package_types", "package_type"),
          ("owners", "owner_name"), ("locations", "location_label"),
          ("anbars", "anbar_name"), ("hscodes", "hscode"))


def _blank() -> dict:
    block = {name: ZERO for name in _SUMS}
    block.update(rows=0, tallies=set(), insured_value=ZERO,
                 insurance_unknown=set(), pallets_missing=set())
    block.update({name: OrderedDict() for name, _ in _LISTS})
    return block


def _add(block, row):
    block["rows"] += 1
    for name in _SUMS:
        value = row[name]
        if value is not None:
            block[name] += value
    # The insured value belongs to the tally, so it counts once per tally.
    if row["tally_id"] not in block["tallies"]:
        if row["insured_value"] is None:
            block["insurance_unknown"].add(row["tally_id"])
        else:
            block["insured_value"] += row["insured_value"]
    block["tallies"].add(row["tally_id"])
    if row["pallets"] is None and row["cargo_type"] in VOLUMETRIC:
        block["pallets_missing"].add(row["tally_id"])
    for name, field in _LISTS:
        if row[field]:
            block[name][str(row[field]).strip()] = None


_SETS = ("tallies", "insurance_unknown", "pallets_missing")


def _finish(block) -> dict:
    result = {key: value for key, value in block.items()
              if key not in _SETS and key not in dict(_LISTS)}
    for name in _SETS:
        result[name] = len(block[name])
    for name, _ in _LISTS:
        result[name] = list(block[name])
    return result


def summarize(rows, group_by="hscode") -> tuple[dict, list[dict]]:
    """(totals, groups). groups is empty for group_by == 'none'."""
    if group_by not in GROUP_BY:
        raise ValueError(f"unknown grouping {group_by!r}")
    total = _blank()
    groups: "OrderedDict[object, dict]" = OrderedDict()
    for row in rows:
        _add(total, row)
        if group_by == "none":
            continue
        key, label = group_key(row, group_by)
        if key not in groups:
            groups[key] = _blank()
            groups[key].update(key=key, label=label)
        _add(groups[key], row)
    finished = [_finish(g) for g in groups.values()]
    finished.sort(key=lambda g: (-g["customs_value"], str(g["label"])))
    return _finish(total), finished
