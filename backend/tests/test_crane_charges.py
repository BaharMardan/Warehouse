from decimal import Decimal
import pytest
from app.services.crane_charges import crane_rows
from app.services import receipt_invoice as ri

CATALOG = {code: {"title": code, "unloading": unload, "loading": load}
           for code, unload, load in [
               ("118", 38694065, 1), ("119", 3347231, 2),
               ("120", 56977332, 3), ("121", 5656689, 4),
               ("122", 5, 26536524), ("123", 6, 39527570)]}


def row(code="120", carrier="A"):
    return {"id": 1, "service_kind": "crane", "rate_code": code,
            "number_hamel": carrier, "number_service": 1, "pricing_type": "dangerous",
            "normal": 999, "dangerous": 888}


@pytest.mark.parametrize("code,weight,expected", [
    ("120", 20400, 6), ("120", 24400, 10), ("120", 15000, 0),
    ("120", 15001, 1), ("118", 10000, 0), ("118", 15400, 6),
    ("401", 20400, 6), ("201", 15400, 6),
])
def test_crane_ceil_without_empty_lift(code, weight, expected):
    result = crane_rows([row(code)], {"A": weight}, CATALOG)
    assert result[0]["number_service"] == 1
    assert not any(r["is_auto_empty"] for r in result)
    assert len(result) == (2 if expected else 1)
    extras = [r for r in result if r["is_auto_excess"]]
    assert sum(r["number_service"] for r in extras) == expected
    assert result[0]["normal"] == CATALOG[result[0]["rate_code"]]["unloading"]
    assert all(r["rate_code"] not in ("122", "123") for r in result)


def test_invoice_includes_only_full_container_and_excess():
    charges = ri.service_charges(other=[], strip=[row()], night=[], diamound=[], vehicle=[],
        container_weights={"A": Decimal(20400)}, excess_catalog={}, crane_catalog=CATALOG,
        freight_rate=0, carrier_count=0)
    crane = [c for c in charges if c.description.startswith(ri.SERVICE_LABELS["crane"])]
    assert [c.quantity for c in crane] == [1, 6]
    assert sum(c.price for c in crane) == 56977332 + 6 * 5656689


def test_each_container_has_its_own_rounding_without_empty_lift():
    result = crane_rows([row(carrier="A"), {**row(carrier="B"), "id": 2}],
                        {"A": 15100, "B": 15100}, CATALOG)
    assert sum(r["number_service"] for r in result if r["is_auto_excess"]) == 2
    assert not any(r["is_auto_empty"] for r in result)
    assert len({r["id"] for r in result}) == 4


@pytest.mark.parametrize("bad", [None, "", "abc", "-1", "NaN", "Infinity"])
def test_empty_loading_rate_is_not_required(bad):
    catalog = {**CATALOG, "123": {**CATALOG["123"], "loading": bad}}
    result = crane_rows([row()], {"A": 15000}, catalog)
    assert len(result) == 1
    assert result[0]["calculated_amount"] == 56977332


def test_non_crane_rows_are_unchanged():
    source = {**row(), "service_kind": "strip"}
    assert crane_rows([source], {}, {}) == [source]


@pytest.mark.parametrize("code,weight,expected", [("118", 15400, 58777451), ("120", 20400, 90917466)])
def test_crane_does_not_require_empty_container_catalog(code, weight, expected):
    catalog = {key: value for key, value in CATALOG.items() if key not in ("122", "123")}
    result = crane_rows([row(code)], {"A": weight}, catalog)
    assert sum(r["calculated_amount"] for r in result) == expected


@pytest.mark.parametrize("bad", [None, "", "abc", "-1", "NaN", "Infinity"])
def test_invalid_full_container_unloading_rate_is_rejected(bad):
    catalog = {**CATALOG, "120": {**CATALOG["120"], "unloading": bad}}
    with pytest.raises(ValueError):
        crane_rows([row()], {"A": 15000}, catalog)
