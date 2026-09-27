"""Original-row allocation and atomic receipt invoice behavior."""
from decimal import Decimal
from unittest.mock import MagicMock
import pytest
from fastapi import HTTPException
from app.services.receipt_sources import allocate_sources
from app.services import receipt_db
from app.routers import receipt_workflow as api
from app.routers import invoice


def source(sid=1, group="A", **changes):
    return {"id": sid, "hscode": group, "quantity": 10, "weight": 100, "baskol": 90,
            "used_quantity": 0, "used_weight": 0, "used_baskol": 0, **changes}


def selection(sid=1, **changes):
    return {"tally_detail_id": sid, "quantity": 10, "weight": 100, "baskol": 90, **changes}


def expected(**changes):
    return [{"hscode": "A", "quantity": 10, "weight": 100, "baskol": 90, **changes}]


def test_partial_receipt_links_keep_original_identity_and_shares_only():
    result = allocate_sources([source()], [selection(quantity=4, weight=40, baskol=36)],
                              expected(quantity=4, weight=40, baskol=36))
    assert result == [{"tally_detail_id": 1, "quantity_share": Decimal(".4"),
                      "weight_share": Decimal(".4"), "baskol_share": Decimal(".4")}]


def test_same_hs_code_different_original_rows_remain_separate():
    result = allocate_sources([source(), source(2)], [selection(), selection(2)],
                              expected(quantity=20, weight=200, baskol=180))
    assert [row["tally_detail_id"] for row in result] == [1, 2]


@pytest.mark.parametrize("selections, sources, totals", [
    ([selection(), selection()], [source()], expected(quantity=20, weight=200, baskol=180)),
    ([selection(99)], [source()], expected()),
    ([selection()], [source(used_quantity=Decimal(".5"))], expected()),
    ([selection(weight=99)], [source()], expected()),
    ([selection(weight=-1)], [source()], expected(weight=-1)),
    ([selection(weight=1)], [source(weight=0)], expected(weight=1)),
    ([selection()], [source(group="B")], expected()),
    ([], [source()], expected()),
])
def test_invalid_or_overlapping_sources_are_rejected(selections, sources, totals):
    with pytest.raises(ValueError):
        allocate_sources(sources, selections, totals)




def test_automatic_sources_use_tally_order_and_available_amounts():
    from app.services.receipt_sources import automatic_selections
    rows = [source(2), source(1, used_quantity=Decimal(".5"),
                                used_weight=Decimal(".5"), used_baskol=Decimal(".5"))]
    result = automatic_selections(rows, expected(quantity=8, weight=80, baskol=72))
    assert result == [selection(1, quantity=5, weight=50, baskol=45),
                      selection(2, quantity=3, weight=30, baskol=27)]


def test_automatic_sources_do_not_take_other_hs_or_overallocate():
    from app.services.receipt_sources import automatic_selections
    result = automatic_selections([source(1, group="B"), source(2)], expected())
    assert result == [selection(2)]
    with pytest.raises(ValueError):
        automatic_selections([source()], expected(quantity=11))
