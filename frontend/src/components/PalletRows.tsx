import { useState } from 'react'
import { IranianPlate } from './IranianPlate'
import './TallyHandlingSection.css'
import { Button, Group, Table, Text, TextInput } from '@mantine/core'

export type PalletRow = {
  id: number; number_hamel: string | null; description: string | null
  hscode: string | null; zarib_mahal: string | null; pallets: number | null
  used_pallets?: number; selected_pallets?: number | null
}
export type PalletEntry = { tally_detail_id: number; pallets: number }
const digits = (value: string) => value.replace(/[۰-۹]/g, d => String(d.charCodeAt(0) - 1776))
  .replace(/[٠-٩]/g, d => String(d.charCodeAt(0) - 1632))

export function PalletRows({ rows, allocation = false, editable, pending, expected, onSave }: {
  rows: PalletRow[]; allocation?: boolean; editable: boolean; pending: boolean
  expected?: number | null; onSave: (lines: PalletEntry[]) => void
}) {
  const [draft, setDraft] = useState<Record<number, string>>({})
  const value = (row: PalletRow) => draft[row.id] ?? String((allocation ? row.selected_pallets : row.pallets) ?? '')
  const entries = rows.map(row => ({ tally_detail_id: row.id, pallets: Number(value(row)) }))
  const total = entries.reduce((sum, r) => sum + (Number.isFinite(r.pallets) ? r.pallets : 0), 0)
  const valid = rows.length > 0 && entries.every((entry, index) => Number.isInteger(entry.pallets) && entry.pallets > 0
    && (!allocation || entry.pallets <= Number(rows[index].pallets ?? 0) - Number(rows[index].used_pallets ?? 0)))
    && total <= 100000 && (expected == null || total === expected)
  return <>
    <Table.ScrollContainer minWidth={760}><Table className="tally-pallet-table" withTableBorder withColumnBorders>
      <Table.Thead><Table.Tr>
        <Table.Th>ردیف تالی</Table.Th><Table.Th>شماره حامل</Table.Th><Table.Th>شرح کالا</Table.Th>
        <Table.Th>HS Code</Table.Th><Table.Th>ضریب محل</Table.Th>
        {allocation && <Table.Th>پالت قابل تخصیص</Table.Th>}
        <Table.Th>{allocation ? 'پالت این قبض' : 'تعداد پالت این ردیف'}</Table.Th>
      </Table.Tr></Table.Thead>
      <Table.Tbody>{rows.map((row, index) => <Table.Tr key={row.id}>
        <Table.Td className="tally-pallet-row-number">{(index + 1).toLocaleString('fa-IR')}</Table.Td><Table.Td><IranianPlate value={row.number_hamel} /></Table.Td>
        <Table.Td>{row.description ?? '—'}</Table.Td><Table.Td>{row.hscode ?? '—'}</Table.Td>
        <Table.Td>{row.zarib_mahal ?? '—'}</Table.Td>
        {allocation && <Table.Td>{row.pallets == null ? 'ابتدا پالت تالی را تکمیل کنید' : row.pallets - (row.used_pallets ?? 0)}</Table.Td>}
        <Table.Td>{!editable ? <Text size="sm">{value(row) || '—'}</Text> : <TextInput aria-label={`تعداد پالت ردیف ${index + 1}`} inputMode="numeric"
          value={value(row)} disabled={!editable || pending} style={{ minWidth: 100 }}
          onChange={event => { const next = digits(event.currentTarget.value); if (/^\d*$/.test(next)) setDraft(prev => ({ ...prev, [row.id]: next })) }}
        />}</Table.Td>
      </Table.Tr>)}</Table.Tbody>
    </Table></Table.ScrollContainer>
    <Group justify="space-between" mt="sm">
      <Text size="sm">جمع پالت ردیف‌ها: {total.toLocaleString('fa-IR')}{expected != null && ` / ${expected.toLocaleString('fa-IR')}`}</Text>
      {editable && <Button loading={pending} disabled={!valid} onClick={() => onSave(entries)}>ذخیره پالت ردیف‌ها</Button>}
    </Group>
    {editable && !valid && <Text size="xs" c="orange" mt="xs">برای تمام ردیف‌ها تعداد صحیح و مثبت وارد کنید؛ جمع و مانده قابل تخصیص نیز باید رعایت شود.</Text>}
  </>
}
