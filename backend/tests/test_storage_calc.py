"""Rules behind the 1405 invoice: day blocks, location coefficient, storage,
insurance and totals. The day-count cases are the business examples verbatim."""
from datetime import date, datetime, timedelta
from decimal import Decimal

import pytest

from app.services.jalali import from_jalali, to_jalali
from app.services.storage_calc import (
    billed_days, insurance_charge, invoice_totals, location, storage_charge,
)


def j(text: str) -> date:
    year, month, day = (int(part) for part in text.split("/"))
    return from_jalali(year, month, day)


# --- Jalali conversion used by the tests and the invoice ---------------------------

def test_from_jalali_round_trips_and_rejects_impossible_days():
    assert j("1405/01/01") == date(2026, 3, 21)
    assert to_jalali(j("1405/06/31")) == (1405, 6, 31)
    for impossible in ("1405/07/31", "1405/12/30"):
        with pytest.raises(ValueError):
            j(impossible)


# --- day blocks ----------------------------------------------------------------------
#
# The rule, step by step:
#   1. actual days = exit date - unloading date
#   2. remove every date in the stay that is the 31st of a Jalali month; only
#      Farvardin, Ordibehesht, Khordad, Tir, Mordad and Shahrivar have one,
#      months 7 to 12 never do
#   3. bill what remains in 30-day blocks, minimum one block

@pytest.mark.parametrize("month", range(1, 7))
def test_rule_step2_the_31st_of_months_1_to_6_is_removed(month):
    start = j(f"1405/{month:02d}/10")
    end = j(f"1405/{month + 1:02d}/10")          # one calendar month, 31 days
    result = billed_days(start, end)
    assert (result.actual, result.forgiven, result.billed) == (31, 1, 30)


@pytest.mark.parametrize("year", [1405, 1403])   # common and leap year
@pytest.mark.parametrize("month", range(7, 13))
def test_rule_step2_months_7_to_12_have_no_31st(year, month):
    with pytest.raises(ValueError):
        j(f"{year}/{month:02d}/31")


@pytest.mark.parametrize("month", range(7, 13))
def test_rule_step2_nothing_is_removed_from_31_days_in_months_7_to_12(month):
    start = j(f"1405/{month:02d}/10")
    result = billed_days(start, start + timedelta(days=31))
    assert (result.actual, result.forgiven, result.billed) == (31, 0, 60)


@pytest.mark.parametrize("start, end, remaining, billed", [
    ("1405/01/01", "1405/07/01", 180, 180),   # 186 - 6 removed
    ("1405/01/01", "1405/07/02", 181, 210),   # 187 - 6 removed, one day into block 7
    ("1405/05/01", "1405/08/01", 90, 90),     # 92 - 2 (Mordad 31, Shahrivar 31)
    ("1405/05/01", "1405/08/02", 91, 120),    # 93 - 2
    ("1405/05/01", "1405/07/30", 89, 90),     # 91 - 2
])
def test_rule_step3_remaining_days_bill_in_30_day_blocks(start, end, remaining, billed):
    result = billed_days(j(start), j(end))
    assert (result.actual - result.forgiven, result.billed) == (remaining, billed)


@pytest.mark.parametrize("start, end, actual, forgiven, billed", [
    # business examples
    ("1405/01/01", "1405/01/31", 30, 0, 30),
    ("1405/01/01", "1405/02/01", 31, 1, 30),   # Farvardin has 31 days
    ("1405/02/01", "1405/03/03", 33, 1, 60),
    ("1405/01/01", "1405/03/01", 62, 2, 60),   # two 31-day months
    ("1405/07/01", "1405/09/03", 62, 0, 90),   # 30-day months
    # the 31st day of a stay that is not caused by a 31-day month
    ("1405/07/10", "1405/08/11", 31, 0, 60),   # Mehr has 30 days
    ("1405/08/10", "1405/09/11", 31, 0, 60),   # Aban has 30 days
    # the extra day comes from Shahrivar even though day 31 of the stay is in Mehr
    ("1405/06/10", "1405/07/10", 31, 1, 30),
    # minimum one block
    ("1405/03/15", "1405/03/15", 0, 0, 30),
    ("1405/01/31", "1405/02/01", 1, 1, 30),
    # Esfand 1405 has 29 days
    ("1405/12/01", "1406/01/01", 29, 0, 30),
    ("1405/12/01", "1406/01/02", 30, 0, 30),
    ("1405/12/01", "1406/01/03", 31, 0, 60),
    # half a year of 31-day months
    ("1405/01/01", "1405/07/01", 186, 6, 180),
])
def test_billed_days(start, end, actual, forgiven, billed):
    result = billed_days(j(start), j(end))
    assert (result.actual, result.forgiven, result.billed) == (actual, forgiven, billed)


def test_billed_days_accepts_datetimes_and_rejects_reverse_ranges():
    start = datetime.combine(j("1405/01/01"), datetime.min.time())
    assert billed_days(start, j("1405/02/01")).billed == 30
    with pytest.raises(ValueError):
        billed_days(j("1405/02/01"), j("1405/01/01"))


def test_billed_days_note_explains_the_forgiven_day():
    note = billed_days(j("1405/01/01"), j("1405/02/01")).note
    assert note == "1405/01/01 تا 1405/02/01: 31 روز، 1 روزِ سی‌ویکم ماه کسر شد، مبنای محاسبه 30 روز"


# --- location coefficient ----------------------------------------------------------------

@pytest.mark.parametrize("label, multiplier", [
    ("انبارداری مسقف", "1.5"),
    ("انبارداری هانگار", "1.3"),
    ("انبارداری بارانداز", "1.2"),
    ("انبارداری محوطه", "1.1"),
    ("مسقف", "1.5"),
    ("هنگار", "1.3"),
    ("انبارداري مسقف", "1.5"),   # Arabic yeh
    ("1.5", "1.5"),              # legacy numeric coefficient
    ("۱٫۵", "1.5"),              # legacy, Persian digits
])
def test_location_multiplier(label, multiplier):
    assert location(label).multiplier == Decimal(multiplier)


@pytest.mark.parametrize("bad", [None, "", "  ", "انبار نامشخص", "0", "-1"])
def test_location_rejects_missing_or_unknown(bad):
    with pytest.raises(ValueError):
        location(bad)


# --- storage -----------------------------------------------------------------------------

def test_weight_storage_converts_kg_to_tons():
    charge = storage_charge("weight", rate=56003, loc=location("انبارداری مسقف"),
                            days=30, weight_kg=435436)
    # 435,436 kg is 435 tons and 436 kg: 56,003 x 1.5 x 435.436 x 30 = 1,097,357,503.86
    assert charge.amount == Decimal(1097357504)
    assert charge.note == "56,003 × 1.5 (مسقف 50٪) × 435,436 کیلوگرم ÷ 1,000 × 30 روز = 1,097,357,504"


def test_weight_storage_rounds_half_up():
    charge = storage_charge("weight", rate=56003, loc=location("مسقف"), days=30, weight_kg=100)
    assert charge.amount == Decimal(252014)   # 252,013.5


def test_volumetric_storage_uses_the_given_pallets():
    charge = storage_charge("volumetric", rate=56003, loc=location("محوطه"), days=30, pallets=10)
    assert charge.amount == Decimal(22177188)   # 56,003 x 1.1 x 1.2 x 10 x 30
    assert charge.note == "56,003 × 1.1 (محوطه 10٪) × 1.2 × 10 پالت × 30 روز = 22,177,188"


def test_container_storage_uses_declared_weight_in_tons():
    charge = storage_charge("container", rate=804650, loc=location("بارانداز"), days=60,
                            weight_kg=25000)
    assert charge.amount == Decimal(1448370000)   # 804,650 x 1.2 x 25 t x 60
    assert charge.note == "804,650 × 1.2 (بارانداز 20٪) × 25,000 کیلوگرم ÷ 1,000 × 60 روز = 1,448,370,000"


def test_container_storage_preserves_fractional_tons_and_rounds_rials():
    charge = storage_charge("container", rate=56003, loc=location("مسقف"),
                            days=30, weight_kg=100)
    assert charge.amount == Decimal(252014)   # 0.1 t; 252,013.5 rounded half up


@pytest.mark.parametrize("cargo, kwargs", [
    ("weight", {}),
    ("weight", {"weight_kg": 0}),
    ("container", {}),
    ("container", {"weight_kg": 0}),
    ("container", {"weight_kg": -1}),
    ("volumetric", {}),
    ("volumetric", {"weight_kg": 1000}),
    ("unknown", {"weight_kg": 1000}),
])
def test_storage_requires_the_cargo_quantity(cargo, kwargs):
    with pytest.raises(ValueError):
        storage_charge(cargo, rate=56003, loc=location("مسقف"), days=30, **kwargs)


def test_storage_requires_a_rate():
    with pytest.raises(ValueError):
        storage_charge("weight", rate=None, loc=location("مسقف"), days=30, weight_kg=1000)


# --- insurance -------------------------------------------------------------------------------

def test_insurance_without_policy_uses_full_customs_value():
    charge = insurance_charge(1_000_000_000, None, 30)
    assert charge.amount == Decimal(16500000)
    assert charge.note == "1,000,000,000 × 0.00055 × 30 روز (بدون بیمه) = 16,500,000"


def test_insurance_under_insured_uses_the_shortfall():
    charge = insurance_charge(1_200_000_000, 1_000_000_000, 60)
    assert charge.amount == Decimal(6600000)   # 200,000,000 x 0.00055 x 60


@pytest.mark.parametrize("insured", [1_000_000_000, 1_500_000_000])
def test_insurance_fully_covered_is_not_charged(insured):
    assert insurance_charge(1_000_000_000, insured, 30) is None


def test_insurance_requires_customs_value():
    with pytest.raises(ValueError):
        insurance_charge(None, None, 30)


# --- totals ------------------------------------------------------------------------------------

def test_totals_add_tax_before_deductions():
    totals = invoice_totals([Decimal(600000), Decimal(400000)], "10",
                            prepayment=200000, discount=50000)
    assert (totals.subtotal, totals.tax, totals.payable) == (1000000, 100000, 850000)


def test_totals_round_tax_and_default_missing_deductions():
    totals = invoice_totals([Decimal(1234565)], 10)
    assert totals.tax == Decimal(123457)          # 123,456.5
    assert totals.payable == Decimal(1358022)


def test_totals_reject_negative_deductions():
    with pytest.raises(ValueError):
        invoice_totals([Decimal(1)], 10, prepayment=-1)
