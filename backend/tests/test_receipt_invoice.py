"""One receipt's invoice under the 1405 rules: storage per cargo type, service
order, prepayment/discount decision and totals. DB-free."""
from decimal import Decimal

import pytest

from app.services import receipt_invoice as ri
from app.services.receipt_invoice import SERVICE_LABELS
from app.services.jalali import from_jalali
from app.services.storage_calc import billed_days


def line(**overrides):
    base = {"id": 1, "hscode": "7208", "description": "ورق", "goods_group": 1,
            "kala_code": "101", "storage_price": 56003, "zarib_mahal": "انبارداری مسقف",
            "number_hamel": "MSKU1234567", "quantity": Decimal(10), "weight_kg": Decimal(100000)}
    return {**base, **overrides}


# --- cargo type ------------------------------------------------------------------------

@pytest.mark.parametrize("stored, cargo", [
    ("weight", "weight"), ("volumetric", "volumetric"), ("container", "container"),
    ("yes", "volumetric"), ("no", "weight"),
])
def test_cargo_type(stored, cargo):
    assert ri.cargo_type(stored) == cargo


@pytest.mark.parametrize("stored", [None, "", "other"])
def test_cargo_type_must_be_set(stored):
    with pytest.raises(ValueError):
        ri.cargo_type(stored)


# --- weight ----------------------------------------------------------------------------

def test_weight_bills_each_linked_line_with_its_own_rate_and_location():
    rows = ri.storage_rows("weight", [
        line(),
        line(id=2, kala_code="124", storage_price=43009, zarib_mahal="انبارداری محوطه",
             weight_kg=Decimal(2500)),
    ], 30)
    assert [r.description for r in rows] == ["هزینه انبارداری کد کالای 101",
                                            "هزینه انبارداری کد کالای 124"]
    assert rows[0].price == Decimal(252013500)   # 56,003 x 1.5 x 100 t x 30
    assert rows[1].price == Decimal(3548243)     # 43,009 x 1.1 x 2.5 t x 30 = 3,548,242.5
    assert rows[0].note == "56,003 × 1.5 (مسقف 50٪) × 100,000 کیلوگرم ÷ 1,000 × 30 روز = 252,013,500"
    assert (rows[0].quantity, rows[0].weight) == (Decimal(10), Decimal(100000))
    assert all(r.kind == "storage" for r in rows)


@pytest.mark.parametrize("bad, message", [
    ({"zarib_mahal": None}, "ضریب محل"),
    ({"storage_price": None}, "نرخ انبارداری"),
    ({"weight_kg": Decimal(0)}, "وزن اظهار"),
])
def test_weight_errors_name_the_line(bad, message):
    with pytest.raises(ValueError) as exc:
        ri.storage_rows("weight", [line(**bad)], 30)
    assert str(exc.value).startswith("7208: ") and message in str(exc.value)


def test_a_receipt_without_linked_lines_is_refused():
    with pytest.raises(ValueError):
        ri.storage_rows("weight", [], 30)


# --- volumetric --------------------------------------------------------------------------

def test_volumetric_uses_the_given_pallets_once_per_receipt():
    rows = ri.storage_rows("volumetric", [line(), line(id=2, hscode="7209")], 60, pallets=12)
    assert len(rows) == 1
    assert rows[0].price == Decimal(72579888)    # 56,003 x 1.5 x 1.2 x 12 x 60 = 72,579,888
    assert rows[0].quantity == Decimal(12) and rows[0].weight is None
    assert "12 پالت × 60 روز" in rows[0].note


@pytest.mark.parametrize("other", [
    {"goods_group": 2, "kala_code": "124"},
    {"zarib_mahal": "انبارداری محوطه"},
])
def test_volumetric_refuses_mixed_codes_or_locations(other):
    with pytest.raises(ValueError) as exc:
        ri.storage_rows("volumetric", [line(), line(id=2, **other)], 30, pallets=5)
    assert "تعداد پالت" in str(exc.value)


def test_volumetric_requires_pallets():
    with pytest.raises(ValueError):
        ri.storage_rows("volumetric", [line()], 30, pallets=None)


# --- container ----------------------------------------------------------------------------

def test_whole_container_is_charged_by_device_and_excess():
    rows = ri.storage_rows("container", [line(kala_code="118", storage_price=804650, excess_storage_price=80465)], 30,
                           container_weights={"MSKU1234567": Decimal(100000)})
    assert rows[0].description == "هزینه انبارداری کانتینر MSKU1234567 (کد کالای 118)"
    assert rows[0].quantity == Decimal(1)
    assert rows[0].weight == Decimal(100000)
    assert rows[0].price == Decimal(362092500)    # (804,650 + 90 x 80,465) x 1.5 x 30


def test_split_container_is_charged_by_this_receipts_weight_share():
    rows = ri.storage_rows("container", [line(kala_code="118", storage_price=804650, excess_storage_price=80465,
                                              weight_kg=Decimal(30000))], 30,
                           container_weights={"MSKU1234567": Decimal(100000)})
    assert rows[0].quantity == Decimal("0.3")
    assert rows[0].weight == Decimal(30000)
    assert rows[0].price == Decimal(108627750)    # 30% of the physical container charge
    assert "90 تن مازاد" in rows[0].note
    assert "سهم این قبض 0.3" in rows[0].note


def test_each_container_gets_its_own_row():
    rows = ri.storage_rows("container", [
        line(), line(id=2, number_hamel="TGHU7654321"),
    ], 30, container_weights={"MSKU1234567": Decimal(100000), "TGHU7654321": Decimal(100000)})
    assert [r.description.split()[3] for r in rows] == ["MSKU1234567", "TGHU7654321"]


def test_container_sums_declared_weight_across_linked_tally_lines():
    rows = ri.storage_rows("container", [
        line(weight_kg=Decimal(1200)),
        line(id=2, weight_kg=Decimal(2300)),
    ], 30, container_weights={"MSKU1234567": Decimal(10000)})
    assert len(rows) == 1
    assert rows[0].weight == Decimal(3500)
    assert rows[0].price == Decimal(8820473)   # 56,003 x 1.5 x 3.5 t x 30
    assert "3,500 کیلوگرم ÷ 1,000" in rows[0].note


@pytest.mark.parametrize("lines, weights, message", [
    ([line(number_hamel=None)], {}, "شماره حامل"),
    ([line(), line(id=2, goods_group=2)], {"MSKU1234567": 1}, "کد کالا یا ضریب محل"),
    ([line()], {}, "وزن اظهار کانتینر"),
    ([line(weight_kg=Decimal(0))], {"MSKU1234567": 1000}, "سهم وزنی"),
])
def test_container_errors(lines, weights, message):
    with pytest.raises(ValueError) as exc:
        ri.storage_rows("container", lines, 30, container_weights=weights)
    assert message in str(exc.value)


# --- services ---------------------------------------------------------------------------------

def test_services_follow_the_spec_order_and_explain_the_share():
    pool = [
        {"line_no": 1, "description": SERVICE_LABELS["other_service"], "total": 1000, "amount": 300},
        {"line_no": 2, "description": SERVICE_LABELS["diamound"], "total": 2000, "amount": 600},
        {"line_no": 3, "description": SERVICE_LABELS["strip"], "total": 0, "amount": 0},
        {"line_no": 4, "description": f'{SERVICE_LABELS["crane"]} — 20 فوت', "total": 500, "amount": 150},
    ]
    rows = ri.service_rows(pool, Decimal("0.3"))
    assert [r.service_line for r in rows] == [3, 4, 2, 1]
    assert rows[3].note == "سهم این قبض از 1,000 (نسبت 0.3) = 300"
    assert ri.service_rows(pool[:1], 1)[0].note == "کل مبلغ خدمت = 300"


# --- prepayment and discount ----------------------------------------------------------------------

@pytest.mark.parametrize("kwargs, plan", [
    ({"is_general": True, "prepayment": 100, "discount": None, "already_applied": False, "answer": None}, "apply"),
    ({"is_general": False, "prepayment": 100, "discount": None, "already_applied": False, "answer": None}, "ask"),
    ({"is_general": False, "prepayment": None, "discount": 50, "already_applied": False, "answer": True}, "apply"),
    ({"is_general": False, "prepayment": 100, "discount": 50, "already_applied": False, "answer": False}, "skip"),
    ({"is_general": False, "prepayment": 100, "discount": 50, "already_applied": True, "answer": None}, "none"),
    ({"is_general": True, "prepayment": 0, "discount": None, "already_applied": False, "answer": None}, "none"),
])
def test_deduction_plan(kwargs, plan):
    assert ri.deduction_plan(**kwargs) == plan


# --- whole invoice --------------------------------------------------------------------------------------

def storage_row(amount):
    return ri.InvoiceRow("storage", "هزینه انبارداری کد کالای 101", Decimal(amount), "")


def service_row(amount):
    return ri.InvoiceRow("service", SERVICE_LABELS["diamound"], Decimal(amount), "", service_line=1)


def test_invoice_rows_discount_then_tax_then_prepayment():
    rows, totals = ri.build_invoice(system_rate=50000, storage=[storage_row(600000)],
                                    services=[service_row(350000)], tax_rate=10,
                                    prepayment=200000, discount=50000, apply_deductions=True,
                                    receipt_label="1405_1503_2")
    assert [r.kind for r in rows] == ["system", "storage", "service", "discount", "tax", "prepayment"]
    assert [r.price for r in rows] == [50000, 600000, 350000, -50000, 95000, -200000]
    assert sum(r.price for r in rows) == totals.payable == Decimal(845000)
    assert rows[4].note == "10٪ × 950,000 = 95,000"
    assert rows[5].note == "پیش‌پرداخت سربرگ تالی، اعمال‌شده روی قبض \u20661405_1503_2\u2069 = 200,000"
    assert rows[3].note == "تخفیف سربرگ تالی، اعمال‌شده روی قبض \u20661405_1503_2\u2069 = 50,000"


def test_skipped_deductions_leave_no_rows():
    rows, totals = ri.build_invoice(system_rate=0, storage=[storage_row(1000)], services=[],
                                    tax_rate=0, prepayment=500, discount=100,
                                    apply_deductions=False)
    assert [r.kind for r in rows] == ["system", "storage"]   # zero tax -> no tax row
    assert totals.payable == 1000


def test_deductions_larger_than_the_invoice_are_refused():
    with pytest.raises(ValueError):
        ri.build_invoice(system_rate=0, storage=[storage_row(1000)], services=[], tax_rate=10,
                         prepayment=5000, apply_deductions=True)


def test_header_note():
    days = billed_days(from_jalali(1405, 1, 1), from_jalali(1405, 2, 1))
    assert ri.header_note("weight", days) == (
        "نوع بار: وزنی؛ 1405/01/01 تا 1405/02/01: 31 روز، 1 روزِ سی‌ویکم ماه کسر شد، مبنای محاسبه 30 روز")


# --- insurance ------------------------------------------------------------------------------------

from app.services.insurance_cover import InsuranceCover   # noqa: E402

UNINSURED = InsuranceCover(False, Decimal(0), None, Decimal(0), Decimal(0))


def insured(cover, ceiling=Decimal(5_000_000_000), used=Decimal(0)):
    return InsuranceCover(True, Decimal(0), ceiling, used, Decimal(cover))


def test_insurance_without_policy_charges_the_receipts_customs_value():
    row = ri.insurance_row(1_000_000_000, UNINSURED, 0, 30)
    assert (row.kind, row.description, row.price) == ("insurance", "هزینه بیمه", Decimal(550000))
    assert row.note == "1,000,000,000 × 0.00055 × 1 ماه (بدون بیمه) = 550,000"


@pytest.mark.parametrize("cover", [UNINSURED, "insured"])
def test_missing_customs_value_is_a_visible_zero_row(cover):
    cover = insured(1_000_000_000) if cover == "insured" else cover
    row = ri.insurance_row(0, cover, 0, 30, missing=["7208", "7209"])
    assert (row.kind, row.price) == ("insurance", Decimal(0))
    assert row.note == ("ارزش گمرکی کالاهای این قبض در تالی ثبت نشده است؛ هزینه بیمه صفر ثبت شد"
                        " (ردیف‌ها: 7208، 7209)")


def test_partly_missing_customs_is_explained_in_the_note():
    row = ri.insurance_row(1_000_000_000, UNINSURED, 0, 30, missing=["7209"])
    assert row.price == Decimal(550000)
    assert "ارزش گمرکی ردیف‌های 7209 ثبت نشده و صفر حساب شد" in row.note


def test_covered_receipt_with_missing_rows_keeps_a_zero_row():
    row = ri.insurance_row(800_000_000, insured(1_000_000_000), 0, 30, missing=["7209"])
    assert row.price == 0 and row.note.startswith("تحت پوشش بیمه") and "7209" in row.note


def test_insured_without_recorded_ceiling_charges_the_full_value_and_says_why():
    missing = InsuranceCover(True, Decimal(0), None, Decimal(0), Decimal(0), (("B-1", "S-1"),))
    row = ri.insurance_row(1_000_000_000, missing, 0, 30)
    assert row.price == Decimal(550000)
    assert row.note == (
        "1,000,000,000 × 0.00055 × 1 ماه (کل ارزش گمرکی قبض؛ تالی بیمه‌دار ثبت شده است "
        "(بیمه‌نامه «\u2066B-1\u2069» / ثبت سفارش «\u2066S-1\u2069») ولی ارزش کالای بیمه‌شده نه در ردیف‌های این تالی و نه در "
        "تالی‌های هم‌بیمه‌نامه ثبت نشده است؛ چون سقف بیمه معلوم نیست، کل ارزش گمرکی این قبض مبنای "
        "محاسبه قرار گرفت) = 550,000")


def test_fully_covered_receipt_has_no_insurance_row():
    assert ri.insurance_row(800_000_000, insured(1_000_000_000), 0, 30) is None


def test_under_insured_receipt_pays_only_the_real_shortfall():
    row = ri.insurance_row(1_200_000_000, insured(1_000_000_000, used=Decimal(4_000_000_000)), 0, 60)
    assert row.price == Decimal(220000)   # 200,000,000 x 0.00055 x 2
    assert row.note == ("200,000,000 × 0.00055 × 2 ماه (ارزش گمرکی 1,200,000,000 − پوشش باقی‌مانده "
                        "1,000,000,000؛ سقف بیمه‌نامه 5,000,000,000؛ مصرف تالی‌های قبلی 4,000,000,000)"
                        " = 220,000")


def test_earlier_invoiced_receipts_of_the_tally_use_its_cover_first():
    row = ri.insurance_row(500_000_000, insured(1_000_000_000), 700_000_000, 30)
    assert row.price == Decimal(110000)   # (500M - 300M left) x 0.00055 x 1
    assert "مصرف قبض‌های قبلی همین تالی 700,000,000" in row.note


def test_insurance_sits_between_services_and_tax():
    insurance = ri.insurance_row(1_000_000_000, UNINSURED, 0, 30)
    rows, _ = ri.build_invoice(system_rate=0, storage=[storage_row(1000)],
                               services=[service_row(500)], tax_rate=10, insurance=insurance)
    assert [r.kind for r in rows] == ["system", "storage", "service", "insurance", "tax"]


@pytest.mark.parametrize("code,rate,extra,weight,expected_excess,expected", [
    ("120", 1906300, 160930, 20400, 6, 206775360),
    ("120", 1906300, 160930, 15000, 0, 137253600),
    ("120", 1906300, 160930, 15001, 1, 148840560),
    ("118", 804650, 80465, 10000, 0, 57934800),
    ("118", 804650, 80465, 10400, 1, 63728280),
    ("118", 804650, 80465, 20400, 11, 121663080),
])
def test_container_base_and_rounded_excess(code, rate, extra, weight, expected_excess, expected):
    rows = ri.storage_rows("container", [line(kala_code=code, storage_price=rate,
        excess_storage_price=extra, weight_kg=Decimal(weight), zarib_mahal="بارانداز")],
        60, container_weights={"MSKU1234567": weight})
    assert len(rows) == 1
    assert rows[0].price == Decimal(expected)
    assert "× 1 دستگاه" in rows[0].note
    if expected_excess:
        assert f"× {expected_excess} تن مازاد" in rows[0].note
    else:
        assert "تن مازاد" not in rows[0].note


@pytest.mark.parametrize("bad_rate", [None, "", "bad", -1, "NaN", "Infinity"])
def test_container_excess_requires_valid_tariff(bad_rate):
    with pytest.raises(ValueError, match="مازاد"):
        ri.storage_rows("container", [line(kala_code="120", storage_price=1906300,
            excess_storage_price=bad_rate, weight_kg=Decimal(20400))],
            60, container_weights={"MSKU1234567": 20400})


def test_split_container_allocates_base_and_excess_without_charging_twice():
    amounts = []
    for weight in (10200, 10200):
        rows = ri.storage_rows("container", [line(kala_code="120", storage_price=1906300,
            excess_storage_price=160930, weight_kg=Decimal(weight), zarib_mahal="بارانداز")],
            60, container_weights={"MSKU1234567": 20400})
        assert rows[0].quantity == Decimal("0.5")
        amounts.append(rows[0].price)
    assert sum(amounts) == Decimal(206775360)


def test_screenshot_insurance_uses_two_months():
    row = ri.insurance_row(671695063084, insured(3870986209), 0, 60)
    assert row.price == Decimal(734606485)
    assert "× 2 ماه" in row.note
