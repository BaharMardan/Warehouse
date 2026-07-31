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
type VariantOption = {
  value: string
  label: string
  field?: string
}

type Props = {
  path: string
  valueKey: string
  labelKey: LabelKey
  params?: Record<string, string | number>
  value: number | null
  onChange: (value: number | null) => void
  /** optional: also receive the full picked row (for snapshotting extra fields) */
  onPick?: (row: Row | null) => void
  /** optional: flatten each catalog row into multiple selectable variants */
  variantOptions?: VariantOption[]
  variantValue?: string | null
  onVariantChange?: (value: string | null) => void
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

function formatAmount(value: unknown): string {
  if (value == null || String(value).trim() === '') return '—'
  const normalized = String(value)
    .replace(/[\u06F0-\u06F9]/g, (d) => String(d.charCodeAt(0) - 0x06f0))
    .replace(/[\u0660-\u0669]/g, (d) => String(d.charCodeAt(0) - 0x0660))
    .replace(/[,\u066C]/g, '')
  const amount = Number(normalized)
  return Number.isFinite(amount) ? amount.toLocaleString('fa-IR') : String(value)
}

export function RefSelect({
  path,
  valueKey,
  labelKey,
  params,
  value,
  onChange,
  onPick,
  variantOptions,
  variantValue,
  onVariantChange,
  ...selectProps
}: Props) {
  const url = withParams(path, params)

  const { data, isLoading, isError } = useQuery({
    queryKey: ['refselect', path, params ?? null],
    queryFn: () => apiGet<Row[]>(url),
    staleTime: 5 * 60 * 1000,
  })

  // Some legacy CRUD endpoints ignore query-string filters. Apply the same fixed
  // lookup scope on the client so border/country selectors never mix categories.
  const scopedData = data?.filter((row) =>
    Object.entries(params ?? {}).every(
      ([key, expected]) => String(row[key] ?? '') === String(expected),
    ),
  )

  const hasVariants = Boolean(variantOptions?.length)
  const options = scopedData?.flatMap((row) => {
    const baseLabel = toLabel(row, labelKey)
    if (!hasVariants) {
      return [{ value: String(row[valueKey]), label: baseLabel }]
    }
    return variantOptions!.map((variant) => {
      const amount = variant.field ? `: ${formatAmount(row[variant.field])} ریال` : ''
      return {
        value: `${String(row[valueKey])}::${variant.value}`,
        label: `${baseLabel} — ${variant.label}${amount}`,
      }
    })
  }) ?? []

  const selectedValue =
    value == null
      ? null
      : hasVariants
        ? (variantValue == null ? null : `${String(value)}::${variantValue}`)
        : String(value)

  return (
    <Select
      data={options}
      value={selectedValue}
      onChange={(val) => {
        const [rawId, pickedVariant] =
          val == null ? [null, null] : hasVariants ? val.split('::', 2) : [val, null]
        const id = rawId == null ? null : Number(rawId)
        onChange(id)
        onVariantChange?.(pickedVariant)
        if (onPick) {
          const picked =
            id == null ? null : (scopedData?.find((r) => String(r[valueKey]) === String(rawId)) ?? null)
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
