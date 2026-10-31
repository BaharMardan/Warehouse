from decimal import Decimal
from app.services.non_customs_stock import build_rows
from app.services.stock_report import summarize, filter_rows


def entry(**changes):
    return {"tally_id": 1, "source_id": 10, "cargo": "weight", "weight": 20,
        "quantity": 2, "pallets": 1, "original_weight": 100, "original_quantity": 10,
        "original_pallets": 5, "original_baskol": 110, "original_customs_value": 1000,
        "is_insured": "yes", "insured_ceiling": 5000, "container_number": "A",
        "owner_id": 2, "owner_name": "Owner", "zarib_mahal": "مسقف", **changes}


def test_split_receipts_merge_without_double_counting_container_or_value():
    rows = build_rows([entry(), entry(weight=30, quantity=3)])
    assert len(rows) == 1
    assert rows[0]["weight"] == 50
    assert rows[0]["customs_value"] == 500
    assert rows[0]["baskol"] == 55
    assert rows[0]["containers"] == 1


def test_insurance_counts_once_per_tally_across_rows():
    rows = build_rows([entry(), entry(source_id=11)])
    totals, groups = summarize(rows, "owner")
    assert totals["insured_value"] == 5000
    assert groups[0]["weight"] == 40


def test_volumetric_value_uses_remaining_pallets():
    row = build_rows([entry(cargo="volumetric", pallets=2, weight=10)])[0]
    assert row["customs_value"] == 400
    assert row["remaining_ratio"] == Decimal("0.4")


def test_report_filters_use_shared_stock_rules():
    rows = build_rows([entry(), entry(source_id=11, owner_id=3)])
    assert len(filter_rows(rows, owner_id=2, location="covered")) == 1


def test_empty_inventory_has_zero_totals():
    totals, groups = summarize(build_rows([]))
    assert totals["weight"] == 0 and not groups
