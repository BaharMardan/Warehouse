import { useState } from 'react'
import { useMutation, useQueryClient, useQuery } from '@tanstack/react-query'
import { useNavigate } from 'react-router-dom'
import { Alert, Button, Group, Modal, Center, Loader, Paper, Table, Text } from '@mantine/core'
import { usePermissions } from '../auth/usePermissions'
import { apiGet, apiSend, errorMessage } from '../api/client'
import { BackButton } from '../components/BackButton'
import { PageHeader } from '../components/PageHeader'
import { InvoiceListRow, jalali, money } from './invoiceTypes'

export function InvoiceListPage() {
  const navigate = useNavigate()
  const qc = useQueryClient()
  const { can } = usePermissions()
  const [selected, setSelected] = useState<InvoiceListRow | null>(null)
  const cancel = useMutation({
    mutationFn: (id: number) => apiSend<void>(`/invoice/${id}`, 'DELETE'),
    onSuccess: async (_, id) => {
      qc.setQueryData<InvoiceListRow[]>(['invoice-list'], rows => rows?.filter(row => row.id_sorat !== id))
      setSelected(null)
      await qc.invalidateQueries()
    },
  })
  const close = () => { if (!cancel.isPending) { setSelected(null); cancel.reset() } }
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
          {can('invoice.issue') && <Table.Th>عملیات</Table.Th>}
        </Table.Tr></Table.Thead>
        <Table.Tbody>{data.map(row => <Table.Tr key={row.id_sorat} style={{ cursor: 'pointer' }}
          onClick={() => navigate(`/invoice/${row.id_sorat}`)}>
          <Table.Td><bdi dir="ltr">{row.id_sorat}</bdi>{row.original_invoice_id && <Text size="xs" c="orange">باقی‌مانده — اصلی {row.original_invoice_id}</Text>}</Table.Td>
          <Table.Td>{jalali(row.created_at)}</Table.Td>
          <Table.Td><bdi dir="ltr">{row.tali_number ?? '—'}</bdi></Table.Td>
          <Table.Td>{row.seller_name || '—'}</Table.Td><Table.Td>{row.buyer_name || '—'}</Table.Td>
          <Table.Td><bdi dir="ltr">{money(row.grand_total)}</bdi></Table.Td>
          {can('invoice.issue') && <Table.Td>
            <Button color="red" variant="light" size="xs" disabled={cancel.isPending}
              onClick={event => { event.stopPropagation(); cancel.reset(); setSelected(row) }}>ابطال صورتحساب</Button>
          </Table.Td>}
        </Table.Tr>)}</Table.Tbody>
      </Table></Table.ScrollContainer>}
    </Paper>
    <Modal opened={selected !== null} onClose={close} title="ابطال صورتحساب" centered dir="rtl"
      closeOnClickOutside={!cancel.isPending} closeOnEscape={!cancel.isPending} withCloseButton={!cancel.isPending}>
      <Text>آیا از ابطال صورتحساب شماره {selected?.id_sorat} اطمینان دارید؟</Text>
      <Text size="sm" c="dimmed" mt="sm">قبض و تالی حفظ می‌شوند و امکان صدور مجدد صورتحساب فراهم می‌شود.</Text>
      {cancel.isError && <Alert color="red" mt="sm">{errorMessage(cancel.error, 'ابطال صورتحساب انجام نشد. دوباره تلاش کنید.')}</Alert>}
      <Group justify="flex-end" mt="lg">
        <Button variant="default" disabled={cancel.isPending} onClick={close}>انصراف</Button>
        <Button color="red" loading={cancel.isPending}
          onClick={() => { if (selected && !cancel.isPending) cancel.mutate(selected.id_sorat) }}>تأیید ابطال</Button>
      </Group>
    </Modal>
  </div>
}
