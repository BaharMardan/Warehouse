from decimal import Decimal
from itertools import product
from app.services.invoice_handling import LEGACY, selected_labels, merge_handling


def row(description, price, **extra):
    return dict(id_detail=1, row_kind="service", description=description,
                price=Decimal(price), discount=Decimal(0), quantity=None, weight=None,
                amount=None, calc_note=None, **extra)


def test_all_selected_combinations_and_decimal_totals():
    for unloading, loading in product((False, True), repeat=2):
        selections = [
            {"service_kind": "strip", "pricing_type": "unloading" if unloading else "normal"},
            {"service_kind": "stuffing", "pricing_type": "loading" if loading else "dangerous"},
        ]
        names = selected_labels(selections, "strip") + selected_labels(selections, "stuffing")
        source = [row(list(LEGACY)[0], "10.15"), row(list(LEGACY)[1], "20.20")]
        merged = merge_handling(source, selections)
        assert len(merged) == 1
        assert merged[0]["description"] == " و ".join(names)
        assert merged[0]["price"] == Decimal("30.35")
        assert source[0]["price"] == Decimal("10.15")


def test_new_snapshot_does_not_depend_on_current_selections():
    source = [row("تخلیه", "100"), row("بارگیری", "200"), row("بیمه", "10")]
    merged = merge_handling(source, [{"service_kind": "strip", "pricing_type": "normal"}])
    assert [r["description"] for r in merged] == ["تخلیه و بارگیری", "بیمه"]
    assert merged[0]["price"] == 300


def test_missing_selection_is_not_guessed_and_zero_is_not_named():
    old = row(list(LEGACY)[0], "100")
    assert merge_handling([old])[0]["description"] == old["description"]
    result = merge_handling([row("استریپ", "100"), row("بارگیری", "0")])
    assert result[0]["description"] == "استریپ"
    assert result[0]["price"] == 100
