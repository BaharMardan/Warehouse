"""Invoice rows for one warehouse receipt under the 1405 rules.

DB-free: the receipt_workflow router fetches plain rows and passes them here, so
every rule is unit-tested without Oracle. Amount formulas live in storage_calc.

Row order follows the business spec:
    1 system service   2 storage   3 strip, stuffing, crane, transportation
    4 demurrage        5 entry     6 other services   (then night stop)
    7 insurance        8 VAT              9 prepayment and discount (negative rows)

Insurance: base x 0.00055 x days. Without insurance the base is the receipt's
customs value. With insurance it is the part of that value the tally's remaining
cover does not reach; the cover is consumed in tally registration order
(insurance_cover.py) and, inside a tally, by its receipts in invoice order.

Storage per cargo type:
  weight      one row per linked tally line, its own rate, location and weight
  volumetric  one row per receipt; pallets come from the receipt (detailed) or
              the tally (general). All linked lines must share one goods code and
              one location, otherwise the pallets per code are unknown and the
              invoice is refused rather than guessed.
  container   one row per container (NUMBER_HAMEL). A container split between
              detailed receipts is charged by this receipt's share of the
              container's declared weight; a whole container counts as 1.
"""
from collections import OrderedDict
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from typing import Optional

from app.services import storage_calc as sc
from app.services.container_excess import derived_rows
from app.services.insurance_cover import InsuranceCover

# --- shared service charges (snapshotted once per tally) ----------------------
# Labels are persisted as the pool/invoice row DESCRIPTION, so they must not change.
SERVICE_LABELS = {
    "other_service": "هزینه کل سایر خدمات",
    "strip": "هزینه کل استریپ / تخلیه",
    "stuffing": "هزینه کل استافینگ / بارگیری",
    "transportation": "هزینه باربری",
    "crane": "هزینه جابه‌جایی کانتینر با جرثقیل",
    "night_stop": "هزینه کل توقف شبانه",
    "diamound": "هزینه کل دیماند",
    "vehicle_enter": "هزینه کل حق ورودی (حق محوطه)",
}

# Pricing type on a strip/stuffing/crane junction selects the tariff column;
# NULL or unknown means "normal". unloading/loading use the per-ton handling
# amount computed from the carrier's goods.
_STRIP_COLUMN = {"normal": "normal", "non_standard": "non_standard", "dangerous": "dangerous"}


class ServiceTariffError(ValueError):
    """A selected service has a missing, non-numeric or negative tariff."""


@dataclass(frozen=True)
class ServiceCharge:
    description: str
    quantity: Optional[object]    # int, Decimal or None, as stored on the pool row
    price: Optional[Decimal]


def to_decimal(value) -> Optional[Decimal]:
    """Catalog prices are VARCHAR2: blank or non-numeric text is None (no charge)."""
    if value is None:
        return None
    if isinstance(value, Decimal):
        return value
    if isinstance(value, int):
        return Decimal(value)
    if isinstance(value, float):
        return Decimal(str(value))
    text = str(value).strip()
    if text == "":
        return None
    try:
        return Decimal(text)
    except InvalidOperation:
        return None


def strip_price(row: dict):
    if row.get("pricing_type") == "unloading":
        return row["unloading_amount"]
    if row.get("pricing_type") == "loading":
        return row["loading_amount"]
    return row[_STRIP_COLUMN.get((row.get("pricing_type") or "normal"), "normal")]


def _weighted_total(prices, counts):
    """Sum of price x quantity; a blank quantity counts as one."""
    price_values, count_values = list(prices), list(counts)
    if not price_values:
        return Decimal(0), None, False
    total, total_count = Decimal(0), Decimal(0)
    for index, raw_price in enumerate(price_values):
        quantity = to_decimal(count_values[index]) if index < len(count_values) else None
        if quantity is None:
            quantity = Decimal(1)
        total_count += quantity
        price = to_decimal(raw_price)
        if price is not None:
            total += price * quantity
    return total, int(total_count), True


def service_charges(*, other, strip, night, diamound, vehicle, container_weights, excess_catalog,
                    freight_rate, carrier_count, strict=True) -> list[ServiceCharge]:
    """The tally's shared service charges, frozen into FA_RECEIPT_SERVICE_POOL at
    the keeper's first final checklist. Inputs are the junction rows joined to
    their catalogs. Order: other services (when any), strip, stuffing, night
    stop, demurrage, entry, one row per crane service, transportation."""
    strip = derived_rows(strip, container_weights, excess_catalog)
    if strict:
        values = [r["price"] for group in (other, night, diamound, vehicle) for r in group]
        values += [strip_price(r) for r in strip]
        if any(to_decimal(v) is None or to_decimal(v) < 0 for v in values):
            raise ServiceTariffError("تعرفه خدمات انتخاب‌شده ناقص یا نامعتبر است")

    charges: list[ServiceCharge] = []
    total, count, present = _weighted_total([r["price"] for r in other],
                                            [r["number_service"] for r in other])
    if present:
        charges.append(ServiceCharge(SERVICE_LABELS["other_service"], count, total))
    groups = (
        ("strip", [strip_price(r) for r in strip if r["service_kind"] == "strip"],
         [None if r["pricing_type"] == "unloading" else r["number_service"]
          for r in strip if r["service_kind"] == "strip"]),
        ("stuffing", [strip_price(r) for r in strip if r["service_kind"] == "stuffing"],
         [None if r["pricing_type"] == "loading" else r["number_service"]
          for r in strip if r["service_kind"] == "stuffing"]),
        ("night_stop", [r["price"] for r in night], [r["number_service"] for r in night]),
        ("diamound", [r["price"] for r in diamound], [r["number_service"] for r in diamound]),
        ("vehicle_enter", [r["price"] for r in vehicle], [r["number_service"] for r in vehicle]),
    )
    for key, prices, counts in groups:
        total, count, _ = _weighted_total(prices, counts)
        charges.append(ServiceCharge(SERVICE_LABELS[key], count, total))
    for row in strip:
        if row["service_kind"] != "crane":
            continue
        rate = to_decimal(strip_price(row))
        quantity = to_decimal(row["number_service"]) or Decimal(1)
        charges.append(ServiceCharge(
            f'{SERVICE_LABELS["crane"]} — {row["rate_title"] or row["rate_code"]}',
            quantity, None if rate is None else rate * quantity))
    carriers = int(carrier_count or 0)
    if carriers:
        charges.append(ServiceCharge(SERVICE_LABELS["transportation"], carriers,
                                     Decimal(str(freight_rate or 0)) * carriers))
    return charges

CARGO_LABELS = {"weight": "وزنی", "volumetric": "حجمی", "container": "کانتینری"}
SHARE_STEP = Decimal("0.0001")

# Pool rows are frozen at the keeper's final checklist with these descriptions.
# Crane rows carry a suffix, so ranks match on the label prefix.
SERVICE_ORDER = tuple(SERVICE_LABELS[key] for key in (
    "strip", "stuffing", "crane", "transportation",
    "diamound", "vehicle_enter", "other_service", "night_stop",
))

SYSTEM_LABEL = "خدمات سیستمی"
TAX_LABEL = "مالیات بر ارزش افزوده"
INSURANCE_LABEL = "هزینه بیمه"
PREPAYMENT_LABEL = "کسر پیش‌پرداخت"
DISCOUNT_LABEL = "تخفیف"


@dataclass(frozen=True)
class InvoiceRow:
    kind: str
    description: str
    price: Decimal
    note: str
    quantity: Optional[Decimal] = None
    weight: Optional[Decimal] = None
    service_line: Optional[int] = None


def cargo_type(value) -> str:
    cargo = {"yes": "volumetric", "no": "weight"}.get(value, value)
    if cargo not in CARGO_LABELS:
        raise ValueError("نوع بار تالی (وزنی، حجمی یا کانتینری) مشخص نشده است")
    return cargo


def _dec(value) -> Decimal:
    return Decimal(0) if value is None else Decimal(str(value))


def _name(line) -> str:
    return str(line.get("hscode") or line.get("description") or f"ردیف {line.get('id')}").strip()


def _storage_label(line) -> str:
    return f"هزینه انبارداری کد کالای {line.get('kala_code')}"


def _location(line) -> sc.Location:
    try:
        return sc.location(line.get("zarib_mahal"))
    except ValueError as exc:
        raise ValueError(f"{_name(line)}: {exc}") from exc


def _single_rate(lines, message: str):
    """All lines must share one goods code and one location multiplier."""
    keys = {(line.get("goods_group"), _location(line).multiplier) for line in lines}
    if len(keys) != 1:
        raise ValueError(message)
    return lines[0], _location(lines[0])


def storage_rows(cargo: str, lines: list[dict], days: int, *, pallets=None,
                 container_weights: Optional[dict] = None) -> list[InvoiceRow]:
    """lines: the receipt's linked tally rows, with weight_kg and quantity already
    multiplied by this receipt's share of each row."""
    if not lines:
        raise ValueError("ردیف‌های اصلی تالی متعلق به این قبض را انتخاب کنید")

    if cargo == "weight":
        rows = []
        for line in lines:
            try:
                charge = sc.storage_charge("weight", rate=line.get("storage_price"),
                                           loc=_location(line), days=days,
                                           weight_kg=line.get("weight_kg"))
            except ValueError as exc:
                raise ValueError(f"{_name(line)}: {exc}") from exc
            rows.append(InvoiceRow("storage", _storage_label(line), charge.amount, charge.note,
                                   quantity=line.get("quantity"), weight=line.get("weight_kg")))
        return rows

    if cargo == "volumetric":
        line, loc = _single_rate(
            lines, "کالاهای این قبض کد کالا یا ضریب محل متفاوت دارند و تعداد پالت هر کدام مشخص نیست")
        charge = sc.storage_charge("volumetric", rate=line.get("storage_price"), loc=loc,
                                   days=days, pallets=pallets)
        return [InvoiceRow("storage", _storage_label(line), charge.amount, charge.note,
                           quantity=_dec(pallets))]

    if cargo == "container":
        groups: "OrderedDict[str, list[dict]]" = OrderedDict()
        for line in lines:
            hamel = str(line.get("number_hamel") or "").strip()
            if not hamel:
                raise ValueError(f"{_name(line)}: شماره حامل (کانتینر) ثبت نشده است")
            groups.setdefault(hamel, []).append(line)
        rows = []
        for hamel, group in groups.items():
            line, loc = _single_rate(
                group, f"کالاهای کانتینر {hamel} کد کالا یا ضریب محل متفاوت دارند")
            total = _dec((container_weights or {}).get(hamel))
            linked = sum((_dec(item.get("weight_kg")) for item in group), Decimal(0))
            if total <= 0:
                raise ValueError(f"وزن اظهار کانتینر {hamel} ثبت نشده است")
            if linked <= 0:
                raise ValueError(f"سهم وزنی این قبض از کانتینر {hamel} صفر است")
            share = Decimal(1) if linked >= total else (linked / total).quantize(SHARE_STEP)
            charge = sc.storage_charge("container", rate=line.get("storage_price"), loc=loc,
                                       days=days, containers=share)
            rows.append(InvoiceRow("storage",
                                   f"هزینه انبارداری کانتینر {hamel} (کد کالای {line.get('kala_code')})",
                                   charge.amount, charge.note, quantity=share))
        return rows

    raise ValueError("نوع بار تالی (وزنی، حجمی یا کانتینری) مشخص نشده است")


def service_rank(description) -> int:
    text = str(description or "")
    for index, label in enumerate(SERVICE_ORDER):
        if text.startswith(label):
            return index
    return len(SERVICE_ORDER)


def service_rows(allocated: list[dict], ratio) -> list[InvoiceRow]:
    """allocated: pool lines with line_no, description, total and this receipt's amount."""
    ratio = _dec(ratio)
    rows = []
    for item in sorted(allocated, key=lambda r: (service_rank(r["description"]), int(r["line_no"]))):
        amount, total = _dec(item["amount"]), _dec(item["total"])
        if ratio >= 1:
            note = "کل مبلغ خدمت"
        else:
            note = f"سهم این قبض از {sc.fmt(total)} (نسبت {sc.fmt(ratio.quantize(SHARE_STEP))})"
        rows.append(InvoiceRow("service", item["description"], amount, f"{note} = {sc.fmt(amount)}",
                               service_line=int(item["line_no"])))
    return rows


def insurance_row(value, cover: InsuranceCover, prior_receipts_value, days: int,
                  missing=()) -> Optional[InvoiceRow]:
    """value: this receipt's customs value. prior_receipts_value: customs value of
    the tally's receipts already invoiced; they used the tally's cover first.
    missing: names of linked rows without a customs value (counted as zero).

    Returns None only when the goods are fully covered and nothing is missing.
    """
    value, prior = _dec(value), _dec(prior_receipts_value)
    rate = sc.fmt(sc.INSURANCE_DAILY_RATE)
    missing_text = "، ".join(str(name) for name in missing)

    if value <= 0:
        # Nothing to price. Kept as a visible zero row; issuing also warns.
        return InvoiceRow("insurance", INSURANCE_LABEL, Decimal(0),
                          "ارزش گمرکی کالاهای این قبض در تالی ثبت نشده است؛ هزینه بیمه صفر ثبت شد"
                          + (f" (ردیف‌ها: {missing_text})" if missing_text else ""))
    missing_note = (f"؛ ارزش گمرکی ردیف‌های {missing_text} ثبت نشده و صفر حساب شد"
                    if missing_text else "")

    if not cover.insured or cover.missing_ceiling:
        if not cover.insured:
            basis = "بدون بیمه"
        else:
            policies = cover.policy_text or "بیمه‌نامه ثبت‌شده"
            basis = ("کل ارزش گمرکی قبض؛ تالی بیمه‌دار ثبت شده است "
                     f"({policies}) ولی ارزش کالای بیمه‌شده نه در ردیف‌های این تالی و نه در "
                     "تالی‌های هم‌بیمه‌نامه ثبت نشده است؛ چون سقف بیمه معلوم نیست، کل ارزش "
                     "گمرکی این قبض مبنای محاسبه قرار گرفت")
        charge = sc.insurance_charge(value, None, days)
        return InvoiceRow("insurance", INSURANCE_LABEL, charge.amount,
                          f"{sc.fmt(value)} × {rate} × {days} روز ({basis}{missing_note})"
                          f" = {sc.fmt(charge.amount)}")

    available = max(Decimal(0), cover.cover - prior)
    charge = sc.insurance_charge(value, available, days)
    if charge is None:
        if not missing_text:
            return None
        return InvoiceRow("insurance", INSURANCE_LABEL, Decimal(0),
                          f"تحت پوشش بیمه ({cover.policy_text}){missing_note}")
    parts = [f"ارزش گمرکی {sc.fmt(value)} − پوشش باقی‌مانده {sc.fmt(available)}",
             f"سقف بیمه‌نامه {sc.fmt(cover.ceiling)}",
             f"مصرف تالی‌های قبلی {sc.fmt(cover.used_before)}"]
    if prior > 0:
        parts.append(f"مصرف قبض‌های قبلی همین تالی {sc.fmt(min(prior, cover.cover))}")
    return InvoiceRow("insurance", INSURANCE_LABEL, charge.amount,
                      f"{sc.fmt(value - available)} × {rate} × {days} روز ({'؛ '.join(parts)}"
                      f"{missing_note}) = {sc.fmt(charge.amount)}")


def deduction_plan(*, is_general: bool, prepayment, discount, already_applied: bool,
                   answer: Optional[bool]) -> str:
    """none | apply | skip | ask.

    A tally's prepayment and discount are applied once. A general receipt takes
    them automatically; for detailed receipts the user is asked per receipt
    until one invoice takes them.
    """
    if already_applied or (_dec(prepayment) <= 0 and _dec(discount) <= 0):
        return "none"
    if is_general:
        return "apply"
    if answer is None:
        return "ask"
    return "apply" if answer else "skip"


def build_invoice(*, system_rate, storage: list[InvoiceRow], services: list[InvoiceRow],
                  tax_rate, prepayment=None, discount=None, apply_deductions=False,
                  receipt_label: str = "", insurance: Optional[InvoiceRow] = None):
    """Return (rows, totals). Deductions are stored as negative rows so the saved
    invoice total is the payable amount. Their notes name the receipt they were
    applied on, since a tally's prepayment and discount land on only one invoice."""
    system = _dec(system_rate)
    rows = [InvoiceRow("system", SYSTEM_LABEL, system,
                       f"مبلغ ثابت از تنظیمات = {sc.fmt(system)}")]
    rows += storage + services + ([insurance] if insurance else [])
    prepaid = _dec(prepayment) if apply_deductions else Decimal(0)
    off = _dec(discount) if apply_deductions else Decimal(0)
    totals = sc.invoice_totals([row.price for row in rows], tax_rate, prepaid, off)
    if totals.tax:
        rows.append(InvoiceRow("tax", TAX_LABEL, totals.tax,
                               f"{sc.fmt(totals.tax_rate)}٪ × {sc.fmt(totals.subtotal)} = {sc.fmt(totals.tax)}"))
    applied_on = f"، اعمال‌شده روی قبض {sc.ltr(receipt_label)}" if receipt_label else ""
    if prepaid > 0:
        rows.append(InvoiceRow("prepayment", PREPAYMENT_LABEL, -prepaid,
                               f"پیش‌پرداخت سربرگ تالی{applied_on} = {sc.fmt(prepaid)}"))
    if off > 0:
        rows.append(InvoiceRow("discount", DISCOUNT_LABEL, -off,
                               f"تخفیف سربرگ تالی{applied_on} = {sc.fmt(off)}"))
    if totals.payable < 0:
        raise ValueError("مجموع پیش‌پرداخت و تخفیف از مبلغ این صورتحساب بیشتر است")
    return rows, totals


def header_note(cargo: str, days: sc.BilledDays) -> str:
    return f"نوع بار: {CARGO_LABELS[cargo]}؛ {days.note}"
