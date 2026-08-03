import { isValidJalaaliDate, toGregorian, toJalaali } from 'jalaali-js'

export type FlexibleJalaliDateResult =
  | { status: 'empty'; iso: null }
  | { status: 'invalid'; iso: null }
  | { status: 'valid'; iso: string }

const pad = (value: number) => String(value).padStart(2, '0')

/** Persian/Arabic-Indic digits -> Latin digits. */
export function normalizeDateDigits(value: string): string {
  return value
    .replace(/[\u06F0-\u06F9]/g, (digit) => String(digit.charCodeAt(0) - 0x06f0))
    .replace(/[\u0660-\u0669]/g, (digit) => String(digit.charCodeAt(0) - 0x0660))
}

/**
 * Keep a manual Jalali date tidy without forcing an entry direction.
 * Both 1405/06/12 and 12/06/1405 remain possible while the user types.
 */
export function normalizeFlexibleJalaliInput(value: string): string {
  return normalizeDateDigits(value)
    .replace(/[.\\\-\s]+/g, '/')
    .replace(/[^\d/]/g, '')
    .replace(/\/{2,}/g, '/')
    .slice(0, 10)
}

/**
 * Parse a manually entered Jalali date. The four-digit part identifies the year,
 * so both year/month/day and day/month/year are accepted without ambiguity.
 */
export function parseFlexibleJalaliDate(value: string): FlexibleJalaliDateResult {
  const normalized = normalizeFlexibleJalaliInput(value).replace(/^\/+|\/+$/g, '')
  if (normalized === '') return { status: 'empty', iso: null }

  const parts = normalized.split('/')
  if (parts.length !== 3 || parts.some((part) => part === '')) {
    return { status: 'invalid', iso: null }
  }

  const yearFirst = parts[0].length === 4 && parts[2].length !== 4
  const yearLast = parts[2].length === 4 && parts[0].length !== 4
  if (!yearFirst && !yearLast) return { status: 'invalid', iso: null }

  const [yearText, monthText, dayText] = yearFirst
    ? [parts[0], parts[1], parts[2]]
    : [parts[2], parts[1], parts[0]]
  const jy = Number(yearText)
  const jm = Number(monthText)
  const jd = Number(dayText)

  if (!isValidJalaaliDate(jy, jm, jd)) return { status: 'invalid', iso: null }

  try {
    const { gy, gm, gd } = toGregorian(jy, jm, jd)
    return { status: 'valid', iso: `${gy}-${pad(gm)}-${pad(gd)}` }
  } catch {
    return { status: 'invalid', iso: null }
  }
}

/** Oracle/FastAPI ISO date -> canonical Jalali year/month/day for editing/display. */
export function isoToJalaliInput(value: string | null): string {
  if (!value) return ''
  const [gy, gm, gd] = value.slice(0, 10).split('-').map(Number)
  if (!gy || !gm || !gd) return value

  try {
    const { jy, jm, jd } = toJalaali(gy, gm, gd)
    return `${jy}/${pad(jm)}/${pad(jd)}`
  } catch {
    return value
  }
}
