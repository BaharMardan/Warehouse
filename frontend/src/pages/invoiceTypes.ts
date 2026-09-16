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
}
export type InvoiceLine = {
  id_detail: number; description: string | null; quantity: number | null
  weight: number | null; price: string | null; discount: string | null; amount: string | null
}
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
