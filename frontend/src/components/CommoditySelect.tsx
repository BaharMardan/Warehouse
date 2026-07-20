import { useState } from 'react'
import { Select, type SelectProps } from '@mantine/core'
import { useDebouncedValue } from '@mantine/hooks'
import { useQuery } from '@tanstack/react-query'
import { apiGet } from '../api/client'

/**
 * CommoditySelect — server-side autocomplete over FA_COMMODITY_CATALOG.
 *
 * The catalog has ~9k rows, so this NEVER loads them all (unlike RefSelect). It queries
 * /commodity?q=… as the user types (debounced) and hands the full picked row back via
 * onPick, so the caller can snapshot HS code / description / unit / duty / profit and,
 * when present, the storage group.
 */

export type Commodity = {
  id: number
  hs_code: string
  description_fa: string | null
  unit: string | null
  customs_duty: number | null
  commercial_profit: number | null
  storage_group_id: number | null
  storage_group_code: string | null
}

type SearchResponse = { items: Commodity[]; total: number }

type Props = {
  value: number | null
  onPick: (c: Commodity | null) => void
  /** the currently-selected row, so its label shows even when it isn't in the latest search */
  selected?: Commodity | null
} & Omit<SelectProps, 'data' | 'value' | 'onChange'>

const optionLabel = (c: Commodity) =>
  `${c.hs_code} — ${c.description_fa ?? ''}`.trim()

export function CommoditySelect({ value, onPick, selected, ...rest }: Props) {
  const [search, setSearch] = useState('')
  const [debounced] = useDebouncedValue(search, 300)
  const canSearch = debounced.trim().length >= 2

  const { data, isFetching } = useQuery({
    queryKey: ['commodity-search', debounced],
    queryFn: () =>
      apiGet<SearchResponse>(`/commodity?q=${encodeURIComponent(debounced)}&limit=20`),
    enabled: canSearch,
    staleTime: 60 * 1000,
  })

  const items = data?.items ?? []

  // union the search results with the already-selected row so its label stays visible
  const merged = new Map<number, Commodity>()
  if (selected) merged.set(selected.id, selected)
  for (const c of items) merged.set(c.id, c)

  const options = [...merged.values()].map((c) => ({
    value: String(c.id),
    label: optionLabel(c),
  }))

  return (
    <Select
      searchable
      clearable
      data={options}
      value={value == null ? null : String(value)}
      searchValue={search}
      onSearchChange={setSearch}
      // the server already filtered; keep every option Mantine received
      filter={({ options }) => options}
      onChange={(val) => {
        const picked = val == null ? null : merged.get(Number(val)) ?? null
        onPick(picked)
      }}
      placeholder="جستجوی HS Code یا شرح کالا…"
      nothingFoundMessage={
        !canSearch
          ? 'حداقل ۲ حرف تایپ کنید'
          : isFetching
            ? 'در حال جستجو…'
            : 'موردی یافت نشد'
      }
      {...rest}
    />
  )
}
