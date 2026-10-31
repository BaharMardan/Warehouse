import { useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { Alert, Button, Checkbox, Group, Loader, Modal, Radio, Stack, Table, Text } from '@mantine/core'
import { useNavigate } from 'react-router-dom'
import { apiSend, errorMessage } from '../api/client'
import { invoiceDescription, money } from '../pages/invoiceTypes'
import { InvoiceNumberInput, validInvoiceNumber } from './InvoiceNumberInput'

type Preview = {
  preview_hash: string; calc_note: string
  rows: { kind: string; description: string; price: string }[]
  totals: { subtotal: string; discount: string; net: string; tax: string; total_with_tax: string; prepayment: string; payable: string }
}

export function InvoiceIssueModal({ receiptId, missingCustoms, askDeductions, close }: {
  receiptId: number; missingCustoms: string[]; askDeductions: boolean; close: () => void
}) {
  const [number, setNumber] = useState('')
  const [confirmCustoms, setConfirmCustoms] = useState(false)
  const [deductions, setDeductions] = useState<string>('')
  const qc = useQueryClient()
  const navigate = useNavigate()
  const answers = {
    confirm_missing_customs: confirmCustoms,
    ...(askDeductions && deductions ? { apply_deductions: deductions === 'yes' } : {}),
  }
  const ready = (!missingCustoms.length || confirmCustoms) && (!askDeductions || !!deductions)
  const preview = useQuery({
    queryKey: ['invoice-preview', receiptId, answers],
    queryFn: () => apiSend<Preview>(`/ghabz/${receiptId}/invoice/preview`, 'POST', answers),
    enabled: ready, retry: false, staleTime: 0, refetchOnWindowFocus: false,
  })
  const current = ready && !preview.isError && !preview.isFetching ? preview.data : undefined
  const issue = useMutation({
    mutationFn: () => apiSend<{ invoice_id: number }>(`/ghabz/${receiptId}/invoice`, 'POST', {
      ...answers, invoice_number: number, preview_hash: current!.preview_hash,
    }),
    onSuccess: async result => {
      await qc.invalidateQueries()
      close()
      navigate(`/invoice/${result.invoice_id}`)
    },
  })
  const closeModal = () => { if (!issue.isPending) close() }
  return <Modal opened onClose={closeModal} title="پیش‌نمایش و صدور صورتحساب" size="lg" centered dir="rtl"
    closeOnClickOutside={!issue.isPending} closeOnEscape={!issue.isPending} withCloseButton={!issue.isPending}>
    <Stack gap="md">
      {!!missingCustoms.length && <Alert color="orange" title="ارزش گمرکی ثبت نشده است">
        <Text size="sm">ارزش گمرکی ردیف‌های {missingCustoms.join('، ')} ثبت نشده و هزینه بیمه آن‌ها صفر محاسبه می‌شود.</Text>
        <Checkbox mt="sm" label="محاسبه بیمه صفر برای این ردیف‌ها را تأیید می‌کنم"
          checked={confirmCustoms} onChange={event => setConfirmCustoms(event.currentTarget.checked)} disabled={issue.isPending} />
      </Alert>}
      {askDeductions && <Radio.Group label="پیش‌پرداخت و تخفیف روی همین قبض اعمال شود؟"
        value={deductions} onChange={setDeductions}>
        <Group mt="xs">
          <Radio value="yes" label="بله" disabled={issue.isPending} />
          <Radio value="no" label="خیر؛ برای قبض‌های دیگر بماند" disabled={issue.isPending} />
        </Group>
      </Radio.Group>}
      {ready && preview.isFetching && <Group justify="center"><Loader size="sm" /><Text>در حال محاسبه مبلغ صورتحساب…</Text></Group>}
      {preview.isError && ready && <Alert color="red">{errorMessage(preview.error, 'محاسبه صورتحساب انجام نشد')}</Alert>}
      {current && <>
        <Text size="sm" c="dimmed">{current.calc_note}</Text>
        <Table.ScrollContainer minWidth={400}><Table striped>
          <Table.Thead><Table.Tr><Table.Th>شرح</Table.Th><Table.Th>مبلغ (ریال)</Table.Th></Table.Tr></Table.Thead>
          <Table.Tbody>
            {current.rows.filter(row => !['discount', 'tax', 'prepayment'].includes(row.kind)).map((row, index) =>
              <Table.Tr key={index}><Table.Td>{invoiceDescription(row.description)}</Table.Td><Table.Td><bdi dir="ltr">{money(row.price)}</bdi></Table.Td></Table.Tr>)}
            {([
              ['جمع ردیف‌ها', current.totals.subtotal], ['تخفیف', current.totals.discount],
              ['جمع', current.totals.net], ['مالیات بر ارزش افزوده', current.totals.tax],
              ['جمع کل', current.totals.total_with_tax], ['پیش‌پرداخت', current.totals.prepayment],
              ['مبلغ قابل پرداخت', current.totals.payable],
            ] as [string, string][]).map(([label, value]) =>
              <Table.Tr key={label} fw={700}><Table.Td>{label}</Table.Td><Table.Td><bdi dir="ltr">{money(value)}</bdi></Table.Td></Table.Tr>)}
          </Table.Tbody>
        </Table></Table.ScrollContainer>
      </>}
      <InvoiceNumberInput value={number} onChange={setNumber} disabled={issue.isPending} />
      {issue.isError && <Alert color="red">{errorMessage(issue.error, 'صدور صورتحساب انجام نشد؛ دوباره تلاش کنید')}</Alert>}
      <Group justify="space-between">
        <Button variant="subtle" disabled={!ready || preview.isFetching || issue.isPending}
          onClick={() => { issue.reset(); void preview.refetch() }}>محاسبه مجدد</Button>
        <Group>
          <Button variant="default" disabled={issue.isPending} onClick={closeModal}>انصراف</Button>
          <Button color="red" loading={issue.isPending} disabled={!current || !validInvoiceNumber(number)}
            onClick={() => { if (current && validInvoiceNumber(number) && !issue.isPending) issue.mutate() }}>صدور صورتحساب</Button>
        </Group>
      </Group>
    </Stack>
  </Modal>
}
