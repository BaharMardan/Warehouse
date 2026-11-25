import { Alert, Button, Group, Loader, Paper, Stack, Table, Text, Title } from '@mantine/core'
import { Link, useNavigate } from 'react-router-dom'
import { useReleasedGoods } from '../../api/reports'
import { amount, downloadCsv, jalali, money } from './reportFormat'

export function ReleasedGoodsReport({ from, to, enabled, ownerId = null, printable = false }: {
  from: string; to: string; enabled: boolean; ownerId?: string | null; printable?: boolean
}) {
  const query = useReleasedGoods(from, to, enabled, ownerId)
  const navigate = useNavigate()
  if (query.isError) return <Alert color="red">دریافت گزارش کالاهای ترخیص‌شده ناموفق بود.</Alert>
  if (!query.data) return <Loader size="sm" />
  const { rows, totals, unresolved } = query.data
  const headers = ['ردیف', 'تالی', 'صورتحساب / قبض', 'HS Code', 'شرح کالا', 'صاحب کالا',
    'وزن اظهار (kg)', 'تاریخ صدور صورتحساب (ترخیص)',
    'ارزش کالا (گمرکی، ریال)', 'ارزش بیمه‌شده (هر تالی یک‌بار، ریال)']
  const values = rows.map((r, index) => [index + 1, r.tally_number ?? r.tally_id,
    `${r.invoice_number ?? r.invoice_id} / ${r.receipt_number ?? '—'}`, r.hscode, r.description,
    r.owner_name, r.weight,
    jalali(r.issued_at), r.customs_value, r.insured_value])
  return <Paper withBorder={!printable} p={printable ? 0 : 'md'} radius="md">
    <Stack gap="md">
      <Group justify="space-between">
        <Title order={4}>کالاهای ترخیص‌شده در بازه</Title>
        {!printable && <Group gap="xs">
          <Button size="xs" variant="light" onClick={() => navigate(`/reports/print?${new URLSearchParams({
            kind: 'released-goods', from, to, ...(ownerId ? { owner_id: ownerId } : {}),
          })}`)}>چاپ</Button>
          <Button size="xs" variant="light" disabled={!rows.length || query.isFetching}
            onClick={() => downloadCsv(`released-goods_${from}_${to}.csv`, headers,
              [...values, ['', 'جمع کل', '', '', '', '', totals.weight, '', totals.customs_value, totals.insured_value]])}>
            خروجی Excel (CSV)
          </Button>
        </Group>}
      </Group>
      <Text fw={700}>از {jalali(from)} تا {jalali(to)} — {amount(totals.tallies, 0)} تالی، {amount(totals.invoices, 0)} صورتحساب، {amount(totals.rows, 0)} ردیف کالا</Text>
      <Text size="xs" c="dimmed">مبنای ترخیص، تاریخ صدور صورتحساب فعال است. مقادیر مربوط به بخش ترخیص‌شده‌اند؛ ارزش بیمه‌نامه برای هر تالی فقط در اولین ردیف آن نمایش داده می‌شود.</Text>
      {unresolved.length > 0 && <Alert color="orange">تخصیص ردیف‌های {unresolved.length} صورتحساب قدیمی مشخص نیست و در جمع نیامده‌اند: {unresolved.map(r => `${r.invoice_number} (قبض ${r.receipt_number})`).join('، ')}</Alert>}
      {totals.insurance_unknown > 0 && <Alert color="orange">ارزش بیمه‌نامهٔ {totals.insurance_unknown} تالی بیمه‌دار نامشخص است و در جمع بیمه نیامده است.</Alert>}
      {query.isFetching && !printable && <Text size="xs">در حال به‌روزرسانی…</Text>}
      {!rows.length ? <Text c="dimmed">در این بازه کالای ترخیص‌شده‌ای با شرایط انتخابی یافت نشد.</Text> :
        <div style={{ overflowX: printable ? 'visible' : 'auto' }}>
          <Table striped={!printable} withTableBorder className={printable ? 'rp-table' : undefined}
            style={{ minWidth: printable ? undefined : 1500 }}>
            <Table.Thead><Table.Tr>{headers.map(label => <Table.Th key={label}>{label}</Table.Th>)}</Table.Tr></Table.Thead>
            <Table.Tbody>
              {rows.map((r, index) => <Table.Tr key={`${r.invoice_id}-${r.detail_id}`}>
                <Table.Td>{index + 1}</Table.Td>
                <Table.Td>{printable ? r.tally_number ?? r.tally_id : <Link to={`/tally/id/${r.tally_id}`}>{r.tally_number ?? r.tally_id}</Link>}</Table.Td>
                <Table.Td>{printable ? r.invoice_number : <Link to={`/invoice/${r.invoice_id}`}>{r.invoice_number}</Link>} / {r.receipt_number}</Table.Td>
                <Table.Td><bdi dir="ltr">{r.hscode ?? '—'}</bdi></Table.Td>
                <Table.Td>{r.description ?? '—'}</Table.Td><Table.Td>{r.owner_name ?? 'نامشخص'}</Table.Td>
                <Table.Td>{amount(r.weight, 4)}</Table.Td>
                <Table.Td>{jalali(r.issued_at)}</Table.Td><Table.Td>{money(r.customs_value)}</Table.Td>
                <Table.Td>{r.insurance_first ? r.insured_value == null ? 'نامشخص' : money(r.insured_value) : '—'}</Table.Td>
              </Table.Tr>)}
              <Table.Tr fw={700}><Table.Td colSpan={6}>جمع کل</Table.Td><Table.Td>{amount(totals.weight, 4)}</Table.Td>
                <Table.Td /><Table.Td>{money(totals.customs_value)}</Table.Td><Table.Td>{money(totals.insured_value)}</Table.Td></Table.Tr>
            </Table.Tbody>
          </Table>
        </div>}
    </Stack>
  </Paper>
}
