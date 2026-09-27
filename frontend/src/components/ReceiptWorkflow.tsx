import { useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { Alert, Badge, Button, Group, Modal, Paper, Stack, Table, Text } from '@mantine/core'
import { useNavigate } from 'react-router-dom'
import { apiGet, apiSend, errorMessage } from '../api/client'
import { usePermissions } from '../auth/usePermissions'

type Workflow = {
  id: number; tally_id: number; is_master: string; status: string
  summary_only: boolean; show_checklist: boolean; show_invoice: boolean
  can_finalize: boolean; can_invoice: boolean; services_locked: boolean
  allocation_ratio: number | null; invoice_id: number | null; pallet_quantity: number | null
  // A tally's prepayment and discount land on one of its invoices. For detailed
  // receipts the user is asked per receipt until one invoice takes them.
  deductions?: { prepayment: number | null; discount: number | null; applied: boolean; ask: boolean }
  // Linked tally rows without a customs value: insurance counts them as zero, so
  // issuing shows this error first and needs an explicit confirmation.
  missing_customs?: string[]
}
type IssueAnswers = { confirm_missing_customs?: boolean; apply_deductions?: boolean }
const rials = (value: number | null | undefined) => Number(value ?? 0).toLocaleString('en-US')
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

export function ReceiptWorkflow({ id, placement = 'receipt' }: { id: number; placement?: 'receipt' | 'tally' }) {
  const { data: state, error } = useReceiptWorkflow(id)
  const { can } = usePermissions()
  const navigate = useNavigate()
  const qc = useQueryClient()
  const action = useMutation({
    mutationFn: ({ path, method = 'POST', body }: { path: string; method?: 'PUT' | 'POST'; body?: unknown }) =>
      apiSend<{ invoice_id?: number }>(`/ghabz/${id}/${path}`, method, body),
    onSuccess: async (result, variables) => {
      await Promise.all(['receipt-workflow', 'receipt-sources', 'receipt-keeper-queue',
        'keeper-queue', 'tally-handoff', 'kartabl-list', 'invoice-list', 'ghabz-summary'].map(key =>
          qc.invalidateQueries({ queryKey: [key] })))
      if (variables.path === 'invoice' && result.invoice_id) navigate(`/invoice/${result.invoice_id}`)
    },
  })
  // Issuing may need two answers, asked in order: the missing-customs error,
  // then the prepayment/discount question.
  const [issueStep, setIssueStep] = useState<null | 'customs' | 'deductions'>(null)
  const [answers, setAnswers] = useState<IssueAnswers>({})
  const issueInvoice = (final: IssueAnswers) => {
    setIssueStep(null)
    setAnswers({})
    action.mutate({ path: 'invoice', body: Object.keys(final).length ? final : undefined })
  }
  if (error) return <Text c="red">خطا در دریافت وضعیت چک‌لیست قبض.</Text>
  if (!state) return <Text size="sm">در حال دریافت وضعیت قبض…</Text>
  const editable = can('tally.services') && state.can_finalize
  const missingCustoms = state.missing_customs ?? []
  const startIssue = () => {
    if (missingCustoms.length > 0) setIssueStep('customs')
    else if (state.deductions?.ask) setIssueStep('deductions')
    else issueInvoice({})
  }
  const confirmCustoms = () => {
    if (state.deductions?.ask) {
      setAnswers({ confirm_missing_customs: true })
      setIssueStep('deductions')
    } else issueInvoice({ confirm_missing_customs: true })
  }
  return <>
    {!state.summary_only && <Badge color={state.can_finalize ? 'orange' : 'teal'}>{statusLabels[state.status]}</Badge>}
    {placement === 'receipt' && state.show_checklist && <Button variant="light"
      onClick={() => navigate(`/tally/id/${state.tally_id}?receipt=${id}`)}>
      چک‌لیست نهایی توسط انباردار
    </Button>}
    {placement === 'tally' && editable && <Button color="teal" loading={action.isPending}
      onClick={() => action.mutate({ path: 'final-checklist' })}>تأیید نهایی</Button>}
    {placement === 'receipt' && state.show_invoice && state.status === 'finalized' && can('invoice.issue') &&
      <Button color="red" disabled={!state.can_invoice} loading={action.isPending}
        onClick={startIssue}>صدور صورتحساب</Button>}
    <Modal opened={issueStep === 'customs'} onClose={() => setIssueStep(null)} title="ارزش گمرکی ثبت نشده" centered dir="rtl">
      <Stack gap="sm">
        <Alert color="red" variant="light" title="ارزش گمرکی این کالاها در تالی ثبت نشده است.">
          ردیف‌ها: <bdi dir="ltr">{missingCustoms.join('، ')}</bdi>
          <br />
          هزینه بیمه این ردیف‌ها صفر محاسبه می‌شود و در صورتحساب یک ردیف بیمه با مبلغ صفر ثبت خواهد شد.
        </Alert>
        <Group justify="flex-end">
          <Button variant="default" onClick={() => setIssueStep(null)}>انصراف</Button>
          <Button color="red" onClick={confirmCustoms}>صدور با بیمه صفر برای این ردیف‌ها</Button>
        </Group>
      </Stack>
    </Modal>
    <Modal opened={issueStep === 'deductions'} onClose={() => setIssueStep(null)} title="پیش‌پرداخت و تخفیف" centered dir="rtl">
      <Stack gap="sm">
        <Text fw={600}>آیا مبلغ پیش‌پرداخت و تخفیف روی همین قبض اعمال شود؟</Text>
        {Number(state.deductions?.prepayment ?? 0) > 0 &&
          <Text size="sm">پیش‌پرداخت: <bdi dir="ltr">{rials(state.deductions?.prepayment)}</bdi> ریال</Text>}
        {Number(state.deductions?.discount ?? 0) > 0 &&
          <Text size="sm">تخفیف: <bdi dir="ltr">{rials(state.deductions?.discount)}</bdi> ریال</Text>}
        <Text size="sm" c="dimmed">
          اگر «خیر» را انتخاب کنید، این سؤال هنگام صدور صورتحساب قبض‌های دیگر این تالی دوباره پرسیده می‌شود.
        </Text>
        <Group justify="flex-end">
          <Button variant="default" onClick={() => issueInvoice({ ...answers, apply_deductions: false })}>خیر</Button>
          <Button color="red" onClick={() => issueInvoice({ ...answers, apply_deductions: true })}>بله</Button>
        </Group>
      </Stack>
    </Modal>
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
  </Paper>
}
