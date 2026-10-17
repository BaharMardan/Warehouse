"""Uninvoiced stock on aging tallies. No database or HTTP dependencies.

Source shares identify modern receipts exactly. Legacy receipts without links
consume the remaining amounts once per receipt/HS, in original tally-row order.
An invoice supplements a receipt's charges; it never consumes its stock twice.
"""
from collections import defaultdict
from decimal import Decimal

ZERO = Decimal(0)
EPS = Decimal("0.000001")
FIELDS = ("weight", "quantity", "baskol")


def number(value):
    return ZERO if value is None else Decimal(str(value))


def attach_remaining_goods(items, rows):
    by_tally = {item["id"]: item for item in items}
    goods_by_key = {}
    base, remaining = {}, {}
    by_hs = defaultdict(list)
    paid, exact, legacy = set(), set(), {}
    for item in items:
        item["goods"] = []
    for row in rows:
        if row["tally_id"] not in by_tally:
            continue
        key = (row["tally_id"], row["detail_id"])
        hs = (row.get("hscode") or "").strip().upper()
        if key not in goods_by_key:
            goods_by_key[key] = {name: row.get(name) for name in
                ("detail_id", "hscode", "description", "customs_value", "remaining_weight")}
            goods_by_key[key]["receipts"] = []
            base[key] = {"weight": max(ZERO, number(row.get("remaining_weight"))),
                         "quantity": max(ZERO, number(row.get("quantity"))),
                         "baskol": max(ZERO, number(row.get("baskol")))}
            remaining[key] = dict(base[key])
            by_hs[(row["tally_id"], hs)].append(key)
        goods = goods_by_key[key]
        rid = row.get("receipt_id")
        if rid is None:
            continue
        if row.get("invoiced") != 1:
            if not any(receipt["id"] == rid for receipt in goods["receipts"]):
                goods["receipts"].append({"id": rid, "number": row.get("receipt_number")})
            continue
        paid.add(key)
        if row.get("source_detail_id") is not None:
            pair = (rid, key)
            if pair not in exact:
                exact.add(pair)
                for field in FIELDS:
                    share = min(Decimal(1), max(ZERO, number(row.get(field + "_share"))))
                    remaining[key][field] = max(ZERO, remaining[key][field] - base[key][field] * share)
        else:
            legacy[(row["tally_id"], rid, hs)] = {
                field: max(ZERO, number(row.get("receipt_" + field))) for field in FIELDS}
    # Exact links take priority. Older unlinked receipts consume the same HS
    # in tally-row order, without deducting their full weight from every row.
    for (tid, rid, hs), wanted in sorted(legacy.items()):
        for key in sorted(by_hs[(tid, hs)], key=lambda pair: pair[1]):
            for field in FIELDS:
                consumed = min(remaining[key][field], wanted[field])
                remaining[key][field] -= consumed
                wanted[field] -= consumed
    tallies_with_goods = set()
    for key, goods in goods_by_key.items():
        tid, _ = key
        tallies_with_goods.add(tid)
        primary = next((field for field in FIELDS if base[key][field] > EPS), None)
        if primary is not None and remaining[key][primary] <= EPS:
            continue
        if primary is None and key in paid:
            continue
        if goods["remaining_weight"] is not None:
            goods["remaining_weight"] = remaining[key]["weight"]
        by_tally[tid]["goods"].append(goods)
    # Preserve empty/unfinished tallies, but remove a tally whose goods have
    # all been covered by active invoices. Cancelled invoices restore stock.
    return [item for item in items if item["goods"] or item["id"] not in tallies_with_goods]
