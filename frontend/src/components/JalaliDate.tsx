import { useEffect, useMemo, useState } from 'react'
import { Button, Group, Input, Popover, Select, SimpleGrid, Text } from '@mantine/core'
import { jalaaliMonthLength, toGregorian, toJalaali } from 'jalaali-js'

type Props = {
  value: string | null
  onChange: (isoDate: string | null) => void
  label?: string
  compact?: boolean
}

const MONTHS = [
  'فروردین', 'اردیبهشت', 'خرداد', 'تیر', 'مرداد', 'شهریور',
  'مهر', 'آبان', 'آذر', 'دی', 'بهمن', 'اسفند',
]
const WEEKDAYS = ['ش', 'ی', 'د', 'س', 'چ', 'پ', 'ج']
const FA_DIGITS = '۰۱۲۳۴۵۶۷۸۹'
const faDigits = (value: number | string) => String(value).replace(/\d/g, (digit) => FA_DIGITS[Number(digit)])
const pad = (value: number) => String(value).padStart(2, '0')

function isoToParts(iso: string | null): { y: string; m: string; d: string } {
  if (!iso) return { y: '', m: '', d: '' }
  const [gy, gm, gd] = iso.slice(0, 10).split('-').map(Number)
  if (!gy || !gm || !gd) return { y: '', m: '', d: '' }
  const { jy, jm, jd } = toJalaali(gy, gm, gd)
  return { y: String(jy), m: String(jm), d: String(jd) }
}

function jalaliToIso(year: number, month: number, day: number): string {
  const { gy, gm, gd } = toGregorian(year, month, day)
  return `${gy}-${pad(gm)}-${pad(gd)}`
}

function yearOptions(selectedYear: number) {
  const today = new Date()
  const { jy } = toJalaali(today.getFullYear(), today.getMonth() + 1, today.getDate())
  const years = new Set<number>()
  for (let year = jy - 15; year <= jy + 5; year += 1) years.add(year)
  years.add(selectedYear)
  return [...years].sort((a, b) => a - b).map((year) => ({ value: String(year), label: faDigits(year) }))
}

/** Click-to-open Jalali calendar. Operators can select its month, year, and day. */
export function JalaliDate({ value, onChange, label, compact = false }: Props) {
  const initial = isoToParts(value)
  const today = new Date()
  const todayJalali = toJalaali(today.getFullYear(), today.getMonth() + 1, today.getDate())
  const [opened, setOpened] = useState(false)
  const [viewYear, setViewYear] = useState(Number(initial.y) || todayJalali.jy)
  const [viewMonth, setViewMonth] = useState(Number(initial.m) || todayJalali.jm)

  useEffect(() => {
    const next = isoToParts(value)
    if (next.y) setViewYear(Number(next.y))
    if (next.m) setViewMonth(Number(next.m))
  }, [value])

  const selected = isoToParts(value)
  const years = useMemo(() => yearOptions(viewYear), [viewYear])
  const daysInMonth = jalaaliMonthLength(viewYear, viewMonth)
  const first = toGregorian(viewYear, viewMonth, 1)
  // JavaScript starts weeks on Sunday; the Persian calendar grid starts on Saturday.
  const leadingEmptyCells = (new Date(first.gy, first.gm - 1, first.gd).getDay() + 1) % 7
  const cells: Array<number | null> = [
    ...Array.from({ length: leadingEmptyCells }, () => null),
    ...Array.from({ length: daysInMonth }, (_, index) => index + 1),
  ]
  while (cells.length % 7 !== 0) cells.push(null)

  const display = value
    ? `${faDigits(selected.d)} ${MONTHS[Number(selected.m) - 1]} ${faDigits(selected.y)}`
    : 'انتخاب تاریخ'

  return (
    <Input.Wrapper label={label}>
      <Popover opened={opened} onChange={setOpened} position="bottom-start" shadow="md" withinPortal>
        <Popover.Target>
          <Button
            variant="default"
            fullWidth
            justify="flex-start"
            onClick={() => setOpened((current) => !current)}
            styles={{
              root: {
                marginTop: compact ? 0 : 4,
                minHeight: compact ? 30 : undefined,
                height: compact ? 30 : undefined,
                paddingInline: compact ? 8 : undefined,
                border: compact ? 0 : undefined,
                background: compact ? 'transparent' : undefined,
                fontSize: compact ? 12 : undefined,
                fontWeight: 400,
              },
              label: { width: '100%', textAlign: 'right' },
            }}
          >
            {display}
          </Button>
        </Popover.Target>
        <Popover.Dropdown p={0} dir="rtl" style={{ minWidth: 300, overflow: 'hidden', borderRadius: 12 }}>
          <div style={{ padding: 12, background: 'linear-gradient(135deg, #5f3dc4, #7950f2)', color: '#fff' }}>
            <Text ta="center" fw={800} size="sm" mb="xs">انتخاب تاریخ</Text>
            <Group gap="xs" grow>
            <Select
              data={MONTHS.map((name, index) => ({ value: String(index + 1), label: name }))}
              value={String(viewMonth)}
              onChange={(month) => setViewMonth(Number(month ?? viewMonth))}
              styles={{ input: { background: 'rgba(255,255,255,0.95)', border: 0, fontWeight: 700 } }}
            />
            <Select
              data={years}
              value={String(viewYear)}
              onChange={(year) => setViewYear(Number(year ?? viewYear))}
              searchable
              styles={{ input: { background: 'rgba(255,255,255,0.95)', border: 0, fontWeight: 700 } }}
            />
            </Group>
          </div>
          <div style={{ padding: 10, background: '#f8f7ff' }}>
          <SimpleGrid cols={7} spacing={4} mb={6}>
            {WEEKDAYS.map((weekday, index) => (
              <Text
                key={weekday}
                ta="center"
                size="xs"
                fw={800}
                style={{ color: index === 6 ? '#e03131' : index === 0 ? '#1971c2' : '#6741d9' }}
              >
                {weekday}
              </Text>
            ))}
          </SimpleGrid>
          <SimpleGrid cols={7} spacing={4}>
            {cells.map((day, index) => {
              if (day == null) return <span key={`empty-${index}`} />
              const active = Number(selected.y) === viewYear && Number(selected.m) === viewMonth && Number(selected.d) === day
              const isFriday = index % 7 === 6
              const isSaturday = index % 7 === 0
              return (
                <Button
                  key={day}
                  size="xs"
                  h={32}
                  px={0}
                  radius="md"
                  variant={active ? 'filled' : 'light'}
                  color={active ? 'violet' : isFriday ? 'red' : isSaturday ? 'blue' : 'gray'}
                  styles={{
                    root: active
                      ? { boxShadow: '0 4px 10px rgba(103,65,217,0.35)' }
                      : { background: isFriday ? '#fff0f0' : isSaturday ? '#edf6ff' : '#fff' },
                  }}
                  onClick={() => {
                  onChange(jalaliToIso(viewYear, viewMonth, day))
                  setOpened(false)
                  }}
                >
                  {faDigits(day)}
                </Button>
              )
            })}
          </SimpleGrid>
          </div>
        </Popover.Dropdown>
      </Popover>
    </Input.Wrapper>
  )
}
