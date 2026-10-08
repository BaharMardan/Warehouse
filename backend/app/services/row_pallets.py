"""Explicit pallet counts, keyed by tally detail rather than carrier number."""
from decimal import Decimal
from app.services import receipt_db as db

ROWS_SQL = '''SELECT d."ID_TALI_DETAILS" AS id, d."NUMBER_HAMEL" AS number_hamel,
    d."DESCRIPTION_KALA" AS description, d."HSCODE" AS hscode,
    d."ZARIB_MAHAL" AS zarib_mahal, d."ROW_PALLETS" AS pallets
    FROM "FA_TALI_DETAILES" d
    WHERE d."ID_HEADERS_TALI" = :tid AND d."IS_DELETED" = 'no'
    ORDER BY d."ID_TALI_DETAILS"'''


def validate_counts(rows, entries, *, expected=None, allocation=False):
    by_id = {int(r['id']): r for r in rows}
    values = {}
    for entry in entries:
        key = int(entry['tally_detail_id'])
        count = Decimal(str(entry['pallets']))
        if key not in by_id or key in values:
            raise ValueError('ردیف تالی نامعتبر یا تکراری است')
        if not count.is_finite() or count < 1 or count != count.to_integral_value():
            raise ValueError('تعداد پالت هر ردیف باید عدد صحیح و مثبت باشد')
        if allocation:
            row = by_id[key]
            available = Decimal(str(row.get('pallets') or 0)) - Decimal(str(row.get('used_pallets') or 0))
            if count > available:
                raise ValueError('تعداد پالت از مانده قابل تخصیص ردیف بیشتر است')
        values[key] = int(count)
    if not values or set(values) != set(by_id):
        raise ValueError('تعداد پالت تمام ردیف‌های کالا را مشخص کنید')
    total = sum(values.values())
    if expected is not None and total != Decimal(str(expected)):
        raise ValueError('جمع پالت ردیف‌ها باید با تعداد پالت ثبت‌شده برابر باشد')
    if total > 100000:
        raise ValueError('جمع تعداد پالت نباید بیشتر از ۱۰۰۰۰۰ باشد')
    return values


def tally_rows(cur, tid):
    return db.rows(cur, ROWS_SQL, {'tid': tid})


def complete_total(rows):
    if not rows or any(r.get('pallets') is None for r in rows):
        return None
    return sum(int(r['pallets']) for r in rows)


def allocations(cur, rid):
    return db.rows(cur, '''SELECT "TALLY_DETAIL_ID" AS tally_detail_id, "PALLETS" AS pallets
        FROM "FA_RECEIPT_PALLETS" WHERE "RECEIPT_ID" = :rid''', {'rid': rid})


def receipt_rows(cur, current, selected_ids):
    rows = tally_rows(cur, current['tally_id'])
    used = {int(r['id']): r['pallets'] for r in db.rows(cur, '''
        SELECT p."TALLY_DETAIL_ID" AS id, SUM(p."PALLETS") AS pallets
        FROM "FA_RECEIPT_PALLETS" p
        JOIN "fa_ghabz_anbar_header" h ON h."ID_ghabz" = p."RECEIPT_ID"
        WHERE h."TALI_ID" = :tid AND h."IS_DELETED" = 'no'
          AND NVL(h."IS_MASTER", 'no') = 'no' AND h."ID_ghabz" <> :rid
        GROUP BY p."TALLY_DETAIL_ID"''', {'tid': current['tally_id'], 'rid': current['id']})}
    saved = {int(r['tally_detail_id']): r['pallets'] for r in allocations(cur, current['id'])}
    return [{**r, 'used_pallets': used.get(int(r['id']), 0),
             'selected_pallets': saved.get(int(r['id']))}
            for r in rows if int(r['id']) in selected_ids]


def validate_receipt(cur, current, selected_ids):
    rows = receipt_rows(cur, current, selected_ids)
    return validate_counts(rows, allocations(cur, current['id']),
                           expected=current['pallet_quantity'], allocation=True)


def automatic_counts(rows, sources, expected):
    """Reuse complete tally rows; infer a partial row only if its count is unique.

    Never prorate pallets by declared weight or package count. The receipt total
    can determine one remaining row, or all remaining stock, without guessing.
    """
    if not expected:
        raise ValueError('ابتدا تعداد پالت قبض تفکیکی را در اطلاعات قبض ثبت کنید')
    by_id = {int(r['id']): r for r in sources}
    counts, partial = {}, []
    for row in rows:
        sid = int(row['id'])
        source = by_id.get(sid)
        if row.get('pallets') is None or source is None:
            raise ValueError('ابتدا تعداد پالت ردیف‌های تالی را تکمیل کنید')
        shares = [Decimal(str(source[key + '_share'])) for key in ('quantity', 'weight', 'baskol')
                  if Decimal(str(source.get(key) or 0)) > 0]
        if shares and all(abs(share - 1) <= Decimal('0.000001') for share in shares):
            counts[sid] = int(row['pallets'])
        else:
            partial.append(row)
    remaining = Decimal(str(expected)) - sum(counts.values())
    if len(partial) == 1:
        counts[int(partial[0]['id'])] = remaining
    elif partial:
        available = {int(r['id']): Decimal(str(r['pallets'])) - Decimal(str(r.get('used_pallets') or 0))
                     for r in partial}
        if sum(available.values()) != remaining:
            raise ValueError('قبض شامل بخشی از چند ردیف است؛ سهم پالت این ردیف‌ها از اطلاعات تالی مشخص نیست')
        counts.update(available)
    return validate_counts(rows, [{'tally_detail_id': k, 'pallets': v} for k, v in counts.items()],
                           expected=expected, allocation=True)


def resolve_counts(rows, sources, expected, saved):
    if saved:
        return validate_counts(rows, saved, expected=expected, allocation=True)
    return automatic_counts(rows, sources, expected)


def ensure_receipt_counts(cur, current, sources):
    """Called inside the tally-locked finalize/issue transaction; retry-safe."""
    selected = [r for r in sources if any(r[k + '_share'] for k in ('quantity', 'weight', 'baskol'))]
    rows = receipt_rows(cur, current, {int(r['id']) for r in selected})
    saved = allocations(cur, current['id'])
    counts = resolve_counts(rows, selected, current['pallet_quantity'], saved)
    if not saved:
        cur.executemany('''INSERT INTO "FA_RECEIPT_PALLETS" ("RECEIPT_ID", "TALLY_DETAIL_ID", "PALLETS")
            VALUES (:rid, :id, :pallets)''',
            [{'rid': current['id'], 'id': k, 'pallets': v} for k, v in counts.items()])
    return counts
