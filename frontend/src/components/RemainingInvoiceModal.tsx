import './RemainingInvoiceModal.css'
import { useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { ActionIcon, Alert, Badge, Button, Group, Loader, Modal, NumberInput, Paper, Select, SimpleGrid, Stack, Table, Text, TextInput, Tooltip } from '@mantine/core'
import { useDebouncedValue } from '@mantine/hooks'
import { IconPlus, IconTrash } from './icons'
import { useNavigate } from 'react-router-dom'
import { apiGet, apiSend, errorMessage } from '../api/client'
import { invoiceDescription, money } from '../pages/invoiceTypes'

type Goods = { id: number; description: string | null; hscode: string | null; kala_code: string | null; number_hamel: string | null }
type Service = { id: number; title: string; price: string | null }
type Options = { other_services: Service[]; original_invoice_id: number; cargo: string; goods: Goods[]; original_insurance: string }
type Input = { other_services: { service_id: number; quantity: string }[]; days: number; source_id: number; hscode: string; kala_code: string; amount: string; insurance_percent: string }
type Preview = { preview_hash: string; total: string; calc_note: string; rows: { kind: string; description: string; quantity: string | null; price: string; note: string }[] }

function requestId() {
  const bytes = crypto.getRandomValues(new Uint8Array(16))
  bytes[6] = (bytes[6] & 15) | 64
  bytes[8] = (bytes[8] & 63) | 128
  const hex = Array.from(bytes, b => b.toString(16).padStart(2, '0')).join('')
  return `${hex.slice(0, 8)}-${hex.slice(8, 12)}-${hex.slice(12, 16)}-${hex.slice(16, 20)}-${hex.slice(20)}`
}

export function RemainingInvoiceModal({ receiptId, close }: { receiptId: number; close: () => void }) {
  const navigate = useNavigate()
  const qc = useQueryClient()
  const [request] = useState(requestId)
  const [source, setSource] = useState<string | null>(null)
  const [hscode, setHscode] = useState('')
  const [code, setCode] = useState('')
  const [days, setDays] = useState<string | number>('')
  const [amount, setAmount] = useState<string | number>('')
  const [services, setServices] = useState<{ key: string; id: string | null; quantity: string | number }[]>([])
  const [percent, setPercent] = useState<string | number>(0)
  const { data, isPending, isError } = useQuery({
    queryKey: ['remaining-options', receiptId],
    queryFn: () => apiGet<Options>(`/ghabz/${receiptId}/remaining-invoice`),
  })
  const input: Input = { other_services: services.map(row => ({ service_id: Number(row.id), quantity: String(row.quantity) })), days: Number(days), source_id: Number(source), hscode: hscode.trim(), kala_code: code.trim(),
    amount: String(amount), insurance_percent: String(percent) }
  const key = JSON.stringify(input)
  const volumetric = data?.cargo === 'volumetric' || data?.cargo === 'yes'
  const valid = Number.isSafeInteger(Number(days)) && Number(days) > 0 && !!source && !!input.hscode && !!input.kala_code && Number(amount) > 0
    && services.every(row => !!row.id && Number(row.quantity) > 0 && Number.isFinite(Number(row.quantity)))
    && String(percent) !== '' && Number(percent) >= 0 && Number(percent) <= 100
  const [debouncedKey] = useDebouncedValue(key, 450)
  const calculate = useQuery({
    queryKey: ['remaining-preview', receiptId, debouncedKey],
    queryFn: () => apiSend<Preview>(`/ghabz/${receiptId}/remaining-invoice/preview`, 'POST', JSON.parse(debouncedKey)),
    enabled: !!data && valid && key === debouncedKey,
    retry: false,
    staleTime: 0,
  })
  const current = valid && key === debouncedKey && !calculate.isError ? calculate.data : undefined
  const calculating = valid && (key !== debouncedKey || calculate.isFetching)
  const issue = useMutation({
    mutationFn: () => apiSend<{ invoice_id: number }>(`/ghabz/${receiptId}/remaining-invoice`, 'POST',
      { ...input, preview_hash: current!.preview_hash, request_id: request }),
    onSuccess: async result => {
      await qc.invalidateQueries({ queryKey: ['invoice-list'] })
      close()
      navigate(`/invoice/${result.invoice_id}`)
    },
  })
  const selectGoods = (value: string | null) => {
    setSource(value)
    const row = data?.goods.find(item => String(item.id) === value)
    setHscode(row?.hscode ?? '')
    setCode(String(row?.kala_code ?? ''))
  }
  return <Modal classNames={{ content: 'remaining-modal', header: 'remaining-modal-header', body: 'remaining-modal-body' }} opened onClose={() => { if (!issue.isPending) close() }} size={900} radius="lg" padding="lg" centered dir="rtl"
    title={<Text fw={800} size="lg">صدور صورتحساب باقی‌مانده</Text>} closeOnClickOutside={!issue.isPending}
    closeOnEscape={!issue.isPending} withCloseButton={!issue.isPending}>
    <Stack gap="md">
      {isPending && <Group justify="center" py="xl"><Loader size="sm" /><Text>در حال دریافت اطلاعات…</Text></Group>}
      {isError && <Alert color="red" radius="md">دریافت اطلاعات ناموفق بود یا صورتحساب اصلی فعال وجود ندارد.</Alert>}
      {data && <>
        <Paper className="remaining-original" withBorder radius="md" p="sm">
          <Group justify="space-between" gap="xs">
            <Badge variant="light" size="lg">صورتحساب اصلی {data.original_invoice_id}</Badge>
            <Text size="sm" c="dimmed">بیمهٔ اصلی: <bdi>{money(data.original_insurance)}</bdi> ریال</Text>
          </Group>
        </Paper>
        <Paper className="remaining-cargo" withBorder radius="md" p="md">
          <Stack gap="sm">
            <Text fw={700} c="blue">اطلاعات بار باقی‌مانده</Text>
            <Select classNames={{ dropdown: 'remaining-goods-dropdown', option: 'remaining-colored-option' }} label="انتخاب کالا از تالی" placeholder="کالا را انتخاب کنید" searchable required value={source} onChange={selectGoods}
              radius="md" disabled={issue.isPending} data={data.goods.map(row => ({ value: String(row.id),
                label: `${row.description || 'کالا'} — HS ${row.hscode || '—'}${row.number_hamel ? ` — ${row.number_hamel}` : ''} — ردیف ${row.id}` }))} />
            <SimpleGrid cols={{ base: 1, xs: 2 }} spacing="sm">
              <TextInput label="HS Code" required radius="md" value={hscode} onChange={e => setHscode(e.currentTarget.value)} disabled={issue.isPending} maxLength={100} />
              <TextInput label="کد گروه کالا" required radius="md" value={code} onChange={e => setCode(e.currentTarget.value)} disabled={issue.isPending} maxLength={50} />
            </SimpleGrid>
            <SimpleGrid cols={{ base: 1, xs: 2, sm: 3 }} spacing="sm">
              <NumberInput label={volumetric ? 'تعداد پالت باقی‌مانده' : 'وزن باقی‌مانده (کیلوگرم)'} radius="md" placeholder="مقدار باقی‌مانده"
                value={amount} onChange={setAmount} min={0} decimalScale={4} required disabled={issue.isPending} />
              <NumberInput label="تعداد روز" radius="md" placeholder="مثلاً ۷" value={days} onChange={setDays} min={1}
                allowDecimal={false} required disabled={issue.isPending} />
              <NumberInput label="درصد بیمه باقی‌مانده" radius="md" value={percent} onChange={setPercent}
                min={0} max={100} decimalScale={4} suffix=" %" required disabled={issue.isPending} />
            </SimpleGrid>
            <Text size="xs" c="dimmed">تعداد روز عیناً در محاسبه اعمال می‌شود.</Text>
          </Stack>
        </Paper>
        <Paper className="remaining-services" withBorder radius="md" p="md">
          <Stack gap="sm">
            <Group justify="space-between">
              <Group gap="xs"><Text fw={700} c="violet">سایر خدمات</Text><Badge variant="light" color="violet">اختیاری</Badge></Group>
              <Button color="violet" variant="light" size="xs" radius="md" leftSection={<IconPlus size={16} />} disabled={issue.isPending || services.length >= 100}
                onClick={() => setServices(previous => [...previous, { key: requestId(), id: null, quantity: 1 }])}>افزودن خدمت</Button>
            </Group>
            {services.length === 0 && <Text size="sm" c="dimmed"></Text>}
            {services.map((row, index) => <Group key={row.key} align="flex-end" gap="sm" wrap="nowrap">
              <Select classNames={{ dropdown: 'remaining-services-dropdown', option: 'remaining-colored-option' }} label="خدمت" placeholder="انتخاب خدمت" searchable required radius="md" style={{ flex: 1, minWidth: 0 }} value={row.id}
                disabled={issue.isPending} data={data.other_services.map(service => ({ value: String(service.id), label: service.title }))}
                onChange={id => setServices(previous => previous.map(item => item.key === row.key ? { ...item, id } : item))} />
              <NumberInput label="تعداد" required radius="md" min={0} decimalScale={4} value={row.quantity} disabled={issue.isPending} w={100}
                onChange={quantity => setServices(previous => previous.map(item => item.key === row.key ? { ...item, quantity } : item))} />
              <Tooltip label="حذف خدمت" withArrow>
                <ActionIcon color="red" variant="light" radius="md" size={36} mb={1} style={{ flexShrink: 0 }} disabled={issue.isPending}
                  aria-label={`حذف خدمت ${index + 1}`} onClick={() => setServices(previous => previous.filter(item => item.key !== row.key))}>
                  <IconTrash size={18} />
                </ActionIcon>
              </Tooltip>
            </Group>)}
          </Stack>
        </Paper>
      </>}
      {calculate.isError && valid && key === debouncedKey && <Alert color="red" radius="md">
        {errorMessage(calculate.error, 'محاسبه انجام نشد')}
        <Button variant="subtle" size="xs" onClick={() => calculate.refetch()}>تلاش دوباره</Button>
      </Alert>}
      {current && !calculating && <Table.ScrollContainer minWidth={580}>
        <Table className="remaining-preview" striped verticalSpacing="sm"><Table.Thead><Table.Tr><Table.Th>شرح</Table.Th><Table.Th>تعداد</Table.Th><Table.Th>مبلغ (ریال)</Table.Th><Table.Th>نحوهٔ محاسبه</Table.Th></Table.Tr></Table.Thead>
          <Table.Tbody>{current.rows.map((row, index) => <Table.Tr key={index}>
            <Table.Td>{invoiceDescription(row.description) || '—'}</Table.Td><Table.Td>{row.quantity ?? '—'}</Table.Td><Table.Td><bdi>{money(row.price)}</bdi></Table.Td><Table.Td><Text size="xs" c="dimmed">{row.note}</Text></Table.Td>
          </Table.Tr>)}</Table.Tbody></Table>
      </Table.ScrollContainer>}
      {issue.isError && <Alert color="red" radius="md">{errorMessage(issue.error, 'صدور انجام نشد؛ دوباره تلاش کنید')}</Alert>}
      <Paper className="remaining-total" withBorder radius="md" p="md" aria-live="polite">
        <Group justify="space-between" mb="md">
          <div><Text fw={700}>مبلغ قابل پرداخت</Text><Text size="xs" c="dimmed"></Text></div>
          {calculating ? <Group gap="xs"><Loader size="xs" /><Text size="sm">در حال محاسبه…</Text></Group>
            : current ? <Text fw={800} size="lg" c="teal"><bdi>{money(current.total)}</bdi> ریال</Text>
            : <Text size="sm" c="dimmed">{valid ? 'مبلغ هنوز آماده نیست' : ''}</Text>}
        </Group>
        <Group justify="flex-end">
          <Button variant="default" radius="md" disabled={issue.isPending} onClick={close}>انصراف</Button>
          <Button color="teal" radius="md" loading={issue.isPending} disabled={!current || calculating || !valid}
            onClick={() => { if (current && !issue.isPending) issue.mutate() }}>صدور صورتحساب باقی‌مانده</Button>
        </Group>
      </Paper>
    </Stack>
  </Modal>
}
