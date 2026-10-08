from decimal import Decimal
from unittest.mock import MagicMock
import pytest
from fastapi import HTTPException
from app.services import row_pallets as rp, receipt_invoice as ri
from app.routers import tally_handoff as handoff, receipt_workflow as workflow


def rows():
    return [dict(id=1, pallets=3, used_pallets=1), dict(id=2, pallets=7, used_pallets=0)]


def entries(a=2, b=7):
    return [dict(tally_detail_id=1, pallets=a), dict(tally_detail_id=2, pallets=b)]


def test_explicit_counts_preserve_duplicate_carriers():
    source = [dict(r, number_hamel='SAME') for r in rows()]
    assert rp.validate_counts(source, entries(), expected=9, allocation=True) == {1: 2, 2: 7}


@pytest.mark.parametrize('values', [entries(0), entries(-1), entries(1.5), entries('NaN'), entries('Infinity'),
    entries(100001), entries(3), entries()[:1], entries() + entries()[:1],
    [dict(tally_detail_id=99, pallets=2), entries()[1]]])
def test_invalid_or_excess_allocations_are_rejected(values):
    with pytest.raises(ValueError):
        rp.validate_counts(rows(), values, expected=9, allocation=True)


def test_receipt_total_must_match_exactly():
    with pytest.raises(ValueError):
        rp.validate_counts(rows(), entries(1), expected=9, allocation=True)


def line(id, pallets, location, hs, rate):
    return dict(id=id, pallets=pallets, zarib_mahal=location, hscode=hs,
                goods_group=id, kala_code=str(id), storage_price=rate, number_hamel='SAME')


def test_mixed_locations_and_hs_codes_are_priced_per_row():
    result = ri.storage_rows('volumetric', [
        line(1, 2, 'انبارداری مسقف', '111', 100),
        line(2, 7, 'انبارداری محوطه', '222', 200)], 10, pallets=9)
    assert [r.price for r in result] == [Decimal(3600), Decimal(18480)]
    assert [r.quantity for r in result] == [2, 7]
    assert '111' in result[0].description and '222' in result[1].description
    assert all('SAME' in r.description for r in result)


@pytest.mark.parametrize('a,b,total', [(2, None, 9), (2, 7, 8), (0, 7, 7), (1.5, 7, 8.5)])
def test_invoice_rejects_missing_or_inconsistent_row_counts(a, b, total):
    with pytest.raises(ValueError):
        ri.storage_rows('volumetric', [line(1, a, 'انبارداری مسقف', '111', 100),
            line(2, b, 'انبارداری مسقف', '222', 100)], 10, pallets=total)


def test_finalized_tally_cannot_change_total(monkeypatch):
    conn = MagicMock()
    monkeypatch.setattr(handoff, 'get_connection', lambda: conn)
    monkeypatch.setattr(handoff, 'lock_tally', lambda *args: ('returned', 'volumetric', 10))
    monkeypatch.setattr(handoff, 'read_handoff', lambda *args: {
        'can_edit_pallets': True, 'receipt_checklists': [{'status': 'finalized'}], 'pallet_rows': rows()})
    with pytest.raises(HTTPException) as exc:
        handoff.save_row_pallets(1, handoff.PalletInput(lines=entries()), {'id': 1})
    assert exc.value.status_code == 422
    conn.commit.assert_not_called()


def test_invoiced_tally_cannot_edit_pallets(monkeypatch):
    conn = MagicMock()
    monkeypatch.setattr(handoff, 'get_connection', lambda: conn)
    monkeypatch.setattr(handoff, 'lock_tally', lambda *args: ('returned', 'volumetric', 10))
    monkeypatch.setattr(handoff, 'read_handoff', lambda *args: {'can_edit_pallets': False})
    with pytest.raises(HTTPException) as exc:
        handoff.save_row_pallets(1, handoff.PalletInput(lines=entries()), {'id': 1})
    assert exc.value.status_code == 409
    conn.commit.assert_not_called()


def test_preview_reserves_older_receipts_before_current(monkeypatch):
    siblings = [dict(id=i, tally_id=1, is_master='no', line_count=1) for i in (1, 2)]
    def sources(cur, receipt):
        return [dict(id=i, hscode='111', quantity=10, weight=10, baskol=0,
            quantity_share=0, weight_share=0, baskol_share=0,
            used_quantity=0, used_weight=0, used_baskol=0) for i in (1, 2)]
    monkeypatch.setattr(workflow, 'source_rows', sources)
    monkeypatch.setattr(workflow.db, 'rows', lambda *a: [dict(hscode='111', quantity=10, weight=10, baskol=0)])
    assert workflow.preview_source_ids(None, siblings[1], siblings) == {2}



def source(id, share=1):
    return dict(id=id, quantity=10, weight=100, baskol=0,
                quantity_share=share, weight_share=share, baskol_share=0)


def test_full_rows_reuse_tally_counts_without_reentry():
    stock = [dict(id=1, pallets=3), dict(id=2, pallets=7)]
    assert rp.automatic_counts(stock, [source(1), source(2)], 10) == {1: 3, 2: 7}


def test_single_partial_row_uses_existing_receipt_total():
    assert rp.automatic_counts([dict(id=1, pallets=20)], [source(1, '.3')], 5) == {1: 5}


def test_one_partial_after_full_rows_uses_remainder():
    assert rp.automatic_counts([dict(id=1, pallets=3), dict(id=2, pallets=20)],
                               [source(1), source(2, '.3')], 8) == {1: 3, 2: 5}


def test_multiple_partial_rows_are_not_guessed_from_weight():
    with pytest.raises(ValueError, match='بخشی از چند ردیف'):
        rp.automatic_counts([dict(id=1, pallets=20), dict(id=2, pallets=20)],
                            [source(1, '.5'), source(2, '.5')], 20)


def test_all_remaining_stock_is_unambiguous():
    assert rp.automatic_counts([dict(id=1, pallets=20, used_pallets=10),
                                dict(id=2, pallets=20, used_pallets=15)],
                               [source(1, '.5'), source(2, '.25')], 15) == {1: 10, 2: 5}


def test_auto_counts_still_enforce_receipt_total_and_capacity():
    with pytest.raises(ValueError):
        rp.automatic_counts([dict(id=1, pallets=20)], [source(1)], 5)
    with pytest.raises(ValueError):
        rp.automatic_counts([dict(id=1, pallets=20, used_pallets=19)], [source(1, '.3')], 5)


def test_automatic_allocation_is_saved_once_under_caller_transaction(monkeypatch):
    cur = MagicMock()
    current = dict(id=10, tally_id=1, pallet_quantity=10)
    stock = [dict(id=1, pallets=3), dict(id=2, pallets=7)]
    saved = []
    monkeypatch.setattr(rp, 'receipt_rows', lambda *args: stock)
    monkeypatch.setattr(rp, 'allocations', lambda *args: saved)
    assert rp.ensure_receipt_counts(cur, current, [source(1), source(2)]) == {1: 3, 2: 7}
    cur.executemany.assert_called_once()
    saved.extend([dict(tally_detail_id=1, pallets=3), dict(tally_detail_id=2, pallets=7)])
    assert rp.ensure_receipt_counts(cur, current, [source(1), source(2)]) == {1: 3, 2: 7}
    cur.executemany.assert_called_once()


def test_existing_explicit_allocation_is_preserved():
    stock = [dict(id=1, pallets=20), dict(id=2, pallets=20)]
    saved = [dict(tally_detail_id=1, pallets=7), dict(tally_detail_id=2, pallets=13)]
    assert rp.resolve_counts(stock, [source(1, '.5'), source(2, '.5')], 20, saved) == {1: 7, 2: 13}
