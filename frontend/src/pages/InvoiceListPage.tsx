import { useQuery } from '@tanstack/react-query'
import { useNavigate } from 'react-router-dom'
import { Center, Loader, Paper, Table, Text } from '@mantine/core'
import { apiGet } from '../api/client'
import { BackButton } from '../components/BackButton'
import { PageHeader } from '../components/PageHeader'
import { InvoiceListRow, jalali, money } from './invoiceTypes'

export function InvoiceListPage() {
  const navigate = useNavigate()
  const { data, isLoading, isError } = useQuery({
    queryKey: ['invoice-list'], queryFn: () => apiGet<InvoiceListRow[]>('/invoice/list'),
  })
  return <div dir="rtl">
    <PageHeader title="لیست صورتحساب‌ها" subtitle="مشاهده و چاپ صورتحساب‌های ثبت‌شده" actions={<BackButton to="/" />} />
    <Paper shadow="none" p={0}>
      {isLoading && <Center py="xl"><Loader /></Center>}
      {isError && <Center py="xl"><Text c="red">خطا در بارگذاری صورتحساب‌ها.</Text></Center>}
      {data?.length === 0 && <Center py="xl"><Text c="dimmed">هنوز صورتحسابی ثبت نشده است.</Text></Center>}
      {!!data?.length && <Table.ScrollContainer minWidth={790}><Table striped highlightOnHover styles={{ th: {
        backgroundColor: '#e03131', color: '#fff', fontWeight: 800, borderColor: '#c92a2a',
      } }}>
        <Table.Thead><Table.Tr>
          <Table.Th>شماره صورتحساب</Table.Th><Table.Th>تاریخ صدور</Table.Th>
          <Table.Th>شماره تالی</Table.Th><Table.Th>فروشنده</Table.Th>
          <Table.Th>خریدار</Table.Th><Table.Th>مبلغ کل (ریال)</Table.Th>
        </Table.Tr></Table.Thead>
        <Table.Tbody>{data.map(row => <Table.Tr key={row.id_sorat} style={{ cursor: 'pointer' }}
          onClick={() => navigate(`/invoice/${row.id_sorat}`)}>
          <Table.Td><bdi dir="ltr">{row.id_sorat}</bdi></Table.Td>
          <Table.Td>{jalali(row.created_at)}</Table.Td>
          <Table.Td><bdi dir="ltr">{row.tali_number ?? '—'}</bdi></Table.Td>
          <Table.Td>{row.seller_name || '—'}</Table.Td><Table.Td>{row.buyer_name || '—'}</Table.Td>
          <Table.Td><bdi dir="ltr">{money(row.grand_total)}</bdi></Table.Td>
        </Table.Tr>)}</Table.Tbody>
      </Table></Table.ScrollContainer>}
    </Paper>
  </div>
}
