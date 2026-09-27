"""Shared insurance ceilings are consumed in tally registration order: earlier
tallies draw first, and only a later tally's real shortfall remains."""
from decimal import Decimal

from app.services.insurance_cover import insurance_cover


def header(tid, bimeh="B-1", sabt="S-1", is_bimeh="بله"):
    return {"id_tali": tid, "is_bimeh": is_bimeh, "number_bimeh": bimeh, "sabt_sefaresh_number": sabt}


def totals(**by_id):
    return {int(k[1:]): {"customs_value": c, "insured_ceiling": i} for k, (c, i) in by_id.items()}


def test_uninsured_tally_has_no_cover():
    cover = insurance_cover(1, [header(1, is_bimeh="خیر")], totals(t1=(800, 1000)))
    assert (cover.insured, cover.cover, cover.customs) == (False, 0, 800)


def test_single_tally_within_and_over_its_ceiling():
    assert insurance_cover(1, [header(1)], totals(t1=(800, 1000))).cover == 800
    over = insurance_cover(1, [header(1)], totals(t1=(1200, 1000)))
    assert (over.ceiling, over.used_before, over.cover) == (1000, 0, 1000)


def test_earlier_tallies_draw_first():
    headers = [header(1), header(2), header(3)]
    t = totals(t1=(600, 1000), t2=(600, 1000), t3=(600, 1000))
    assert insurance_cover(1, headers, t).cover == 600
    second = insurance_cover(2, headers, t)
    assert (second.used_before, second.cover) == (600, 400)     # shortfall 200 is real
    third = insurance_cover(3, headers, t)
    assert (third.used_before, third.cover) == (1000, 0)


def test_later_tallies_never_reduce_an_earlier_tallys_cover():
    t = totals(t1=(600, 1000), t2=(5000, 1000))
    assert insurance_cover(1, [header(1), header(2)], t).cover == 600


def test_ceiling_is_the_largest_recorded_value_never_a_sum():
    t = totals(t1=(900, 1000), t2=(900, 1500))
    second = insurance_cover(2, [header(1), header(2)], t)
    assert (second.ceiling, second.cover) == (1500, 600)


def test_uninsured_tallies_do_not_draw_on_a_shared_policy():
    t = totals(t1=(900, 1000), t2=(900, 1000))
    assert insurance_cover(2, [header(1, is_bimeh="خیر"), header(2)], t).cover == 900


def test_a_tally_with_two_policies_fills_them_in_listed_order():
    headers = [header(1, bimeh="B-1\nB-2", sabt="S-1\nS-2"), header(2, bimeh="B-2", sabt="S-2")]
    t = totals(t1=(1500, 1000), t2=(800, 1000))
    # tally 1 takes 1,000 from B-1 and 500 from B-2; tally 2 finds 500 left on B-2
    second = insurance_cover(2, headers, t)
    assert (second.used_before, second.cover) == (500, 500)
    first = insurance_cover(1, headers, t)
    assert (first.ceiling, first.cover) == (2000, 1500)


def test_policy_numbers_match_across_persian_digits():
    headers = [header(1, bimeh="۱۲۳", sabt="۴۵"), header(2, bimeh="123", sabt="45")]
    assert insurance_cover(2, headers, totals(t1=(700, 1000), t2=(700, 1000))).cover == 300


def test_insured_without_policy_numbers_uses_only_its_own_ceiling():
    headers = [header(1, bimeh=None, sabt=None), header(2, bimeh=None, sabt=None)]
    assert insurance_cover(2, headers, totals(t1=(900, 1000), t2=(900, 1000))).cover == 900


def test_missing_ceiling_is_reported():
    cover = insurance_cover(1, [header(1)], totals(t1=(900, None)))
    assert cover.insured and cover.missing_ceiling and cover.cover == 0


def test_unknown_or_rowless_tally():
    assert insurance_cover(9, [header(1)], {}).insured is False
    assert insurance_cover(1, [header(1)], {}).customs == Decimal(0)


def test_cover_reports_shortfall_policies_and_earlier_consumers():
    headers = [header(1), header(2, bimeh="X-9"), header(3)]
    t = totals(t1=(600, 1000), t2=(900, 1000), t3=(700, 1000))
    third = insurance_cover(3, headers, t)
    assert (third.shortfall, third.drawn_by) == (300, (1,))       # tally 2 is another policy
    assert third.policy_text == "بیمه‌نامه «B-1» / ثبت سفارش «S-1»"
    assert insurance_cover(1, headers, t).shortfall == 0
    missing = insurance_cover(1, [header(1)], totals(t1=(900, None)))
    assert missing.shortfall == 0 and missing.missing_ceiling


# --- the tally banner uses the same algorithm ---------------------------------------------

from app.routers import tally as tally_api   # noqa: E402
from app.services import insurance_cover as cover_sql   # noqa: E402


def banner(monkeypatch, tid, headers, t):
    rows = {cover_sql.HEADERS_SQL: headers,
            cover_sql.TOTALS_SQL: [{"id_tali": k, **v} for k, v in t.items()]}
    monkeypatch.setattr(tally_api, "fetch_all", lambda sql, params=None: rows[sql])
    return tally_api.check_tally_insurance(tid)


def test_banner_warns_only_the_tally_with_a_real_shortfall(monkeypatch):
    headers = [{**header(1), "tali_number": "1001"}, {**header(2), "tali_number": "1002"}]
    t = totals(t1=(600, 1000), t2=(600, 1000))
    first = banner(monkeypatch, 1, headers, t)
    assert first["is_over"] is False                      # no false warning on the earlier tally
    second = banner(monkeypatch, 2, headers, t)
    assert second["is_over"] is True
    assert (second["shortfall"], second["used_before"], second["cover"]) == (200, 600, 400)
    assert second["earlier_tallies"] == ["1001"]
    assert second["policies"] == [{"number_bimeh": "B-1", "sabt_sefaresh_number": "S-1"}]


def test_banner_flags_an_insured_tally_without_insured_value(monkeypatch):
    result = banner(monkeypatch, 1, [{**header(1), "tali_number": "1001"}], totals(t1=(900, None)))
    assert result["missing_ceiling"] is True and result["is_over"] is False


def test_banner_404_for_unknown_tally(monkeypatch):
    import pytest
    from fastapi import HTTPException
    with pytest.raises(HTTPException):
        banner(monkeypatch, 9, [{**header(1), "tali_number": "1001"}], {})
