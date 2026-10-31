import { useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { Alert, Badge, Button, Group, Paper, Stack, Table, Text } from '@mantine/core'
import { useNavigate } from 'react-router-dom'
import { apiGet, apiSend, errorMessage } from '../api/client'
import { InvoiceIssueModal } from './InvoiceIssueModal'
import { ReceiptPallets } from './ReceiptPallets'
import { usePermissions } from '../auth/usePermissions'

type Workflow = {
  id: number; tally_id: number; is_master: string; status: string
  summary_only: boolean; show_checklist: boolean; show_invoice: boolean
  can_return: boolean; can_finalize: boolean; can_invoice: boolean; services_locked: boolean
  allocation_ratio: number | null; invoice_id: number | null; pallet_quantity: number | null
  // A tally's prepayment and discount land on one of its invoices. For detailed
  // receipts the user is asked per receipt until one invoice takes them.
  deductions?: { prepayment: number | null; discount: number | null; applied: boolean; ask: boolean }
  // Linked tally rows without a customs value: insurance counts them as zero, so
  // issuing shows this error first and needs an explicit confirmation.
  missing_customs?: string[]
}
const statusLabels: Record<string, string> = {
  created: 'در انتظار چک‌لیست انباردار', sent_to_keeper: 'در انتظار چک‌لیست انباردار',
  finalized: 'ثبت نهایی شده', invoice_issued: 'صورتحساب صادرشده',
}
export function useReceiptWorkflow(id: number) {
  return useQuery({
    queryKey: ['receipt-workflow', id],
    queryFn: () => apiGet<Workflow>(`/ghabz/${id}/workflow`),
    enabled: Number.isFinite(id), refetchInterval: 20000,
  })
}

export function ReceiptWorkflow({ id, placement = 'receipt' }: { id: number; placement?: 'receipt' | 'tally' | 'correction' }) {
  const { data: state, error } = useReceiptWorkflow(id)
  const { can } = usePermissions()
  const navigate = useNavigate()
  const qc = useQueryClient()
  const action = useMutation({
    mutationFn: ({ path, method = 'POST', body }: { path: string; method?: 'PUT' | 'POST' | 'DELETE'; body?: unknown }) =>
      apiSend<{ invoice_id?: number }>(path.startsWith('/invoice/') ? path : `/ghabz/${id}/${path}`, method, body),
    onSuccess: async (result, variables) => {
      await Promise.all(['receipt-workflow', 'receipt-sources', 'receipt-keeper-queue',
        'keeper-queue', 'abandoned', 'tally-header', 'tally-list', 'tally-insurance-check', 'tally-handoff', 'kartabl-list', 'invoice-list', 'ghabz-summary'].map(key =>
          qc.invalidateQueries({ queryKey: [key] })))
      if (variables.path === 'invoice' && result?.invoice_id) navigate(`/invoice/${result.invoice_id}`)
    },
  })
  const [issueOpen, setIssueOpen] = useState(false)
  if (error) return <Text c="red">خطا در دریافت وضعیت چک‌لیست قبض.</Text>
  if (!state) return <Text size="sm">در حال دریافت وضعیت قبض…</Text>
  const editable = can('tally.services') && state.can_finalize
  const missingCustoms = state.missing_customs ?? []
  return <>
    {!state.summary_only && <Badge color={state.can_finalize ? 'orange' : 'teal'}>{statusLabels[state.status]}</Badge>}
    {placement === 'receipt' && state.show_checklist && state.status !== 'invoice_issued' && !state.invoice_id && <Button variant="light"
      onClick={() => navigate(`/tally/id/${state.tally_id}?receipt=${id}`)}>
      چک‌لیست نهایی توسط انباردار
    </Button>}
    {placement === 'tally' && editable && <Button color="teal" style={{ marginInlineStart: 'auto' }} loading={action.isPending}
      onClick={() => action.mutate({ path: 'final-checklist' })}>ثبت نهایی</Button>}
    {placement !== 'tally' && state.can_return && can('workflow.return') && <Button color="orange" variant="light" loading={action.isPending}
      onClick={() => { if (window.confirm('تمام قبض‌های این تالی برای اصلاح ردیف‌های کالا و خدمات باز می‌شوند و باید دوباره ثبت نهایی شوند. ادامه می‌دهید؟')) action.mutate({ path: 'return' }) }}>بازگشت برای اصلاح</Button>}
    {placement !== 'tally' && state.invoice_id && can('workflow.return') && <Button color="red" variant="light" loading={action.isPending}
      onClick={() => { if (window.confirm('صورتحساب باطل شود؟ پس از ابطال آخرین صورتحساب فعال، تمام بخش‌های تالی برای اصلاح باز می‌شوند.')) action.mutate({ path: `/invoice/${state.invoice_id}`, method: 'DELETE' }) }}>ابطال صورتحساب</Button>}
    {placement === 'receipt' && state.show_invoice && state.status === 'finalized' && can('invoice.issue') &&
      <Button color="red" disabled={!state.can_invoice} loading={action.isPending}
        onClick={() => setIssueOpen(true)}>صدور صورتحساب</Button>}
    {issueOpen && <InvoiceIssueModal receiptId={id} missingCustoms={missingCustoms}
      askDeductions={!!state.deductions?.ask} close={() => setIssueOpen(false)} />}
    {placement === 'receipt' && state.invoice_id && can('invoice.view') && <Button color="red" variant="light"
      onClick={() => navigate(`/invoice/${state.invoice_id}`)}>مشاهده صورتحساب</Button>}
    {action.error && <Text c="red" size="sm">{errorMessage(action.error, 'عملیات انجام نشد')}</Text>}

  </>
}

export function ReceiptKeeperQueue() {
  const { can } = usePermissions()
  const navigate = useNavigate()
  const { data, error } = useQuery({
    queryKey: ['receipt-keeper-queue'],
    queryFn: () => apiGet<{ id: number; number_text: string | null; tally_id: number }[]>('/ghabz/keeper-queue'),
    enabled: can('tally.services'), refetchInterval: 20000,
  })
  if (!can('tally.services')) return null
  return <Paper withBorder p="md" mb="md" style={{ backgroundColor: '#f0fdf4', borderColor: '#bbf7d0' }}>
    <Text fw={700} mb="xs">قبض‌های در انتظار چک‌لیست نهایی انباردار</Text>
    {error && <Text c="red">خطا در دریافت چک‌لیست‌های در انتظار.</Text>}
    <Group>{data?.map(r => <Button key={r.id} variant="light" onClick={() => navigate(`/tally/id/${r.tally_id}?receipt=${r.id}`)}>
      {r.number_text ?? r.id}
    </Button>)}</Group>
    {data?.length === 0 && <Text c="dimmed" size="sm">قبض در انتظار تکمیل ندارید.</Text>}
  </Paper>
}


type ReceiptRow = {
  id_ghabz_anbar_details: number; hscode: string | null; description_kala: string | null
  number_kala: number | null; weighte_asnad: number | null; weighte_baskol: number | null
  type_basteh: string | null
}

export function ReceiptContext({ id, number }: { id: number; number: string | null }) {
  const { data: receipt, isPending: receiptPending, error: receiptError } = useReceiptWorkflow(id)
  const { data, isPending, error } = useQuery({
    queryKey: ['receipt-context', id],
    queryFn: () => apiGet<ReceiptRow[]>(`/ghabz/${id}/details`),
  })
  return <Paper className="tally-receipt-context" withBorder p="md" mb="md">
    <Group justify="space-between" mb="xs">
      <Text fw={700}>اطلاعات قبض {number ?? id}</Text>
      <Text size="sm" fw={600}>تعداد پالت این قبض: {receiptPending ? '…' : receiptError ? 'خطا در دریافت' : receipt?.pallet_quantity == null ? '—' : Number(receipt.pallet_quantity).toLocaleString('fa-IR')}</Text>
    </Group>
    <Text size="sm" c="dimmed" mb="sm">خدمات تالی را برای این قبض تکمیل می‌کنید. ردیف‌های زیر فقط جهت اطلاع نمایش داده می‌شوند.</Text>
    {isPending && <Text size="sm">در حال دریافت ردیف‌های قبض…</Text>}
    {error && <Text c="red">دریافت اطلاعات قبض ناموفق بود.</Text>}
    {data && <Table.ScrollContainer minWidth={650}><Table withTableBorder striped>
      <Table.Thead><Table.Tr>
        <Table.Th>HS Code</Table.Th><Table.Th>شرح کالا</Table.Th><Table.Th>نوع بسته</Table.Th>
        <Table.Th>تعداد</Table.Th><Table.Th>وزن اسناد</Table.Th><Table.Th>وزن باسکول</Table.Th>
      </Table.Tr></Table.Thead>
      <Table.Tbody>{data.map(row => <Table.Tr key={row.id_ghabz_anbar_details}>
        <Table.Td>{row.hscode ?? '—'}</Table.Td><Table.Td>{row.description_kala ?? '—'}</Table.Td>
        <Table.Td>{row.type_basteh ?? '—'}</Table.Td><Table.Td>{row.number_kala ?? '—'}</Table.Td>
        <Table.Td>{row.weighte_asnad ?? '—'}</Table.Td><Table.Td>{row.weighte_baskol ?? '—'}</Table.Td>
      </Table.Tr>)}</Table.Tbody>
    </Table></Table.ScrollContainer>}
    {data?.length === 0 && <Text size="sm">این قبض ردیف فعال ندارد.</Text>}
    <ReceiptPallets id={id} />
  </Paper>
}
