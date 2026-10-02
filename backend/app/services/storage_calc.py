"""Storage, insurance and invoice totals for the 1405 invoice rules.

Pure and DB-free, like receipt_invoice.py and insurance_check.py, so every rule is
unit-tested without Oracle. The storage rate is
fa_kala_price."storage_price" (انبارداری), a per-day rate per ton, per pallet
equivalent. Full 20/40-foot containers use a per-device base plus rounded excess tons.

Storage, by the keeper's cargo type (IS_VOLUMETRIC):
    weight      rate x location x (declared weight in kg / 1000) x days
    volumetric  rate x location x 1.2 x pallets x days
    container   (base rate + excess rate x ceil(excess tons)) x location x days
The caller supplies the pallets: a detailed receipt's own pallet count, or the
tally's keeper-recorded count for a general receipt. Nothing is distributed here.

Location («نرخ + ٪ ضریب محل») raises the rate by a percentage:
    مسقف 50%, هانگار 30%, بارانداز 20%, محوطه 10%
Legacy rows stored a numeric coefficient before ZARIB_MAHAL became a label;
such a value is used as the multiplier itself (1.5 == مسقف).

Insurance: base x 0.00055 x billed months. The base is the customs value when there is
no insurance, or the shortfall (customs value - insured ceiling) when the goods
are under-insured. Fully covered goods are not charged.

Totals: charges - discount + VAT - prepayment. VAT is computed after discount,
before subtracting prepayment.

Day count: actual days are (end - start). Every date inside the stay that is
the 31st of a Jalali month is removed; only Farvardin to Shahrivar have a 31st,
months 7 to 12 never do. The remaining days are billed in 30-day blocks, with a
minimum of one block. So 1405/06/10 to 1405/07/10 (31 days, Shahrivar 31 inside)
bills as 30, 31 days across Mehr bill as 60, and 62 days bill as 60 only when
both removed days come from 31-day months.

Every amount is rounded to whole rials (half up) and returned with a note that
shows the operator exactly how it was produced.
"""
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP, ROUND_CEILING
from typing import Optional

from app.services.insurance_check import normalize_number_text
from app.services.jalali import format_jalali, to_jalali

BLOCK_DAYS = 30
VOLUMETRIC_FACTOR = Decimal("1.2")
INSURANCE_MONTHLY_RATE = Decimal("0.00055")
KG_PER_TON = Decimal(1000)

# Keyword -> percent. Matched as substrings so both the dropdown labels
# ('انبارداری مسقف') and bare names ('مسقف') resolve. 'هنگار' is a stored misspelling.
LOCATION_PERCENT = (
    ("مسقف", 50),
    ("هانگار", 30),
    ("هنگار", 30),
    ("بارانداز", 20),
    ("محوطه", 10),
)

CARGO_TYPES = ("weight", "volumetric", "container")


# --- helpers -----------------------------------------------------------------

def _as_date(value) -> date:
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    raise TypeError(f"Expected a date, received {type(value).__name__}")


def _decimal(value, what: str) -> Decimal:
    """Parse a numeric input (Persian digits allowed); fail loudly when missing."""
    if value is None:
        raise ValueError(f"{what} ثبت نشده است")
    if isinstance(value, Decimal):
        return value
    if isinstance(value, (int, float)):
        return Decimal(str(value))
    text = normalize_number_text(value).replace("٫", ".").replace(",", "").replace("٬", "")
    try:
        return Decimal(text)
    except InvalidOperation as exc:
        raise ValueError(f"{what} معتبر نیست") from exc


def _positive(value, what: str) -> Decimal:
    number = _decimal(value, what)
    if not number.is_finite() or number <= 0:
        raise ValueError(f"{what} باید بیشتر از صفر باشد")
    return number


def round_rial(value: Decimal) -> Decimal:
    return value.quantize(Decimal(1), rounding=ROUND_HALF_UP)


def ltr(text) -> str:
    """Isolate a left-to-right token (receipt or policy number) inside a Persian
    note, so e.g. 1405_1503_2 is not displayed as 2_1503_1405."""
    return f"\u2066{text}\u2069"


def fmt(value) -> str:
    """Latin digits, comma grouping, no trailing zeros (matches the invoice UI)."""
    return format(Decimal(value).normalize(), ",f")


# --- day count -----------------------------------------------------------------

@dataclass(frozen=True)
class BilledDays:
    start: date
    end: date
    actual: int     # end - start
    forgiven: int   # 31st days of Jalali months inside [start, end)
    billed: int     # whole 30-day blocks, minimum one

    @property
    def note(self) -> str:
        text = f"{format_jalali(self.start)} تا {format_jalali(self.end)}: {self.actual} روز"
        if self.forgiven:
            text += f"، {self.forgiven} روزِ سی‌ویکم ماه کسر شد"
        return f"{text}، مبنای محاسبه {self.billed} روز"


def billed_days(start, end) -> BilledDays:
    start, end = _as_date(start), _as_date(end)
    if end < start:
        raise ValueError("تاریخ صدور صورتحساب نمی‌تواند پیش از تاریخ تخلیه باشد")
    actual = (end - start).days
    forgiven = sum(1 for offset in range(actual)
                   if to_jalali(start + timedelta(days=offset))[2] == 31)
    effective = actual - forgiven
    blocks = max(1, -(-effective // BLOCK_DAYS))
    return BilledDays(start, end, actual, forgiven, blocks * BLOCK_DAYS)


# --- location coefficient ---------------------------------------------------------

@dataclass(frozen=True)
class Location:
    multiplier: Decimal
    label: str


def location(zarib_mahal) -> Location:
    text = str(zarib_mahal or "").replace("ي", "ی").replace("ك", "ک").strip()
    for keyword, percent in LOCATION_PERCENT:
        if keyword in text:
            label = "هانگار" if keyword == "هنگار" else keyword
            return Location(1 + Decimal(percent) / 100, f"{label} {percent}٪")
    if not text:
        raise ValueError("ضریب محل کالا ثبت نشده است")
    try:
        legacy = _positive(text, "ضریب محل")
    except ValueError as exc:
        raise ValueError(f"ضریب محل «{zarib_mahal}» معتبر نیست") from exc
    return Location(legacy, f"ضریب {fmt(legacy)}")


# --- charges ---------------------------------------------------------------------

@dataclass(frozen=True)
class Charge:
    amount: Decimal   # whole rials
    note: str


def _storage_note(rate: Decimal, loc: Location, middle: str, days: int) -> str:
    return f"{fmt(rate)} × {fmt(loc.multiplier)} ({loc.label}) × {middle} × {days} روز"


def storage_charge(cargo_type: str, *, rate, loc: Location, days: int,
                   weight_kg=None, pallets=None) -> Charge:
    """One storage line. Which quantity is required depends on the cargo type."""
    rate = _decimal(rate, "نرخ انبارداری کد کالا")
    if rate < 0:
        raise ValueError("نرخ انبارداری کد کالا نمی‌تواند منفی باشد")
    days_d = Decimal(days)
    if cargo_type in ("weight", "container"):
        # وزن اظهار is stored in kilograms; the tariff is per ton. The note shows
        # the kg value as entered plus the ÷ 1,000 step so it cannot be misread.
        kg = _positive(weight_kg, "وزن اظهار")
        raw = rate * loc.multiplier * (kg / KG_PER_TON) * days_d
        middle = f"{fmt(kg)} کیلوگرم ÷ {fmt(KG_PER_TON)}"
    elif cargo_type == "volumetric":
        count = _positive(pallets, "تعداد پالت")
        raw = rate * loc.multiplier * VOLUMETRIC_FACTOR * count * days_d
        middle = f"{fmt(VOLUMETRIC_FACTOR)} × {fmt(count)} پالت"
    else:
        raise ValueError("نوع بار (وزنی، حجمی یا کانتینری) مشخص نشده است")
    amount = round_rial(raw)
    return Charge(amount, f"{_storage_note(rate, loc, middle, days)} = {fmt(amount)}")


def container_storage_charge(*, rate, excess_rate, capacity_tons, weight_kg,
                             share, loc: Location, days: int) -> Charge:
    """Price a physical container once, then allocate its charge to this receipt."""
    base = _decimal(rate, "نرخ انبارداری کد کالا")
    if not base.is_finite() or base < 0:
        raise ValueError("نرخ انبارداری کد کالا نامعتبر است")
    kg = _positive(weight_kg, "وزن اظهار کانتینر")
    tons = (kg / KG_PER_TON).to_integral_value(rounding=ROUND_CEILING)
    excess = max(Decimal(0), tons - Decimal(capacity_tons))
    daily = base
    formula = f"{fmt(base)} × 1 دستگاه"
    if excess:
        extra = _decimal(excess_rate, "نرخ مازاد انبارداری کانتینر")
        if not extra.is_finite() or extra < 0:
            raise ValueError("نرخ مازاد انبارداری کانتینر نامعتبر است")
        daily += extra * excess
        formula += f" + {fmt(extra)} × {fmt(excess)} تن مازاد"
    amount = round_rial(daily * loc.multiplier * Decimal(days) * share)
    note = (f"({formula}) × {fmt(loc.multiplier)} ({loc.label}) × {days} روز"
            f"؛ وزن {fmt(kg)} کیلوگرم، گرد به بالا {fmt(tons)} تن، سقف {capacity_tons} تن")
    if share < 1:
        note += f"؛ سهم این قبض {fmt(share)}"
    return Charge(amount, f"{note} = {fmt(amount)}")


def insurance_months(days: int) -> int:
    """Use the same minimum-one, 30-day billing blocks as storage."""
    return max(1, -(-days // BLOCK_DAYS))


def insurance_charge(customs_value, insured_value, days: int) -> Optional[Charge]:
    """insured_value None means the goods have no insurance.

    Returns None when the insured ceiling covers the customs value.
    """
    customs = _decimal(customs_value, "ارزش کالای گمرکی")
    if insured_value is None:
        base, basis = customs, "بدون بیمه"
    else:
        insured = _decimal(insured_value, "ارزش بیمه‌شده")
        base = customs - insured
        if base <= 0:
            return None
        basis = f"کسری بیمه {fmt(customs)} − {fmt(insured)}"
    months = insurance_months(days)
    amount = round_rial(base * INSURANCE_MONTHLY_RATE * Decimal(months))
    note = f"{fmt(base)} × {fmt(INSURANCE_MONTHLY_RATE)} × {months} ماه ({basis}) = {fmt(amount)}"
    return Charge(amount, note)


# --- totals ----------------------------------------------------------------------

@dataclass(frozen=True)
class Totals:
    subtotal: Decimal
    tax_rate: Decimal
    tax: Decimal
    prepayment: Decimal
    discount: Decimal
    payable: Decimal


def invoice_totals(amounts, tax_rate, prepayment=None, discount=None) -> Totals:
    """جمع هزینه‌ها − تخفیف + مالیاتِ مبلغ پس از تخفیف − پیش‌پرداخت."""
    subtotal = sum((Decimal(a) for a in amounts), Decimal(0))
    rate = _decimal(tax_rate, "نرخ مالیات")
    prepaid = Decimal(0) if prepayment is None else _decimal(prepayment, "پیش‌پرداخت")
    off = Decimal(0) if discount is None else _decimal(discount, "تخفیف")
    if prepaid < 0 or off < 0:
        raise ValueError("پیش‌پرداخت و تخفیف نمی‌توانند منفی باشند")
    if off > subtotal:
        raise ValueError("تخفیف نمی‌تواند از جمع هزینه‌ها بیشتر باشد")
    taxable = subtotal - off
    tax = round_rial(taxable * rate / 100)
    return Totals(subtotal, rate, tax, prepaid, off, taxable + tax - prepaid)
