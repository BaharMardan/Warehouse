import { useQuery } from '@tanstack/react-query'
import { useParams } from 'react-router-dom'
import { Button, Center, Group, Loader, Paper, SimpleGrid, Table, Text, Title } from '@mantine/core'
import { apiGet } from '../api/client'
import { BackButton } from '../components/BackButton'
import { IconPrint } from '../components/icons'
import { SavedInvoice, invoiceSections, jalali, money, quantity, signedMoney } from './invoiceTypes'

const headStyles = { th: { backgroundColor: '#e03131', color: '#fff' } }

export function InvoiceDetailPage() {
  const { id } = useParams()
  const invoiceId = Number(id)
  const { data, isLoading, isError } = useQuery({
    queryKey: ['invoice', invoiceId], queryFn: () => apiGet<SavedInvoice>(`/invoice/${invoiceId}`),
    enabled: Number.isInteger(invoiceId) && invoiceId > 0,
  })
  return <div dir="rtl">
    <Group justify="space-between" mb="md">
      <Title order={2}>صورتحساب <bdi dir="ltr">{data?.header.id_sorat ?? id}</bdi></Title>
      <Group><Button color="red" leftSection={<IconPrint size={18} />}
        onClick={() => window.open(`/invoice/${invoiceId}/print`, '_blank', 'noopener,noreferrer')}
        disabled={!data}>چاپ صورتحساب</Button><BackButton to="/invoice" /></Group>
    </Group>
    {isLoading && <Center py="xl"><Loader /></Center>}
    {isError && <Text c="red">صورتحساب یافت نشد یا بارگذاری آن ناموفق بود.</Text>}
    {data && <>
      <SimpleGrid cols={{ base: 1, md: 2 }} mb="md">
        <Paper withBorder p="md"><Title order={4} c="red" mb="sm">مشخصات فروشنده</Title>
          <Text>{data.header.seller_name || '—'}</Text><Text size="sm">نشانی: {data.header.seller_address || '—'}</Text>
          <Text size="sm">شناسه ملی: {data.header.seller_national_id || '—'}</Text></Paper>
        <Paper withBorder p="md"><Title order={4} c="red" mb="sm">مشخصات خریدار</Title>
          <Text>{data.header.buyer_name || '—'}</Text><Text size="sm">نشانی: {data.header.buyer_address || '—'}</Text>
          <Text size="sm">شماره تالی: {data.header.tali_number || '—'} | تاریخ: {jalali(data.header.created_at)}</Text>
          {data.header.ghabz_number && <Text size="sm">شماره قبض انبار: <bdi dir="ltr">{data.header.ghabz_number}</bdi></Text>}</Paper>
      </SimpleGrid>
      {invoiceSections(data.details).modern ? <ModernDetails data={data} /> :
      <Paper withBorder p="md"><Title order={4} mb="sm">جزئیات صورتحساب</Title>
        <Table.ScrollContainer minWidth={700}><Table striped styles={{ th: { backgroundColor: '#e03131', color: '#fff' } }}>
          <Table.Thead><Table.Tr><Table.Th>ردیف</Table.Th><Table.Th>شرح</Table.Th>
            <Table.Th>تعداد</Table.Th><Table.Th>وزن</Table.Th><Table.Th>مبلغ کل</Table.Th>
            <Table.Th>تخفیف</Table.Th><Table.Th>مبلغ خالص</Table.Th></Table.Tr></Table.Thead>
          <Table.Tbody>{data.details.map((line, index) => <Table.Tr key={line.id_detail}>
            <Table.Td>{index + 1}</Table.Td><Table.Td>{line.description || '—'}</Table.Td>
            <Table.Td>{line.quantity ?? '—'}</Table.Td><Table.Td>{line.weight ?? '—'}</Table.Td>
            <Table.Td>{money(line.price)}</Table.Td><Table.Td>{money(line.discount)}</Table.Td>
            <Table.Td>{money(line.price == null ? null : Number(line.price) - Number(line.discount ?? 0))}</Table.Td>
          </Table.Tr>)}</Table.Tbody>
        </Table></Table.ScrollContainer>
        <Text fw={800} mt="md">جمع کل: <bdi dir="ltr">{money(data.grand_total)}</bdi> ریال</Text>
      </Paper>}
    </>}
  </div>
}

// 1405 invoices: every charge with how it was calculated, then the summary
// «جمع هزینه‌ها + مالیات − پیش‌پرداخت − تخفیف = قابل پرداخت» for the operator's check.
function ModernDetails({ data }: { data: SavedInvoice }) {
  const { charges, subtotal, summary } = invoiceSections(data.details)
  return <Paper withBorder p="md"><Title order={4} mb="xs">جزئیات صورتحساب</Title>
    {data.header.calc_note && <Text size="sm" c="dimmed" mb="sm">{data.header.calc_note}</Text>}
    <Table.ScrollContainer minWidth={900}><Table striped verticalSpacing="xs" styles={headStyles}>
      <Table.Thead><Table.Tr><Table.Th w={50}>ردیف</Table.Th><Table.Th>شرح</Table.Th>
        <Table.Th>تعداد</Table.Th><Table.Th>وزن (کیلوگرم)</Table.Th><Table.Th>مبلغ (ریال)</Table.Th>
        <Table.Th w="38%">نحوه محاسبه</Table.Th></Table.Tr></Table.Thead>
      <Table.Tbody>{charges.map((line, index) => <Table.Tr key={line.id_detail}>
        <Table.Td>{index + 1}</Table.Td><Table.Td>{line.description || '—'}</Table.Td>
        <Table.Td><bdi dir="ltr">{quantity(line.quantity)}</bdi></Table.Td>
        <Table.Td><bdi dir="ltr">{quantity(line.weight)}</bdi></Table.Td>
        <Table.Td><bdi dir="ltr">{money(line.price)}</bdi></Table.Td>
        <Table.Td><Text size="xs" c="dimmed">{line.calc_note || '—'}</Text></Table.Td>
      </Table.Tr>)}</Table.Tbody>
      <Table.Tbody>
        <Table.Tr><Table.Td colSpan={4} fw={700}>جمع هزینه‌ها</Table.Td>
          <Table.Td fw={700}><bdi dir="ltr">{money(subtotal)}</bdi></Table.Td><Table.Td /></Table.Tr>
        {summary.map((line) => <Table.Tr key={line.id_detail}>
          <Table.Td colSpan={4}>{line.description}</Table.Td>
          <Table.Td><bdi dir="ltr">{signedMoney(line.price)}</bdi></Table.Td>
          <Table.Td><Text size="xs" c="dimmed">{line.calc_note || '—'}</Text></Table.Td>
        </Table.Tr>)}
        <Table.Tr style={{ backgroundColor: '#fff1f1' }}><Table.Td colSpan={4} fw={800}>مبلغ قابل پرداخت</Table.Td>
          <Table.Td fw={800}><bdi dir="ltr">{money(data.grand_total)}</bdi></Table.Td><Table.Td /></Table.Tr>
      </Table.Tbody>
    </Table></Table.ScrollContainer>
  </Paper>
}
