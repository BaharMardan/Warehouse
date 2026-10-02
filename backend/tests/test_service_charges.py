"""Shared service charges (pool snapshot) after removing the APEX port.

The expected values were produced by the pre-refactor code (invoice_calc.py +
invoice.compute_from_tally) on these exact inputs, so this pins that the move
into receipt_invoice.py changed no amount, label, quantity or order. The first
case is the old module's own self-check.
"""
from decimal import Decimal

import pytest

from app.services import receipt_invoice as ri
CASES = {
 "invoice_calc_selfcheck": dict(
    other=[{"price": "100", "number_service": "2"}, {"price": "200", "number_service": None}],
    strip=[], night=[{"price": "910800", "number_service": "3"}],
    diamound=[{"price": "2447500", "number_service": None}], vehicle=[],
    weights=[], carriers=0, freight=0),
 "strip_stuffing_crane_transport": dict(
    other=[],
    strip=[
     {"id": 1, "service_kind": "strip", "pricing_type": "non_standard", "number_hamel": "A", "number_service": 2,
      "rate_code": "301", "rate_title": "t", "normal": "100", "non_standard": "150", "dangerous": "300",
      "unloading_amount": None, "loading_amount": None},
     {"id": 2, "service_kind": "strip", "pricing_type": "unloading", "number_hamel": "A", "number_service": 5,
      "rate_code": "301", "rate_title": "t", "normal": "100", "non_standard": "150", "dangerous": "300",
      "unloading_amount": Decimal("3940623.5"), "loading_amount": None},
     {"id": 3, "service_kind": "stuffing", "pricing_type": "loading", "number_hamel": "B", "number_service": 4,
      "rate_code": "302", "rate_title": "t", "normal": "1", "non_standard": "1", "dangerous": "1",
      "unloading_amount": None, "loading_amount": Decimal("123.25")},
     {"id": 4, "service_kind": "crane", "pricing_type": None, "number_hamel": "A", "number_service": 0,
      "rate_code": "201", "rate_title": "جرثقیل 20 فوت", "normal": "750000", "non_standard": "1", "dangerous": "1",
      "unloading_amount": None, "loading_amount": None}],
    night=[], diamound=[], vehicle=[{"price": "935000", "number_service": 1}],
    weights=[], carriers=2, freight=Decimal("1500000.0000")),
 "container_excess": dict(
    other=[], night=[], diamound=[], vehicle=[],
    strip=[{"id": 7, "service_kind": "strip", "pricing_type": "dangerous", "number_hamel": "A", "number_service": 1,
            "rate_code": "201", "rate_title": "20 فوت", "normal": "1000", "non_standard": "2000", "dangerous": "3000",
            "unloading_amount": None, "loading_amount": None}],
    weights=[{"number_hamel": "A", "weight_kg": 15400}], carriers=0, freight=0),
}
CATALOG = [{"id": 42, "code": c, "title": "excess", "normal": "10", "non_standard": "20", "dangerous": "30"} for c in ("202", "402")]

L = ri.SERVICE_LABELS
EXPECTED = {
    "invoice_calc_selfcheck": [
        ("سایر خدمات — سایر خدمات — تعداد 2", 2, "200"),
        ("سایر خدمات — سایر خدمات — تعداد 1", 1, "200"), (L["strip"], None, "0"), (L["stuffing"], None, "0"),
        (L["night_stop"], 3, "2732400"), (L["diamound"], 1, "2447500"), (L["vehicle_enter"], None, "0")],
    "strip_stuffing_crane_transport": [
        (L["strip"], 3, "3940923.5"), (L["stuffing"], 1, "123.25"), (L["night_stop"], None, "0"),
        (L["diamound"], None, "0"), (L["vehicle_enter"], 1, "935000"),
        (f'{L["crane"]} — full', 1, "100"),
        (L["transportation"], 2, "3000000")],
    "container_excess": [
        (L["strip"], 6, "3162"), (L["stuffing"], None, "0"), (L["night_stop"], None, "0"),
        (L["diamound"], None, "0"), (L["vehicle_enter"], None, "0")],
}


def run(case, strict=True):
    return ri.service_charges(
        other=case["other"], strip=case["strip"], night=case["night"], diamound=case["diamound"],
        vehicle=case["vehicle"],
        container_weights={w["number_hamel"]: Decimal(str(w["weight_kg"])) for w in case["weights"]},
        excess_catalog={c["code"]: c for c in CATALOG},
        crane_catalog={"118": {"title": "full", "unloading": 100, "loading": 200},
                       "122": {"title": "empty", "unloading": 25, "loading": 50}},
        freight_rate=case["freight"], carrier_count=case["carriers"], strict=strict)


@pytest.mark.parametrize("name", list(CASES))
def test_service_charges_match_the_pre_refactor_output(name):
    got = [(c.description, None if c.quantity is None else Decimal(str(c.quantity)), c.price)
           for c in run(CASES[name])]
    want = [(d, None if q is None else Decimal(q), Decimal(p)) for d, q, p in EXPECTED[name]]
    assert got == want


@pytest.mark.parametrize("bad", [None, "", "abc", "-5"])
def test_strict_snapshot_refuses_incomplete_tariffs(bad):
    case = {**CASES["invoice_calc_selfcheck"], "other": [{"price": bad, "number_service": 1}]}
    with pytest.raises(ri.ServiceTariffError):
        run(case)
    # non-strict: unreadable text counts as no charge, a number is taken as is
    assert run(case, strict=False)[0].price == (ri.to_decimal(bad) or 0)


def test_no_storage_or_tier_logic_remains():
    import importlib.util
    import app.services.receipt_invoice as module
    assert importlib.util.find_spec("app.services.invoice_calc") is None
    source = open(module.__file__, encoding="utf-8").read()
    for retired in ("price_30_day", "price_60_day", "price_90_day", "pick_tier", "tier_used"):
        assert retired not in source


def test_other_services_keep_each_name_quantity_and_amount_in_invoice():
    case = {**CASES["invoice_calc_selfcheck"], "other": [
        {"title": "برچسب", "number_service": 5, "price": "100"},
        {"title": "پالتیزاسیون", "number_service": 10, "price": "200"},
    ]}
    charges = run(case)[:2]
    assert [(c.description, c.quantity, c.price) for c in charges] == [
        ("سایر خدمات — برچسب — تعداد 5", 5, Decimal(500)),
        ("سایر خدمات — پالتیزاسیون — تعداد 10", 10, Decimal(2000)),
    ]
    # Match the persisted pool contract, which stores description and total.
    allocated = [{"line_no": i + 1, "description": c.description,
                  "total": c.price, "amount": c.price} for i, c in enumerate(charges)]
    rows = ri.service_rows(allocated, Decimal(1))
    assert [r.description for r in rows] == [c.description for c in charges]
    assert [r.price for r in rows] == [Decimal(500), Decimal(2000)]
    assert all(ri.service_rank(r.description) == ri.service_rank(L["other_service"]) for r in rows)


def test_other_service_fractional_quantity_is_not_truncated():
    case = {**CASES["invoice_calc_selfcheck"], "other": [
        {"title": "خدمت", "number_service": "2.5", "price": "100"},
    ]}
    charge = run(case)[0]
    assert charge.quantity == Decimal("2.5")
    assert charge.price == Decimal(250)
    assert "تعداد 2.5" in charge.description
