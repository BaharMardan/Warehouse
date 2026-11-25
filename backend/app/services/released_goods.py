"""Released original goods, scoped to invoice issue dates and receipt shares."""
from decimal import Decimal
from app.services.stock_report import location_of, tally_insured_value


def dec(value):
    return Decimal(str(value or 0))


def build_report(inputs):
    rows, seen, tallies, invoices = [], set(), set(), set()
    totals = dict(weight=Decimal(0), pallets=Decimal(0), customs_value=Decimal(0),
                  insured_value=Decimal(0), insurance_unknown=0, pallets_estimated=0, pallets_missing=0)
    for item in inputs:
        identity = (item['invoice_id'], item['detail_id'])
        if identity in seen:
            continue
        seen.add(identity)
        tid = item['tally_id']
        ratio = dec(item.get('weight_share'))
        master = item.get('is_master') == 'yes'
        if dec(item.get('weight')) > 0:
            value_ratio = ratio
        elif master:
            value_ratio = Decimal(1)
        elif dec(item.get('row_pallets')) > 0 and item.get('receipt_pallets') is not None:
            value_ratio = dec(item['receipt_pallets']) / dec(item['row_pallets'])
        elif dec(item.get('quantity')) > 0:
            value_ratio = dec(item.get('quantity_share'))
        elif dec(item.get('tally_pallets')) > 0 and dec(item.get('pallet_quantity')) > 0:
            value_ratio = dec(item['pallet_quantity']) / dec(item['tally_pallets'])
        else:
            value_ratio = dec(item.get('quantity_share'))
        exact = item.get('row_pallets') if master else item.get('receipt_pallets')
        estimated = not master and exact is None and item.get('row_pallets') is not None
        pallets = dec(exact) if exact is not None else (
            dec(item['row_pallets']) * value_ratio if estimated else None)
        insured = tally_insured_value(item.get('is_bimeh'), item.get('insured_value'))
        first = tid not in tallies
        if first:
            totals['insured_value'] += insured or Decimal(0)
            totals['insurance_unknown'] += int(insured is None)
        location = location_of(item.get('zarib_mahal'))[1]
        result = {**item, 'weight': dec(item.get('weight')) * ratio,
                  'quantity': dec(item.get('quantity')) * dec(item.get('quantity_share')),
                  'pallets': pallets, 'pallets_estimated': estimated,
                  'customs_value': dec(item.get('customs_value')) * value_ratio,
                  'insured_value': insured if first else None, 'insurance_first': first,
                  'location_label': location}
        for field in ('weight', 'pallets', 'customs_value'):
            totals[field] += result[field] or Decimal(0)
        totals['pallets_estimated'] += int(estimated)
        totals['pallets_missing'] += int(pallets is None)
        rows.append(result)
        tallies.add(tid)
        invoices.add(item['invoice_id'])
    totals.update(tallies=len(tallies), invoices=len(invoices), rows=len(rows))
    return {'rows': rows, 'totals': totals}
