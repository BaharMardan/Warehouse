import { Button, Table } from '@mantine/core'
import { Link } from 'react-router-dom'
import type { AgingItem } from '../api/abandoned'
import { jalali } from '../pages/invoiceTypes'

export function AbandonedTable({ rows, warning = false, printable = false }: {
  rows: AgingItem[]; warning?: boolean; printable?: boolean
}) {
  return <Table striped={!printable} highlightOnHover={!printable}
    className={printable ? 'abandoned-print-table' : undefined}>
    <Table.Thead><Table.Tr>
      <Table.Th>شماره تالی</Table.Th><Table.Th>صاحب کالا</Table.Th>
      <Table.Th>تاریخ تخلیه</Table.Th><Table.Th>روزهای سپری‌شده</Table.Th>
      {warning && <Table.Th>روز تا متروکه‌شدن</Table.Th>}
    </Table.Tr></Table.Thead>
    <Table.Tbody>{rows.map(row => <Table.Tr key={row.id}>
      <Table.Td>{printable ? <bdi>{row.tally_number || row.id}</bdi> :
        <Button component={Link} to={`/tally/id/${row.id}`} variant="subtle" color="yellow">
          <bdi>{row.tally_number || row.id}</bdi>
        </Button>}</Table.Td>
      <Table.Td>{row.owner_name || '—'}</Table.Td>
      <Table.Td>{jalali(row.unloaded_at)}</Table.Td>
      <Table.Td>{row.age_days.toLocaleString('fa-IR')}</Table.Td>
      {warning && <Table.Td>{row.days_remaining.toLocaleString('fa-IR')}</Table.Td>}
    </Table.Tr>)}</Table.Tbody>
  </Table>
}
