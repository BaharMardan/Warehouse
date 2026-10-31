"""Present physical non-customs balances using the shared stock report schema."""
from collections import OrderedDict
from decimal import Decimal
from app.services import stock_report as sr


def build_rows(items):
    # A tally row can be allocated to multiple invoiced receipts. Merge physical
    # balances before counting its container or applying its original value.
    merged = OrderedDict()
    for item in items:
        key = (item["tally_id"], item["source_id"])
        if key not in merged:
            merged[key] = {**item, "weight": Decimal(0), "quantity": Decimal(0), "pallets": Decimal(0)}
        for field in ("weight", "quantity", "pallets"):
            merged[key][field] += sr.dec(item.get(field))
    rows = []
    for item in merged.values():
        bases = (("pallets", "original_pallets"), ("weight", "original_weight"), ("quantity", "original_quantity"))
        if item.get("cargo") not in sr.VOLUMETRIC:
            bases = (bases[1], bases[2], bases[0])
        ratio = next((item[field] / sr.dec(item[original]) for field, original in bases
                      if sr.dec(item.get(original)) > 0), Decimal(0))
        ratio = min(Decimal(1), max(Decimal(0), ratio))
        location, label = sr.location_of(item.get("zarib_mahal"))
        row = {field: item.get(field) for field in ("tally_id", "tally_number", "owner_id",
               "hscode", "description", "package_type", "anbar_id", "tagh_name", "carrier",
               "container_type", "container_number", "insurance_company", "policy_numbers")}
        row.update(detail_id=item["source_id"], unloaded_at=sr._day(item.get("unloaded_at")),
            cargo_type=item.get("cargo"), owner_name=item.get("owner_name") or sr.UNKNOWN,
            anbar_name=item.get("anbar_name") or sr.UNKNOWN, location=location, location_label=label,
            containers=int(bool(item.get("container_type") or item.get("container_number"))),
            remaining_ratio=ratio, weight=item["weight"], quantity=item["quantity"], pallets=item["pallets"],
            baskol=sr.dec(item.get("original_baskol")) * ratio,
            customs_value=sr.dec(item.get("original_customs_value")) * ratio,
            insured_value=sr.tally_insured_value(item.get("is_insured"), item.get("insured_ceiling")),
            is_insured=item.get("is_insured"), insurance_expiry=sr._day(item.get("insurance_expiry")))
        rows.append(row)
    return rows
