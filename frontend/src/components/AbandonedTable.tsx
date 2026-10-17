import { Button, Table } from '@mantine/core'
import { Link } from 'react-router-dom'
import type { AgingItem, AgingGoods } from '../api/abandoned'
import { jalali } from '../pages/invoiceTypes'

const number = (value: number | string | null | undefined) =>
  value == null ? '—' : Number(value).toLocaleString('fa-IR', { maximumFractionDigits: 3 })

export function AbandonedTable({ rows, warning = false, printable = false }: {
  rows: AgingItem[]; warning?: boolean; printable?: boolean
}) {
  const lines = rows.flatMap<{ tally: AgingItem; goods: AgingGoods | null }>(tally => tally.goods?.length
    ? tally.goods.map(goods => ({ tally, goods }))
    : [{ tally, goods: null }])
  return <Table striped={!printable} highlightOnHover={!printable}
    className={printable ? 'abandoned-print-table' : undefined}>
    <Table.Thead><Table.Tr>
      <Table.Th>ردیف</Table.Th><Table.Th>HS Code</Table.Th><Table.Th>شرح کالا</Table.Th>
      <Table.Th>ارزش گمرکی کالا</Table.Th><Table.Th>وزن اظهار (کالاهای باقی‌مانده) — کیلوگرم</Table.Th>
      <Table.Th>شماره ثبت سفارش</Table.Th><Table.Th>شماره قبض انبار</Table.Th><Table.Th>تاریخ تخلیه</Table.Th>
      {warning && <Table.Th>روز تا متروکه‌شدن</Table.Th>}
    </Table.Tr></Table.Thead>
    <Table.Tbody>{lines.map(({ tally, goods }, index) => <Table.Tr key={`${tally.id}-${goods?.detail_id ?? 'empty'}`}>
      <Table.Td>{printable ? (index + 1).toLocaleString('fa-IR') :
        <Button component={Link} to={`/tally/id/${tally.id}`} variant="subtle" color="yellow" size="compact-sm"
          title={`تالی ${tally.tally_number || tally.id}`} aria-label={`مشاهده تالی ${tally.tally_number || tally.id}`}>
          {(index + 1).toLocaleString('fa-IR')}
        </Button>}</Table.Td>
      <Table.Td><bdi dir="ltr">{goods?.hscode || '—'}</bdi></Table.Td>
      <Table.Td>{goods?.description || '—'}</Table.Td>
      <Table.Td><bdi dir="ltr">{number(goods?.customs_value)}</bdi></Table.Td>
      <Table.Td><bdi dir="ltr">{number(goods?.remaining_weight)}</bdi></Table.Td>
      <Table.Td style={{ whiteSpace: 'pre-line' }}><bdi dir="ltr">{tally.order_registration_number || '—'}</bdi></Table.Td>
      <Table.Td>{goods?.receipts.length ? goods.receipts.map(receipt =>
        <div key={receipt.id}><bdi dir="ltr">{receipt.number || receipt.id}</bdi></div>) : '—'}</Table.Td>
      <Table.Td>{jalali(tally.unloaded_at)}</Table.Td>
      {warning && <Table.Td>{tally.days_remaining.toLocaleString('fa-IR')}</Table.Td>}
    </Table.Tr>)}</Table.Tbody>
  </Table>
}
