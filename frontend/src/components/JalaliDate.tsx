// import { useState, useEffect } from 'react'
// import { Input, Group, TextInput } from '@mantine/core'
// import { toJalaali, toGregorian } from 'jalaali-js'

// /**
//  * JalaliDate — a Persian (Jalali) date entered as three boxes: روز / ماه / سال
//  * (day / month / year), that talks ISO to the API.
//  *
//  * The database stores a real Gregorian Oracle DATE; the user enters a Persian
//  * date. Three separate number boxes mean there's no ambiguity about order and no
//  * separator parsing — the day box is always the day.
//  *
//  *   - `value`    is an ISO date string "YYYY-MM-DD" (what the API stores), or null
//  *   - `onChange` emits an ISO date string "YYYY-MM-DD", or null when empty/invalid
//  *
//  * Accepts Persian (۰۱۲۳), Arabic-Indic (٠١٢٣) and Latin (0123) digits in any box.
//  *
//  *   <JalaliDate label="تاریخ ورود به مرز" value={form.date_enter_marze}
//  *               onChange={(iso) => setForm({ ...form, date_enter_marze: iso })} />
//  */

// type Props = {
//   /** ISO date the form holds, e.g. "2026-04-28", or null */
//   value: string | null
//   /** called with a new ISO date "YYYY-MM-DD", or null if empty/invalid */
//   onChange: (isoDate: string | null) => void
//   /** field label shown above the boxes */
//   label?: string
//   /** mark the label with a required asterisk */
//   required?: boolean
// }

// const pad = (n: number) => String(n).padStart(2, '0')

// // Persian/Arabic-Indic digits -> Latin, so ۱۴۰۵ parses. Latin passes through.
// function normalizeDigits(s: string): string {
//   return s
//     .replace(/[\u06F0-\u06F9]/g, (d) => String(d.charCodeAt(0) - 0x06f0))
//     .replace(/[\u0660-\u0669]/g, (d) => String(d.charCodeAt(0) - 0x0660))
// }

// // ISO "2026-04-28" -> the three Jalali box strings { y:"1405", m:"2", d:"8" }.
// // Empty/invalid ISO -> all blanks.
// function isoToParts(iso: string | null): { y: string; m: string; d: string } {
//   if (!iso) return { y: '', m: '', d: '' }
//   const [gy, gm, gd] = iso.slice(0, 10).split('-').map(Number)
//   if (!gy || !gm || !gd) return { y: '', m: '', d: '' }
//   const { jy, jm, jd } = toJalaali(gy, gm, gd)
//   return { y: String(jy), m: String(jm), d: String(jd) }
// }

// // The three box strings -> ISO "2026-04-28". null if empty or not a valid date.
// function partsToIso(y: string, m: string, d: string): string | null {
//   const ys = normalizeDigits(y).trim()
//   const ms = normalizeDigits(m).trim()
//   const ds = normalizeDigits(d).trim()
//   if (ys === '' && ms === '' && ds === '') return null // all empty -> null
//   if (!/^\d+$/.test(ys) || !/^\d+$/.test(ms) || !/^\d+$/.test(ds)) return null
//   const jy = Number(ys)
//   const jm = Number(ms)
//   const jd = Number(ds)
//   if (jy < 1000 || jy > 9999) return null
//   if (jm < 1 || jm > 12) return null
//   if (jd < 1 || jd > 31) return null
//   const { gy, gm, gd } = toGregorian(jy, jm, jd)
//   return `${gy}-${pad(gm)}-${pad(gd)}`
// }

// export function JalaliDate({ value, onChange, label, required }: Props) {
//   // Local box strings. Kept as text so users can type freely (blank, partial).
//   const [parts, setParts] = useState(() => isoToParts(value))

//   // If the parent changes value from outside (loading a row to edit), resync.
//   useEffect(() => {
//     setParts(isoToParts(value))
//   }, [value])

//   // Did the user enter something that isn't a valid complete date?
//   const anyFilled = parts.y !== '' || parts.m !== '' || parts.d !== ''
//   const iso = partsToIso(parts.y, parts.m, parts.d)
//   const isInvalid = anyFilled && iso === null

//   // Update one box, recompute, and push ISO (or null) to the parent.
//   function update(next: { y: string; m: string; d: string }) {
//     setParts(next)
//     onChange(partsToIso(next.y, next.m, next.d))
//   }

//   // digits only, capped — keeps boxes tidy (year up to 4, day/month up to 2)
//   const clean = (s: string, max: number) =>
//     normalizeDigits(s).replace(/\D/g, '').slice(0, max)

//   const boxProps = { inputMode: 'numeric' as const, styles: { input: { textAlign: 'center' as const } } }

//   return (
//     <Input.Wrapper label={label} required={required} error={isInvalid ? 'تاریخ نامعتبر است' : undefined}>
//       {/* dir=rtl so the boxes read روز-ماه-سال right-to-left like Persian dates */}
//       <Group gap="xs" dir="rtl" wrap="nowrap" mt={4}>
//         <TextInput
//           {...boxProps}
//           placeholder="روز"
//           w={70}
//           value={parts.d}
//           onChange={(e) => update({ ...parts, d: clean(e.currentTarget.value, 2) })}
//         />
//         <TextInput
//           {...boxProps}
//           placeholder="ماه"
//           w={70}
//           value={parts.m}
//           onChange={(e) => update({ ...parts, m: clean(e.currentTarget.value, 2) })}
//         />
//         <TextInput
//           {...boxProps}
//           placeholder="سال"
//           w={90}
//           value={parts.y}
//           onChange={(e) => update({ ...parts, y: clean(e.currentTarget.value, 4) })}
//         />
//       </Group>
//     </Input.Wrapper>
//   )
// }

import { useState, useEffect, useMemo } from 'react'
import { Input, Group, Select } from '@mantine/core'
import { toJalaali, toGregorian } from 'jalaali-js'

/**
 * JalaliDate — a Persian (Jalali) date entered as three dropdowns: روز / ماه / سال
 * (day / month / year), that talks ISO to the API.
 *
 * The database stores a real Gregorian Oracle DATE; the user picks a Persian date.
 * Three separate dropdowns mean there's no ambiguity about order and no parsing —
 * the day dropdown is always the day. The value emitted and the conversion are
 * unchanged from the previous text-box version; only the input widget differs.
 *
 *   - `value`    is an ISO date string "YYYY-MM-DD" (what the API stores), or null
 *   - `onChange` emits an ISO date string "YYYY-MM-DD", or null when empty/invalid
 *
 *   <JalaliDate label="تاریخ ورود به مرز" value={form.date_enter_marze}
 *               onChange={(iso) => setForm({ ...form, date_enter_marze: iso })} />
 */

type Props = {
  /** ISO date the form holds, e.g. "2026-04-28", or null */
  value: string | null
  /** called with a new ISO date "YYYY-MM-DD", or null if empty/invalid */
  onChange: (isoDate: string | null) => void
  /** field label shown above the boxes */
  label?: string
}

const pad = (n: number) => String(n).padStart(2, '0')

// Persian/Arabic-Indic digits -> Latin, so ۱۴۰۵ parses. Latin passes through.
function normalizeDigits(s: string): string {
  return s
    .replace(/[\u06F0-\u06F9]/g, (d) => String(d.charCodeAt(0) - 0x06f0))
    .replace(/[\u0660-\u0669]/g, (d) => String(d.charCodeAt(0) - 0x0660))
}

// ISO "2026-04-28" -> the three Jalali box strings { y:"1405", m:"2", d:"8" }.
// Empty/invalid ISO -> all blanks.
function isoToParts(iso: string | null): { y: string; m: string; d: string } {
  if (!iso) return { y: '', m: '', d: '' }
  const [gy, gm, gd] = iso.slice(0, 10).split('-').map(Number)
  if (!gy || !gm || !gd) return { y: '', m: '', d: '' }
  const { jy, jm, jd } = toJalaali(gy, gm, gd)
  return { y: String(jy), m: String(jm), d: String(jd) }
}

// The three box strings -> ISO "2026-04-28". null if empty or not a valid date.
function partsToIso(y: string, m: string, d: string): string | null {
  const ys = normalizeDigits(y).trim()
  const ms = normalizeDigits(m).trim()
  const ds = normalizeDigits(d).trim()
  if (ys === '' && ms === '' && ds === '') return null // all empty -> null
  if (!/^\d+$/.test(ys) || !/^\d+$/.test(ms) || !/^\d+$/.test(ds)) return null
  const jy = Number(ys)
  const jm = Number(ms)
  const jd = Number(ds)
  if (jy < 1000 || jy > 9999) return null
  if (jm < 1 || jm > 12) return null
  if (jd < 1 || jd > 31) return null
  const { gy, gm, gd } = toGregorian(jy, jm, jd)
  return `${gy}-${pad(gm)}-${pad(gd)}`
}

// Persian (Jalali) month names, index 0 = فروردین.
const MONTHS = [
  'فروردین', 'اردیبهشت', 'خرداد', 'تیر', 'مرداد', 'شهریور',
  'مهر', 'آبان', 'آذر', 'دی', 'بهمن', 'اسفند',
]

// Latin -> Persian digits, for display labels only (values stay Latin numeric).
const FA = '۰۱۲۳۴۵۶۷۸۹'
const faDigits = (n: number | string) => String(n).replace(/[0-9]/g, (d) => FA[+d])

// Static option lists. Values are Latin numeric strings (what partsToIso expects);
// labels are what the user sees. Day/month never depend on each other, matching the
// old text-box behaviour (1–31 always allowed; range-checked in partsToIso).
const DAY_OPTIONS = Array.from({ length: 31 }, (_, i) => ({
  value: String(i + 1), label: faDigits(i + 1),
}))
const MONTH_OPTIONS = MONTHS.map((name, i) => ({ value: String(i + 1), label: name }))

// Year list: a window around the current Jalali year that ALWAYS includes the year
// currently held (so editing a record whose year is outside the window still shows it).
function buildYearOptions(selectedYear: string) {
  const now = new Date()
  const { jy } = toJalaali(now.getFullYear(), now.getMonth() + 1, now.getDate())
  const years = new Set<number>()
  for (let y = jy - 15; y <= jy + 5; y++) years.add(y)
  const sel = Number(selectedYear)
  if (selectedYear !== '' && Number.isFinite(sel)) years.add(sel)
  return [...years].sort((a, b) => a - b).map((y) => ({ value: String(y), label: faDigits(y) }))
}

export function JalaliDate({ value, onChange, label }: Props) {
  // Local part strings ("8", "2", "1405"). Kept as state so partial picks are allowed.
  const [parts, setParts] = useState(() => isoToParts(value))

  // If the parent changes value from outside (loading a row to edit), resync.
  useEffect(() => {
    setParts(isoToParts(value))
  }, [value])

  // Did the user pick something that isn't a valid complete date (e.g. missing year)?
  const anyFilled = parts.y !== '' || parts.m !== '' || parts.d !== ''
  const iso = partsToIso(parts.y, parts.m, parts.d)
  const isInvalid = anyFilled && iso === null

  // Update one dropdown, recompute, and push ISO (or null) to the parent.
  function update(next: { y: string; m: string; d: string }) {
    setParts(next)
    onChange(partsToIso(next.y, next.m, next.d))
  }

  // Year options depend on the selected year so an out-of-window value still appears.
  const yearOptions = useMemo(() => buildYearOptions(parts.y), [parts.y])

  return (
    <Input.Wrapper label={label} error={isInvalid ? 'تاریخ نامعتبر است' : undefined}>
      {/* dir=rtl so the dropdowns read روز-ماه-سال right-to-left like Persian dates */}
      <Group gap="xs" dir="rtl" wrap="nowrap" mt={4}>
        <Select
          placeholder="روز" w={80} data={DAY_OPTIONS} clearable
          value={parts.d || null}
          onChange={(v) => update({ ...parts, d: v ?? '' })}
        />
        <Select
          placeholder="ماه" w={120} data={MONTH_OPTIONS} clearable searchable
          value={parts.m || null}
          onChange={(v) => update({ ...parts, m: v ?? '' })}
        />
        <Select
          placeholder="سال" w={100} data={yearOptions} clearable searchable
          value={parts.y || null}
          onChange={(v) => update({ ...parts, y: v ?? '' })}
        />
      </Group>
    </Input.Wrapper>
  )
}
