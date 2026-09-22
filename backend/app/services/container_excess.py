"""Derived excess-ton service rows for the four container tariff codes.

The excess row is keyed to its parent service row. Deriving it from current tally
weight prevents stale quantities and duplicate generated charges after edits.
"""
from decimal import Decimal


CONTAINERS = {
    "201": (Decimal("10000"), "202"),
    "401": (Decimal("15000"), "402"),
}
EXCESS_CODES = {"202", "402"}


def excess_tons(code: str | None, weight_kg: object) -> Decimal:
    rule = CONTAINERS.get(str(code or ""))
    if not rule or weight_kg is None:
        return Decimal(0)
    capacity, _ = rule
    return max((Decimal(str(weight_kg)) - capacity) / Decimal(1000), Decimal(0))


def derived_rows(rows: list[dict], weights: dict[str, Decimal], catalog: dict[str, dict]) -> list[dict]:
    generated = []
    parent_keys = {
        (row.get("service_kind"), row.get("number_hamel"), CONTAINERS[str(row.get("rate_code"))][1])
        for row in rows if str(row.get("rate_code")) in CONTAINERS
    }
    for row in rows:
        code = str(row.get("rate_code") or "")
        if code not in CONTAINERS:
            continue
        carrier = row.get("number_hamel")
        quantity = excess_tons(code, weights.get(carrier))
        if quantity <= 0:
            continue
        excess_code = CONTAINERS[code][1]
        tariff = catalog.get(excess_code)
        if not tariff:
            raise ValueError(f"Missing container excess tariff {excess_code}")
        generated.append({
            **row,
            "id": -int(row["id"]),
            "parent_service_id": row["id"],
            "is_auto_excess": True,
            "rate_id": tariff["id"],
            "rate_code": excess_code,
            "rate_title": tariff["title"],
            "number_service": quantity,
            "normal": tariff["normal"],
            "non_standard": tariff["non_standard"],
            "dangerous": tariff["dangerous"],
            "calculated_amount": quantity * Decimal(str(tariff[row.get("pricing_type") or "normal"])),
        })
    # An older manually entered excess line is superseded by the linked derived line.
    visible = [row for row in rows if not (
        str(row.get("rate_code")) in EXCESS_CODES and
        (row.get("service_kind"), row.get("number_hamel"), str(row.get("rate_code"))) in parent_keys
    )]
    return visible + generated


if __name__ == "__main__":
    assert excess_tons("201", 10000) == 0
    assert excess_tons("201", 15000) == 5
    assert excess_tons("401", 20000) == 5
    assert excess_tons("401", 15400) == Decimal("0.4")
    base = {"id": 7, "service_kind": "strip", "number_hamel": "A", "rate_code": "201", "pricing_type": "dangerous"}
    tariff = {"202": {"id": 42, "code": "202", "title": "20-foot excess", "normal": "10", "non_standard": "20", "dangerous": "30"}}
    result = derived_rows([base], {"A": Decimal(15000)}, tariff)
    assert len(result) == 2
    assert result[1]["parent_service_id"] == 7
    assert result[1]["number_service"] == 5
    assert result[1]["pricing_type"] == "dangerous"
    assert result[1]["calculated_amount"] == 150
    assert len(derived_rows([base], {"A": Decimal(10000)}, tariff)) == 1
    crane = {**base, "id": 8, "service_kind": "crane", "pricing_type": "non_standard"}
    crane_rows = derived_rows([crane], {"A": Decimal(15000)}, tariff)
    assert crane_rows[1]["parent_service_id"] == 8
    assert crane_rows[1]["service_kind"] == "crane"
    assert crane_rows[1]["pricing_type"] == "non_standard"
    assert crane_rows[1]["calculated_amount"] == 100
