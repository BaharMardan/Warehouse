from datetime import datetime
from decimal import Decimal

import pytest
from fastapi import HTTPException

from app.routers import reports as api
from app.services import stock_report as sr
from app.services.abandoned_stock import attach_remaining_goods


def tally(tid=1, owner="الف", **extra):
    return {"id": tid, "tally_number": str(1400 + tid), "unloaded_at": datetime(2026, 5, 1),
            "owner_id": tid, "owner_name": owner, "cargo_type": "weight",
            "is_bimeh": "خیر", "insurance_company": None, "policy_numbers": None, **extra}


def goods(tid=1, detail=10, hs="123", weight=1000, value=1000, receipt=None, **extra):
    return {"tally_id": tid, "detail_id": detail, "receipt_id": receipt,
            "receipt_number": str(receipt) if receipt else None, "hscode": hs,
            "description": f"کالای {hs}", "remaining_weight": weight, "customs_value": value,
            "quantity": 10, "baskol": weight, **extra}


def meta(**extra):
    return {"package_type": "کیسه", "anbar_id": 1, "anbar_name": "8", "tagh_name": "1A",
            "zarib_mahal": "انبارداری مسقف", "pallets": None, "released_pallets": 0,
            "container_type": None, "container_number": None, "number_hamel": "12-الف-345-67",
            **extra}


def rows_for(tallies, goods_rows, details, insured=None):
    stock = attach_remaining_goods(tallies, goods_rows, detailed=True)
    return stock, sr.build_rows(stock, details, insured or {t["id"]: Decimal(0) for t in tallies})


@pytest.mark.parametrize("label,key", [
    ("انبارداری مسقف", "covered"), ("انبارداری هانگار", "hangar"), ("انبارداری هنگار", "hangar"),
    ("انبارداری بارانداز", "dock"), ("انبارداری محوطه", "yard"),
    ("1.5", "unknown"), (None, "unknown"), ("", "unknown"),
])
def test_location_label_maps_to_the_storage_place(label, key):
    assert sr.location_of(label)[0] == key


def test_open_yard_is_labelled_for_the_warehouse_staff():
    assert sr.location_of("انبارداری محوطه")[1] == "محوطه (روباز)"


def test_hs_codes_with_stray_spaces_or_case_group_together():
    assert sr.normalize_hscode(" 4011 2010 ") == "40112010"


def test_untouched_goods_count_in_full_with_the_customs_value_as_their_value():
    _, rows = rows_for([tally()], [goods()], {10: meta(pallets=4, container_type="کانتینر ۲۰ فوت")})

    row = rows[0]
    assert (row["weight"], row["baskol"], row["quantity"]) == (1000, 1000, 10)
    assert row["pallets"] == 4 and row["containers"] == 1
    assert row["customs_value"] == 1000
    assert "goods_value" not in row
    assert row["location_label"] == "مسقف" and row["anbar_name"] == "8"


def billed(share="0.4", **extra):
    return {**goods(receipt=20, **extra), "invoiced": 1, "source_detail_id": 10,
            "weight_share": share, "quantity_share": share, "baskol_share": share}


def test_a_partly_invoiced_row_keeps_only_its_remaining_share_of_the_customs_value():
    _, rows = rows_for([tally()], [billed()], {10: meta()})

    assert rows[0]["weight"] == 600 and rows[0]["quantity"] == 6
    assert rows[0]["customs_value"] == 600


def test_a_fully_invoiced_row_is_not_in_stock():
    _, rows = rows_for([tally()], [billed(share="1")], {10: meta()})

    assert rows == []


def test_rows_without_any_measure_count_in_full():
    bare = goods(weight=0, value=0, quantity=None, baskol=None)
    _, rows = rows_for([tally()], [{**bare, "quantity": 0}], {10: meta()})

    assert rows[0]["remaining_ratio"] == 1


def test_pallets_of_invoiced_receipts_are_taken_off_exactly():
    _, rows = rows_for([tally()], [billed()], {10: meta(pallets=10, released_pallets=3)})

    assert rows[0]["pallets"] == 7        # not 10 x 0.6


def test_pallets_fall_back_to_the_remaining_share_when_no_exact_count_exists():
    _, rows = rows_for([tally()], [billed()], {10: meta(pallets=10)})

    assert rows[0]["pallets"] == 6


@pytest.mark.parametrize("is_bimeh,recorded,expected", [
    ("بله", 500, 500), ("بله", None, None), ("خیر", 500, 0), (None, 500, 0), ("yes", 7, 7),
    (" بله ", 0, 0),
])
def test_tally_insured_value_comes_from_the_recorded_value_only_for_insured_tallies(is_bimeh, recorded, expected):
    assert sr.tally_insured_value(is_bimeh, recorded) == expected


def test_insured_value_is_counted_once_per_tally_not_once_per_row():
    tallies = [tally(1, is_bimeh="بله"), tally(2, is_bimeh="بله")]
    _, rows = rows_for(tallies,
                       [goods(1, 10), goods(1, 11), goods(1, 12), goods(2, 13)],
                       {10: meta(), 11: meta(), 12: meta(), 13: meta()},
                       {1: Decimal(900), 2: Decimal(400)})

    totals, _ = sr.summarize(rows, "none")
    assert totals["insured_value"] == 1300
    assert totals["rows"] == 4 and totals["tallies"] == 2


def test_a_group_counts_the_insured_value_of_each_tally_it_contains_once():
    tallies = [tally(1, is_bimeh="بله"), tally(2, is_bimeh="بله")]
    _, rows = rows_for(tallies, [goods(1, 10, hs="1"), goods(1, 11, hs="1"), goods(2, 12, hs="2")],
                       {10: meta(), 11: meta(), 12: meta()}, {1: Decimal(900), 2: Decimal(400)})

    _, groups = sr.summarize(rows, "hscode")

    assert {g["key"]: g["insured_value"] for g in groups} == {"1": 900, "2": 400}


def test_an_insured_tally_without_a_recorded_value_is_reported_as_unknown_not_zero():
    _, rows = rows_for([tally(is_bimeh="بله")], [goods(1, 10), goods(1, 11)],
                       {10: meta(), 11: meta()}, {1: None})

    totals, _ = sr.summarize(rows, "none")
    assert totals["insured_value"] == 0 and totals["insurance_unknown"] == 1


def test_groups_by_hs_code_sum_every_row_and_collect_descriptions_and_owners():
    tallies = [tally(1, "الف"), tally(2, "ب")]
    _, rows = rows_for(tallies,
                       [goods(1, 10, hs="111", weight=100), goods(2, 11, hs="111", weight=50),
                        goods(2, 12, hs="222", weight=7)],
                       {10: meta(), 11: meta(package_type="رول"), 12: meta(anbar_id=2, anbar_name="9")})

    totals, groups = sr.summarize(rows, "hscode")

    first = next(g for g in groups if g["key"] == "111")
    assert (first["rows"], first["tallies"], first["weight"]) == (2, 2, 150)
    assert first["owners"] == ["الف", "ب"]
    assert first["package_types"] == ["کیسه", "رول"]
    assert totals["weight"] == 157 and totals["rows"] == 3 and totals["tallies"] == 2


@pytest.mark.parametrize("group_by,expected_groups", [
    ("owner", 2), ("anbar", 2), ("location", 1), ("tally", 2), ("hscode", 2),
])
def test_every_grouping_partitions_the_rows(group_by, expected_groups):
    tallies = [tally(1, "الف"), tally(2, "ب")]
    _, rows = rows_for(tallies, [goods(1, 10, hs="111"), goods(2, 11, hs="222")],
                       {10: meta(), 11: meta(anbar_id=2, anbar_name="9")})

    totals, groups = sr.summarize(rows, group_by)

    assert len(groups) == expected_groups
    assert sum(g["weight"] for g in groups) == totals["weight"]


def test_no_grouping_returns_totals_only_and_unknown_grouping_is_rejected():
    _, rows = rows_for([tally()], [goods()], {10: meta()})

    assert sr.summarize(rows, "none")[1] == []
    with pytest.raises(ValueError):
        sr.summarize(rows, "weird")


def test_filters_narrow_the_rows():
    tallies = [tally(1, "الف"), tally(2, "ب", unloaded_at=datetime(2026, 6, 1))]
    _, rows = rows_for(tallies, [goods(1, 10, hs="4011"), goods(2, 11, hs="7201")],
                       {10: meta(zarib_mahal="انبارداری محوطه"), 11: meta(anbar_id=2)})

    assert [r["detail_id"] for r in sr.filter_rows(rows, hscode="40")] == [10]
    assert [r["detail_id"] for r in sr.filter_rows(rows, owner_id=2)] == [11]
    assert [r["detail_id"] for r in sr.filter_rows(rows, anbar_id=2)] == [11]
    assert [r["detail_id"] for r in sr.filter_rows(rows, location="yard")] == [10]
    assert [r["detail_id"] for r in sr.filter_rows(rows, unloaded_from="2026-05-15")] == [11]
    assert [r["detail_id"] for r in sr.filter_rows(rows, unloaded_to="2026-05-15")] == [10]
    assert len(sr.filter_rows(rows)) == 2


def test_total_pallets_are_the_sum_of_the_per_carrier_counts():
    volumetric = tally(cargo_type="volumetric")
    _, rows = rows_for([volumetric], [goods(1, 10), goods(1, 11)],
                       {10: meta(pallets=10), 11: meta(pallets=20)})

    totals, _ = sr.summarize(rows, "none")
    assert totals["pallets"] == 30 and totals["pallets_missing"] == 0


def test_volumetric_tallies_with_carriers_missing_their_pallet_count_are_flagged():
    volumetric = tally(cargo_type="volumetric")
    _, rows = rows_for([volumetric, tally(2)], [goods(1, 10), goods(1, 11), goods(2, 12)],
                       {10: meta(pallets=10), 11: meta(), 12: meta()})

    totals, _ = sr.summarize(rows, "none")
    assert totals["pallets"] == 10
    assert totals["pallets_missing"] == 1     # the weight tally needs no pallets


def test_stock_query_uses_the_same_still_in_warehouse_rule_as_the_abandoned_report():
    from app.routers import abandoned

    assert abandoned.STILL_IN_WAREHOUSE_SQL in api.STOCK_TALLIES_SQL
    assert abandoned.STILL_IN_WAREHOUSE_SQL in abandoned.AGING_SQL
    assert 'h."IS_DELETED" = \'no\'' in api.STOCK_TALLIES_SQL
    assert 'd."IS_DELETED" = \'no\'' in api.STOCK_DETAILS_SQL
    assert '"FA_RECEIPT_PALLETS"' in api.STOCK_DETAILS_SQL


def test_stock_endpoint_assembles_rows_groups_and_facets(monkeypatch):
    from unittest.mock import MagicMock

    conn = MagicMock()
    conn.__enter__.return_value = conn
    monkeypatch.setattr(api, "get_connection", lambda: conn)
    tallies = [tally(1, "الف", is_bimeh="بله"), tally(2, "ب", is_bimeh="خیر")]
    answers = {
        api.STOCK_TALLIES_SQL: tallies,
        api.goods_sql(api.STOCK_TALLIES_SQL): [goods(1, 10, hs="111"), goods(1, 11, hs="111"),
                                               goods(2, 12, hs="222")],
        api.STOCK_DETAILS_SQL: [{"detail_id": 10, **meta()}, {"detail_id": 11, **meta()},
                                {"detail_id": 12, **meta(anbar_id=2, anbar_name="9")}],
        api.TOTALS_SQL: [{"id_tali": 1, "customs_value": 2000, "insured_ceiling": 250},
                         {"id_tali": 2, "customs_value": 1000, "insured_ceiling": 999}],
    }
    monkeypatch.setattr(api.db, "rows", lambda cur, sql, params=None: answers[sql])

    result = api.stock("hscode", None, None, None, None, None, None, {})

    assert result["totals"]["rows"] == 3 and result["totals"]["tallies"] == 2
    assert result["totals"]["insured_value"] == 250     # once for tally 1; tally 2 is not insured
    assert {g["key"] for g in result["groups"]} == {"111", "222"}
    assert {row["group_key"] for row in result["rows"]} == {"111", "222"}
    assert [a["name"] for a in result["facets"]["anbars"]] == ["8", "9"]
    assert api.stock("owner", None, 2, None, None, None, None, {})["totals"]["rows"] == 1


def test_stock_endpoint_rejects_bad_parameters():
    with pytest.raises(HTTPException) as exc:
        api.stock("weird", None, None, None, None, None, None, {})
    assert exc.value.status_code == 422
    with pytest.raises(HTTPException):
        api.stock("hscode", None, None, None, "moon", None, None, {})
