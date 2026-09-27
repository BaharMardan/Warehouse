"""Receipt allocation uses original tally weights or keeper-recorded pallets."""
from decimal import Decimal, ROUND_HALF_UP

EPS = Decimal("0.000001")
ONE = Decimal(1)


def decimal(value):
    return Decimal(0) if value is None else Decimal(str(value))


def allocation_ratio(is_general, cargo_type, selected_weight, total_weight, pallets, total_pallets):
    if is_general:
        return ONE
    if cargo_type in ("volumetric", "yes"):
        numerator, denominator = decimal(pallets), decimal(total_pallets)
    elif cargo_type in ("weight", "no", "container"):
        numerator, denominator = decimal(selected_weight), decimal(total_weight)
    else:
        raise ValueError("روش تخصیص هزینه برای این نوع بار مشخص نشده است")
    if not numerator.is_finite() or not denominator.is_finite() or denominator <= 0 or numerator <= 0:
        raise ValueError("وزن یا تعداد پالت قبض و مقدار کل تالی باید مثبت و ثبت‌شده باشد")
    if numerator > denominator + EPS:
        raise ValueError("سهم قبض از کل بار تالی بیشتر است")
    return min(ONE, numerator / denominator)


def allocated_amount(total, ratio, previous_ratio=0, previous_amount=0):
    """Cumulative rounding in whole rials prevents drift and duplicate allocation."""
    total, ratio = decimal(total), decimal(ratio)
    previous_ratio, previous_amount = decimal(previous_ratio), decimal(previous_amount)
    cumulative = previous_ratio + ratio
    if ratio <= 0 or cumulative > ONE + EPS or total < 0:
        raise ValueError("جمع سهم قبض‌ها از کل هزینه تالی بیشتر است")
    target = (total * min(ONE, cumulative)).quantize(ONE, rounding=ROUND_HALF_UP)
    return target - previous_amount
