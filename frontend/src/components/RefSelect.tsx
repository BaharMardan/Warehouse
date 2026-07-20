import { useQuery } from '@tanstack/react-query'
import { Select, type SelectProps } from '@mantine/core'
import { apiGet } from '../api/client'

/**
 * RefSelect — a reusable foreign-key dropdown.
 * Fetches rows from an API resource; user sees a label, form stores the id.
 * Optional onPick hands back the whole picked row (e.g. to snapshot a code).
 */

type Row = Record<string, any>
type LabelKey = string | ((row: Row) => string)

type Props = {
  path: string
  valueKey: string
  labelKey: LabelKey
  params?: Record<string, string | number>
  value: number | null
  onChange: (value: number | null) => void
  /** optional: also receive the full picked row (for snapshotting extra fields) */
  onPick?: (row: Row | null) => void
} & Omit<SelectProps, 'data' | 'value' | 'onChange'>

function withParams(path: string, params?: Record<string, string | number>) {
  if (!params || Object.keys(params).length === 0) return path
  const qs = new URLSearchParams(
    Object.entries(params).map(([k, v]) => [k, String(v)]),
  ).toString()
  return `${path}?${qs}`
}

function toLabel(row: Row, labelKey: LabelKey): string {
  if (typeof labelKey === 'function') return labelKey(row).trim()
  const v = row[labelKey]
  return v == null ? '' : String(v)
}

export function RefSelect({
  path,
  valueKey,
  labelKey,
  params,
  value,
  onChange,
  onPick,
  ...selectProps
}: Props) {
  const url = withParams(path, params)

  const { data, isLoading, isError } = useQuery({
    queryKey: ['refselect', path, params ?? null],
    queryFn: () => apiGet<Row[]>(url),
    staleTime: 5 * 60 * 1000,
  })

  const options =
    data?.map((row) => ({
      value: String(row[valueKey]),
      label: toLabel(row, labelKey),
    })) ?? []

  return (
    <Select
      data={options}
      value={value == null ? null : String(value)}
      onChange={(val) => {
        const id = val == null ? null : Number(val)
        onChange(id)
        if (onPick) {
          const picked = id == null ? null : (data?.find((r) => String(r[valueKey]) === val) ?? null)
          onPick(picked)
        }
      }}
      searchable
      clearable
      nothingFoundMessage={isError ? 'خطا در بارگذاری' : 'موردی یافت نشد'}
      placeholder={isLoading ? 'در حال بارگذاری…' : selectProps.placeholder ?? 'انتخاب کنید'}
      disabled={isLoading || selectProps.disabled}
      {...selectProps}
    />
  )
}