"""JSON-friendly values for report responses."""
from datetime import date, datetime
from decimal import Decimal


def number(value):
    """int when whole, else a float rounded to 4 places (rial totals stay exact)."""
    if value is None:
        return None
    value = Decimal(value)
    return int(value) if value == value.to_integral_value() else round(float(value), 4)


def serializable(value):
    """Decimal -> number and dates -> ISO text, recursively."""
    if isinstance(value, Decimal):
        return number(value)
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, date):
        return value.isoformat()
    if isinstance(value, dict):
        return {key: serializable(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [serializable(item) for item in value]
    return value
