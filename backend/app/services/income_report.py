"""Income report over saved invoice rows. DB-free, so the rules are unit-tested.

Every saved invoice row belongs to one income category. Rows carry a kind
(system, storage, service, insurance, discount, tax, prepayment); service rows
are told apart by the description the invoice stored, using the same labels the
invoice builder writes (receipt_invoice.SERVICE_LABELS, invoice_handling.LABELS).
Older invoices have no kind; their descriptions are recognised by keyword.

Amounts are what the invoice shows: price minus line discount. Rows whose amount
is zero are left out, exactly as the invoice screens do.
"""
import re
from collections import OrderedDict
from decimal import Decimal

from app.services.invoice_handling import handling_labels
from app.services.receipt_invoice import SERVICE_LABELS

# (key, label, section). "charge" categories add up to the gross income;
# "adjustment" categories are the discount, VAT and prepayment rows.
CATEGORIES = (
    ("system", "خدمات سیستمی", "charge"),
    ("storage", "انبارداری", "charge"),
    ("strip", "استریپ", "charge"),
    ("unloading", "تخلیه", "charge"),
    ("stuffing", "استافینگ", "charge"),
    ("loading", "بارگیری", "charge"),
    ("crane", "جابه‌جایی کانتینر با جرثقیل", "charge"),
    ("transportation", "باربری", "charge"),
    ("demurrage", "دیماند", "charge"),
    ("vehicle_enter", "حق ورودی (حق محوطه)", "charge"),
    ("night_stop", "توقف شبانه", "charge"),
    ("other_service", "سایر خدمات", "charge"),
    ("insurance", "بیمه", "charge"),
    ("other", "سایر / طبقه‌بندی‌نشده", "charge"),
    ("discount", "تخفیف", "adjustment"),
    ("tax", "مالیات بر ارزش افزوده", "adjustment"),
    ("prepayment", "کسر پیش‌پرداخت", "adjustment"),
)
CATEGORY_LABELS = {key: label for key, label, _ in CATEGORIES}
SECTION = {key: section for key, _, section in CATEGORIES}

# Strip with unloading (stuffing with loading) saved as one row by older invoices.
# Their amount cannot be split, so these rows are left out of the report entirely;
# new invoices save each service as its own row (receipt_invoice.service_charges).
COMBINED = "combined"

_DIRECT_KINDS = {"system", "storage", "insurance", "discount", "tax", "prepayment"}


def _normalize(description) -> str:
    """Drop the «هزینه» / «کل» lead-ins the labels carry, so 'هزینه کل دیماند' and 'دیماند' match."""
    text = str(description or "").replace("ي", "ی").replace("ك", "ک").strip()
    text = re.sub(r"^هزینه(?:‌ی|ٔ|ی)?\s*", "", text)
    return re.sub(r"^کل\s+", "", text).strip()


_SERVICE_PREFIXES = tuple(
    (_normalize(SERVICE_LABELS[label_key]), category) for label_key, category in (
        ("crane", "crane"),
        ("transportation", "transportation"),
        ("diamound", "demurrage"),
        ("vehicle_enter", "vehicle_enter"),
        ("night_stop", "night_stop"),
        ("other_service", "other_service"),
    )
)
_HANDLING = {
    frozenset({"استریپ"}): "strip",
    frozenset({"تخلیه"}): "unloading",
    frozenset({"استریپ", "تخلیه"}): COMBINED,
    frozenset({"استافینگ"}): "stuffing",
    frozenset({"بارگیری"}): "loading",
    frozenset({"استافینگ", "بارگیری"}): COMBINED,
}
_HANDLING_TEXT = {
    "استریپ / تخلیه": COMBINED,
    "استافینگ / بارگیری": COMBINED,
    "استریپ و استافینگ": COMBINED,
}


def classify_row(row_kind, description) -> str:
    """The income category key of one invoice row."""
    if row_kind in _DIRECT_KINDS:
        return row_kind
    text = _normalize(description)
    labels = handling_labels(text)
    if labels:
        # A label set that mixes both groups (strip with stuffing) is an old, unsplit row.
        return _HANDLING.get(frozenset(labels), COMBINED)
    if text in _HANDLING_TEXT:
        return _HANDLING_TEXT[text]
    for prefix, category in _SERVICE_PREFIXES:
        if text.startswith(prefix):
            return category
    if row_kind == "service":
        return "other_service"
    # Invoices from before row kinds existed.
    if text.startswith("انبارداری") or text.startswith("کد کالای"):
        return "storage"
    if text.startswith("بیمه"):
        return "insurance"
    if text.startswith("تخفیف"):
        return "discount"
    if text.startswith("مالیات"):
        return "tax"
    return "other"


def to_decimal(value) -> Decimal:
    return Decimal(0) if value is None else Decimal(str(value))


def _with_categories(rows) -> list[dict]:
    result = []
    for row in rows:
        amount = to_decimal(row.get("amount"))
        if amount == 0:
            continue
        result.append({**row, "amount": amount,
                       "category": classify_row(row.get("row_kind"), row.get("description"))})
    return result


def classified(rows) -> list[dict]:
    """Rows with their category, amounts as Decimal. Zero-amount rows and old
    combined strip/unloading and stuffing/loading rows are removed."""
    return [line for line in _with_categories(rows) if line["category"] != COMBINED]


def summarize(rows) -> dict:
    """Per-category totals and the grand totals for already-fetched invoice rows."""
    everything = _with_categories(rows)
    lines = [line for line in everything if line["category"] != COMBINED]
    left_out = [line for line in everything if line["category"] == COMBINED]
    buckets = OrderedDict((key, {"lines": 0, "invoices": set(), "amount": Decimal(0)})
                          for key, _, _ in CATEGORIES)
    for line in lines:
        bucket = buckets[line["category"]]
        bucket["lines"] += 1
        bucket["invoices"].add(line["invoice_id"])
        bucket["amount"] += line["amount"]

    def total(key):
        return buckets[key]["amount"]

    gross = sum((b["amount"] for key, b in buckets.items() if SECTION[key] == "charge"), Decimal(0))
    discount, tax, prepayment = -total("discount"), total("tax"), -total("prepayment")
    net = gross - discount
    summary = {
        "gross": gross,                  # all charges, before discount
        "discount": discount,
        "net": net,                      # income before VAT
        "tax": tax,
        "total_with_tax": net + tax,
        "prepayment": prepayment,
        "payable": net + tax - prepayment,
    }
    categories = [{
        "key": key, "label": CATEGORY_LABELS[key], "section": SECTION[key],
        "lines": bucket["lines"], "invoices": len(bucket["invoices"]),
        "amount": bucket["amount"],
    } for key, bucket in buckets.items()]
    # Remaining-cargo invoices supplement an original invoice; they are real income of
    # their own issue date, shown apart so they are not mistaken for double counting.
    supplementary = [line for line in lines if line.get("original_invoice_id") is not None]
    return {"invoice_count": len({line["invoice_id"] for line in lines}),
            "categories": categories, "summary": summary,
            "supplementary": {"invoices": len({line["invoice_id"] for line in supplementary}),
                              "amount": sum((line["amount"] for line in supplementary), Decimal(0))},
            # Not in any figure above; reported so the omission is visible.
            "left_out": {"lines": len(left_out),
                         "amount": sum((line["amount"] for line in left_out), Decimal(0))}}


def summarize_cancelled(rows) -> dict:
    """Invoices issued in the period and cancelled since. They are not income."""
    invoices = [{**row, "amount": to_decimal(row.get("amount"))} for row in rows]
    return {"count": len(invoices),
            "amount": sum((row["amount"] for row in invoices), Decimal(0)),
            "invoices": invoices}
