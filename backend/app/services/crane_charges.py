"""Crane tariffs from goods-group full-container unloading and excess weight, per physical container."""
from decimal import Decimal, InvalidOperation, ROUND_CEILING

CRANE_CATALOG_SQL = """
SELECT "id_kala_price" AS id, "CODE" AS code, "goods_group" AS title,
       "price_unloding" AS unloading, "price_loading" AS loading
FROM "fa_kala_price"
WHERE "CODE" IN ('118', '119', '120', '121') AND "IS_DELETED" = 'no'
"""
RULES = {"118": (10000, "119"), "120": (15000, "121")}
LEGACY = {"201": "118", "401": "120"}


def crane_rows(rows, weights, catalog):
    result = []
    for row in rows:
        if row.get("service_kind") != "crane":
            result.append(row)
            continue
        code = str(row.get("code") or row.get("rate_code") or "")
        code = LEGACY.get(code, code)
        if code not in RULES:
            raise ValueError("اندازه کانتینر جرثقیل را دوباره انتخاب کنید")
        capacity, excess_code = RULES[code]
        weight = Decimal(str(weights.get(row.get("number_hamel"), 0)))
        if not weight.is_finite() or weight < 0:
            raise ValueError("وزن کانتینر جرثقیل معتبر نیست")
        excess = max(Decimal(0), (weight - capacity) / 1000).to_integral_value(rounding=ROUND_CEILING)
        parts = [(code, Decimal(1), "unloading", None)]
        if excess:
            parts.append((excess_code, excess, "unloading", "excess"))
        for tariff_code, quantity, field, derived in parts:
            tariff = catalog.get(tariff_code)
            try:
                price = Decimal(str(tariff[field])) if tariff else Decimal("NaN")
            except (InvalidOperation, TypeError):
                price = Decimal("NaN")
            if not price.is_finite() or price < 0:
                raise ValueError(f"نرخ تخلیه/بارگیری کد گروه کالای {tariff_code} ثبت نشده یا نامعتبر است")
            result.append({
                **row, "id": row["id"] if derived is None else -int(row["id"]) * 10 - 1,
                "parent_service_id": row["id"] if derived else None,
                "is_auto_excess": derived == "excess", "is_auto_empty": False,
                "code": tariff_code, "rate_code": tariff_code, "rate_title": tariff["title"],
                "rate_id": None, "pricing_type": "normal", "number_service": quantity,
                "normal": price, "non_standard": price, "dangerous": price,
                "calculated_amount": price * quantity,
            })
    return result
