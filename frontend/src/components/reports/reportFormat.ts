import { toGregorian, toJalaali } from 'jalaali-js'

export { jalali, money } from '../../pages/invoiceTypes'

const pad = (value: number) => String(value).padStart(2, '0')

export const isoDate = (date: Date) =>
  `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())}`

const fromParts = (year: number, month: number, day: number) => {
  const { gy, gm, gd } = toGregorian(year, month, day)
  return `${gy}-${pad(gm)}-${pad(gd)}`
}

/** Quick periods for the report range, as ISO dates (Gregorian) computed from Jalali months. */
export function periodPresets(now = new Date()) {
  const today = isoDate(now)
  const { jy, jm } = toJalaali(now.getFullYear(), now.getMonth() + 1, now.getDate())
  const monthAgo = new Date(now)
  monthAgo.setDate(monthAgo.getDate() - 29)
  return [
    { label: 'امروز', from: today, to: today },
    { label: 'ماه جاری', from: fromParts(jy, jm, 1), to: today },
    { label: '۳۰ روز اخیر', from: isoDate(monthAgo), to: today },
    { label: 'سال جاری', from: fromParts(jy, 1, 1), to: today },
  ]
}

/** Weights and counts: Latin digits, grouped, up to two decimals. */
export const amount = (value: number | string | null | undefined, digits = 2) =>
  value == null ? '—' : Number(value).toLocaleString('en-US', { maximumFractionDigits: digits })

export const percent = (part: number, whole: number) =>
  whole === 0 ? '—' : `${((part / whole) * 100).toLocaleString('en-US', { maximumFractionDigits: 1 })}٪`

type Cell = string | number | null | undefined

/** Download rows as a UTF-8 CSV with a BOM, so Excel shows Persian text correctly. */
export function downloadCsv(filename: string, header: string[], rows: Cell[][]) {
  const escape = (cell: Cell) => {
    const text = cell == null ? '' : String(cell)
    return /[",\r\n]/.test(text) ? `"${text.replace(/"/g, '""')}"` : text
  }
  const body = [header, ...rows].map((row) => row.map(escape).join(',')).join('\r\n')
  const url = URL.createObjectURL(new Blob(['\uFEFF' + body], { type: 'text/csv;charset=utf-8' }))
  const link = document.createElement('a')
  link.href = url
  link.download = filename
  document.body.appendChild(link)
  link.click()
  link.remove()
  setTimeout(() => URL.revokeObjectURL(url), 1000)
}
