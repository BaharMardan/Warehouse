import { keepPreviousData, useQuery } from '@tanstack/react-query'
import { apiGet } from './client'

export type IncomeCategory = {
  key: string; label: string; section: 'charge' | 'adjustment'
  lines: number; invoices: number; amount: number
}
export type IncomeTotals = {
  gross: number; discount: number; net: number; tax: number
  total_with_tax: number; prepayment: number; payable: number
}
export type CancelledInvoice = {
  invoice_id: number; issued_at: string | null; cancelled_at: string | null
  tally_id: number | null; tally_number: string | null; receipt_number: string | null
  buyer_name: string | null; amount: number; reissued: number
}
export type IncomeSummary = {
  from: string; to: string; invoice_count: number
  categories: IncomeCategory[]; summary: IncomeTotals
  supplementary: { invoices: number; amount: number }
  left_out: { lines: number; amount: number }
  cancelled: { count: number; amount: number; invoices: CancelledInvoice[] }
}
export type IncomeLine = {
  invoice_id: number; issued_at: string | null; tally_id: number | null; tally_number: string | null
  receipt_number: string | null; buyer_name: string | null; line_id: number
  description: string | null; quantity: number | null; weight: number | null
  amount: number; category: string; category_label: string
}
export type IncomeLines = {
  from: string; to: string; category: string | null; total: number
  truncated: boolean; lines: IncomeLine[]
}

export type StockGroupBy = 'hscode' | 'owner' | 'anbar' | 'location' | 'tally' | 'none'

export type StockRow = {
  tally_id: number; tally_number: string | null; detail_id: number; unloaded_at: string | null
  cargo_type: string | null; owner_id: number | null; owner_name: string
  hscode: string | null; description: string | null; package_type: string | null
  anbar_id: number | null; anbar_name: string; tagh_name: string | null
  location: string; location_label: string
  carrier: string | null; container_type: string | null; container_number: string | null
  containers: number; remaining_ratio: number
  weight: number; baskol: number; quantity: number; pallets: number | null
  customs_value: number
  insured_value: number | null
  is_insured: string | null; insurance_company: string | null; policy_numbers: string | null
  insurance_expiry: string | null; group_key?: string | number
}
export type StockBlock = {
  rows: number; tallies: number; weight: number; baskol: number; quantity: number
  pallets: number; containers: number; customs_value: number
  insured_value: number; insurance_unknown: number; pallets_missing: number
  descriptions: string[]; package_types: string[]; owners: string[]
  locations: string[]; anbars: string[]; hscodes: string[]
}
export type StockGroup = StockBlock & { key: string | number; label: string }
export type StockData = {
  as_of: string; group_by: StockGroupBy
  totals: StockBlock
  groups: StockGroup[]; rows: StockRow[]
  facets: {
    owners: { id: number; name: string }[]
    anbars: { id: number; name: string }[]
    locations: { id: string; name: string }[]
  }
}
export type StockFilters = {
  groupBy: StockGroupBy; hscode: string; ownerId: string | null
  anbarId: string | null; location: string | null
  unloadedFrom: string | null; unloadedTo: string | null
}

const query = (params: Record<string, string | null | undefined>) => {
  const search = new URLSearchParams()
  for (const [key, value] of Object.entries(params)) if (value) search.set(key, value)
  return search.toString()
}

export function useIncomeSummary(from: string, to: string, enabled: boolean) {
  return useQuery({
    queryKey: ['reports', 'income', from, to],
    queryFn: () => apiGet<IncomeSummary>(`/reports/income?${query({ from, to })}`),
    enabled,
    placeholderData: keepPreviousData,
  })
}

export function useIncomeLines(from: string, to: string, category: string | null, enabled: boolean) {
  return useQuery({
    queryKey: ['reports', 'income-lines', from, to, category],
    queryFn: () => apiGet<IncomeLines>(`/reports/income/lines?${query({ from, to, category })}`),
    enabled,
    placeholderData: keepPreviousData,
  })
}

export function useStockReport(filters: StockFilters, enabled: boolean) {
  const params = {
    group_by: filters.groupBy, hscode: filters.hscode.trim(), owner_id: filters.ownerId,
    anbar_id: filters.anbarId, location: filters.location,
    unloaded_from: filters.unloadedFrom, unloaded_to: filters.unloadedTo,
  }
  return useQuery({
    queryKey: ['reports', 'stock', params],
    queryFn: () => apiGet<StockData>(`/reports/stock?${query(params)}`),
    enabled,
    placeholderData: keepPreviousData,
  })
}
