"""Read-only expansion of stored HS groups into allocated original tally rows."""
from decimal import Decimal
from app.services.ghabz_allotment import normalize_hscode

MEASURES = {'number_kala': 'quantity_share', 'weighte_asnad': 'weight_share',
            'weighte_baskol': 'baskol_share'}
EPS = Decimal('0.000001')


def separate_lines(grouped, sources, selections):
    """None selections means a master receipt; children require explicit shares.

    Refuse mismatched source data rather than changing any saved receipt total.
    Parent identities remain available, but source_row_id identifies display rows.
    """
    parents = {normalize_hscode(row.get('hscode')): row for row in grouped}
    shares = None if selections is None else {int(row['id']): row for row in selections}
    totals = {key: {field: Decimal(0) for field in MEASURES} for key in parents}
    result = []
    for source in sources:
        key = normalize_hscode(source.get('hscode'))
        if key not in parents:
            continue
        sid = int(source['id'])
        allocation = {share: Decimal(1) for share in MEASURES.values()} if shares is None else shares.get(sid)
        if allocation is None:
            continue
        fractions = {share: Decimal(str(allocation.get(share) or 0)) for share in MEASURES.values()}
        if any(not fraction.is_finite() or not Decimal(0) <= fraction <= Decimal(1)
               for fraction in fractions.values()):
            raise ValueError('Invalid source allocation')
        if not any(fraction > 0 for fraction in fractions.values()):
            continue
        values = {}
        for field, share in MEASURES.items():
            fraction = fractions[share]
            values[field] = Decimal(str(source.get(field) or 0)) * fraction
            totals[key][field] += values[field]
        row = dict(parents[key])
        for field in ('code_kala', 'goods_group_code', 'description_kala', 'type_basteh',
                      'id_tagh_anbar', 'tagh_name', 'number_hamel'):
            row[field] = source.get(field)
        carrier = str(source.get('number_hamel') or '').strip()
        row.update(values, source_row_id=sid, hscode=key,
                   carriers=[carrier] if carrier else [], number_kantiner=None, code_kala_kantiner=None)
        result.append(row)
    for key, parent in parents.items():
        for field in MEASURES:
            if abs(totals[key][field] - Decimal(str(parent.get(field) or 0))) > EPS:
                raise ValueError('Source allocation does not match saved receipt totals')
    return result
