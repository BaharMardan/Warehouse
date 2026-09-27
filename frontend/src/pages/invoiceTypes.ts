import { toJalaali } from 'jalaali-js'

export type InvoiceHeader = {
  id_sorat: number; created_at: string | null; seller_name: string | null
  seller_address: string | null; seller_phone: string | null
  seller_economic_code: string | null; seller_national_id: string | null; seller_postal_code: string | null
  buyer_id: number | null; buyer_name: string | null; buyer_address: string | null
  buyer_phone: string | null; buyer_economic_code: string | null
  buyer_national_id: string | null; buyer_postal_code: string | null
  buyer_kotath_code: string | null; buyer_ghabz_number: string | null
  description: string | null; manager_name: string | null; finance_name: string | null
  representative_name: string | null; tali_id: number | null; tali_number: string | null
  ghabz_id: number | null; is_accepted: string | null
  // 1405 invoices only: cargo type and day count, and the receipt's number.
  calc_note?: string | null; ghabz_number?: string | null
}
export type InvoiceLine = {
  id_detail: number; description: string | null; quantity: number | null
  weight: number | null; price: string | null; discount: string | null; amount: string | null
  // 1405 invoices only; NULL on legacy invoices.
  row_kind?: RowKind | null; calc_note?: string | null
}
export type RowKind = 'system' | 'storage' | 'service' | 'insurance' | 'tax' | 'prepayment' | 'discount'
export type SavedInvoice = { header: InvoiceHeader; details: InvoiceLine[]; grand_total: string }
export type InvoiceListRow = Pick<InvoiceHeader, 'id_sorat' | 'created_at' | 'seller_name' | 'buyer_id' | 'buyer_name' | 'tali_id' | 'tali_number' | 'ghabz_id' | 'is_accepted'> & { grand_total: string | null }

export const money = (value: string | number | null | undefined) =>
  value == null ? '—' : Number(value).toLocaleString('en-US', { maximumFractionDigits: 2 })

export function jalali(iso: string | null) {
  if (!iso) return '—'
  const [year, month, day] = iso.slice(0, 10).split('-').map(Number)
  if (!year || !month || !day) return '—'
  const { jy, jm, jd } = toJalaali(year, month, day)
  return `${jy}/${String(jm).padStart(2, '0')}/${String(jd).padStart(2, '0')}`
}

// Rows of a 1405 invoice carry a kind: charges go in the table, VAT and the
// prepayment/discount (stored as negative rows) go in the summary under it.
// Legacy invoices have no kinds and keep their original single-table layout.
const CHARGE_KINDS: RowKind[] = ['system', 'storage', 'service', 'insurance']

const net = (line: InvoiceLine) => Number(line.price ?? 0) - Number(line.discount ?? 0)

export function invoiceSections(details: InvoiceLine[]) {
  const modern = details.some((line) => line.row_kind != null)
  const charges = modern
    ? details.filter((line) => line.row_kind == null || CHARGE_KINDS.includes(line.row_kind))
    : details
  const summary = details.filter((line) => line.row_kind != null && !CHARGE_KINDS.includes(line.row_kind))
  return {
    modern,
    charges,
    subtotal: charges.reduce((total, line) => total + net(line), 0),
    summary,
  }
}

/** A deduction row is stored negative; show it as a positive amount with a minus sign. */
export const signedMoney = (value: string | number | null | undefined) =>
  value == null ? '—' : Number(value) < 0 ? `− ${money(Math.abs(Number(value)))}` : money(value)

export const quantity = (value: number | string | null | undefined) =>
  value == null ? '—' : Number(value).toLocaleString('en-US', { maximumFractionDigits: 4 })
