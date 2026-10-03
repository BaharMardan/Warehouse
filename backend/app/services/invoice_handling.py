"""Handling labels and presentation-only merging; saved monetary rows stay intact."""
from decimal import Decimal

LABELS = {"strip": "استریپ", "stuffing": "استافینگ", "unloading": "تخلیه", "loading": "بارگیری"}
LEGACY = {"هزینه کل استریپ / تخلیه": "strip", "هزینه کل استافینگ / بارگیری": "stuffing",
          "استریپ / تخلیه": "strip", "استافینگ / بارگیری": "stuffing"}


def selected_labels(rows, kind):
    return list(dict.fromkeys(
        LABELS[r.get("pricing_type")] if r.get("pricing_type") in ("unloading", "loading") else LABELS[kind]
        for r in rows if r.get("service_kind") == kind))


def handling_labels(description):
    parts = (description or "").split(" و ")
    return parts if parts and all(p in LABELS.values() for p in parts) else []


def merge_handling(details, selections=()):
    result, combined, names = [], None, []
    for original in details:
        row = dict(original)
        description = row.get("description") or ""
        labels = handling_labels(description)
        if description in LEGACY:
            labels = selected_labels(selections, LEGACY[description])
        if row.get("row_kind") not in (None, "service") or not labels:
            result.append(row)
            continue
        net = Decimal(str(row.get("price") or 0)) - Decimal(str(row.get("discount") or 0))
        if not net:
            result.append(row)
            continue
        names.extend(label for label in labels if label not in names)
        if combined is None:
            combined = row
            combined["quantity"] = None
            combined["weight"] = None
            result.append(combined)
        else:
            for field in ("price", "discount", "amount"):
                values = (combined.get(field), row.get(field))
                combined[field] = (sum((Decimal(str(v)) for v in values if v is not None), Decimal(0))
                                   if any(v is not None for v in values) else None)
            combined["calc_note"] = "؛ ".join(filter(None, (combined.get("calc_note"), row.get("calc_note"))))
        combined["description"] = " و ".join(names)
    return result
