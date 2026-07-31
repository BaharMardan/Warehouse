import { useMemo } from 'react'
import { Select, type SelectProps } from '@mantine/core'
import { useQuery } from '@tanstack/react-query'
import { apiGet } from '../api/client'

type TermRow = {
  sys_term_id: number
  category_id: number | null
  value: string | null
  order_no: number | null
}

type Props = {
  categoryId: number
  value: string | null
  onChange: (value: string | null) => void
} & Omit<SelectProps, 'data' | 'value' | 'onChange'>

export function TermValueSelect({
  categoryId,
  value,
  onChange,
  ...selectProps
}: Props) {
  const { data, isLoading, isError } = useQuery({
    queryKey: ['term-values', categoryId],
    queryFn: () => apiGet<TermRow[]>('/terms'),
    staleTime: 5 * 60 * 1000,
  })

  const options = useMemo(() => {
    const rows = (data ?? [])
      .filter((row) => Number(row.category_id) === categoryId && row.value?.trim())
      .sort((a, b) =>
        (a.order_no ?? Number.MAX_SAFE_INTEGER) - (b.order_no ?? Number.MAX_SAFE_INTEGER)
        || a.sys_term_id - b.sys_term_id,
      )
      .map((row) => ({ value: row.value!.trim(), label: row.value!.trim() }))

    // Preserve an older stored value even if its lookup row was later removed.
    if (value?.trim() && !rows.some((option) => option.value === value.trim())) {
      rows.push({ value: value.trim(), label: value.trim() })
    }
    return rows
  }, [data, categoryId, value])

  return (
    <Select
      data={options}
      value={value || null}
      onChange={onChange}
      searchable
      clearable
      nothingFoundMessage={isError ? 'خطا در بارگذاری' : 'موردی یافت نشد'}
      placeholder={isLoading ? 'در حال بارگذاری…' : selectProps.placeholder ?? 'انتخاب کنید'}
      disabled={isLoading || selectProps.disabled}
      {...selectProps}
    />
  )
}
