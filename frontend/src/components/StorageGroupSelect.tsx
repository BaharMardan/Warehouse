import { useQuery } from '@tanstack/react-query'
import { Select, type SelectProps } from '@mantine/core'
import { apiGet } from '../api/client'

/**
 * StorageGroupSelect — the warehouse storage-price group picker (code_groupe_kala).
 *
 * Users must never see or type the internal numeric group id. This shows the HUMAN group
 * name (joined from FA_KALA on the backend), so a manual pick reads e.g. «۱۰۲ — محصولات
 * فولادی» instead of «102 - Unit: Ton». Only ~33 groups, so all are loaded once and
 * filtered client-side. Mainly a fallback: once a commodity is mapped, the tally fills
 * this automatically and the field can be hidden entirely.
 */

export type StorageGroup = {
  id: number
  code: string | null
  name: string | null
  price_30_day: number | string | null
  price_60_day: number | string | null
  price_90_day: number | string | null
}

type Props = {
  value: number | null
  onChange: (value: number | null) => void
} & Omit<SelectProps, 'data' | 'value' | 'onChange'>

const groupLabel = (g: StorageGroup) => {
  const name = (g.name ?? '').trim()
  const code = g.code ?? String(g.id)
  return name ? `${code} — ${name}` : `${code}`
}

export function StorageGroupSelect({ value, onChange, ...rest }: Props) {
  const { data, isLoading, isError } = useQuery({
    queryKey: ['storage-groups'],
    queryFn: () => apiGet<StorageGroup[]>('/commodity/storage-groups'),
    staleTime: 5 * 60 * 1000,
  })

  const options =
    data?.map((g) => ({ value: String(g.id), label: groupLabel(g) })) ?? []

  return (
    <Select
      data={options}
      value={value == null ? null : String(value)}
      onChange={(val) => onChange(val == null ? null : Number(val))}
      searchable
      clearable
      nothingFoundMessage={isError ? 'خطا در بارگذاری' : 'گروهی یافت نشد'}
      placeholder={isLoading ? 'در حال بارگذاری…' : (rest.placeholder ?? 'انتخاب گروه قیمت انبار')}
      disabled={isLoading || rest.disabled}
      {...rest}
    />
  )
}
