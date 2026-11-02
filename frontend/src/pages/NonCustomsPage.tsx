import { useEffect, useState, type FormEvent } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { Alert, Button, Checkbox, Group, Modal, NumberInput, Paper, Select, SimpleGrid, Stack, Table, Tabs, Text, TextInput, Title } from '@mantine/core'
import { Link } from 'react-router-dom'
import { normalizeSearchDigits } from '../utils/normalizeSearchDigits'
import { apiGet, apiSend, errorMessage } from '../api/client'
import { usePermissions } from '../auth/usePermissions'
import { BackButton } from '../components/BackButton'
import { PageHeader } from '../components/PageHeader'
import { JalaliDate } from '../components/JalaliDate'
import { StockReport } from '../components/reports/StockReport'
import { jalali } from '../components/reports/reportFormat'
import { RemainingInvoiceModal } from '../components/RemainingInvoiceModal'

// Normalize typing and pasted text before NumberInput parses the value.
function normalizeNumberInput(event: FormEvent<HTMLInputElement>) {
  const input = event.target as HTMLInputElement
  const normalized = normalizeSearchDigits(input.value).replace(/٫/g, '.').replace(/٬/g, ',')
  if (normalized === input.value) return
  const start = input.selectionStart
  const end = input.selectionEnd
  input.value = normalized
  if (start != null && end != null) input.setSelectionRange(start, end)
}

type Row = { row_number: number; zarib_mahal: string | null; receipt_id: number; source_id: number; tally_id: number; tally_number: string; receipt_number: string; invoice_id: number; invoice_active: number; owner_name: string; description: string; hscode: string; cargo: string; weight: string; quantity: string; pallets: string; start_date: string }
type Stock = { items: Row[]; totals: { weight: string; quantity: string; pallets: string } }
const fmt = (n: string | number) => Number(n).toLocaleString('en-US', { maximumFractionDigits: 4 })
const rowKey = (r: Row) => `${r.receipt_id}:${r.source_id}`
type AmountValues = { weight: string; quantity: string; pallets: string }
type DraftRow = AmountValues & { key: number; selection: string | null }
const emptyAmounts = (): AmountValues => ({ weight: '', quantity: '', pallets: '' })
const emptyDraft = (key: number): DraftRow => ({ key, selection: null, ...emptyAmounts() })
export function NonCustomsPage() {
  const { can } = usePermissions()
  const qc = useQueryClient()
  const [activeTab, setActiveTab] = useState<string | null>(can('non_customs.stock') ? 'inventory' : 'operations')
  useEffect(() => {
    if (activeTab === 'inventory' && !can('non_customs.stock')) setActiveTab(can('non_customs.operations') ? 'operations' : null)
    if (activeTab === 'operations' && !can('non_customs.operations')) setActiveTab(can('non_customs.stock') ? 'inventory' : null)
  }, [activeTab, can])
  const [registerOpen, setRegisterOpen] = useState(false)
  const [exitRow, setExitRow] = useState<Row | null>(null)
  const [billing, setBilling] = useState<number | null>(null)
  const [search, setSearch] = useState('')
  const stock = useQuery({ queryKey: ['non-customs'], queryFn: () => apiGet<Stock>('/non-customs'), enabled: can('non_customs.operations') && activeTab === 'operations' })
  const candidates = useQuery({ queryKey: ['non-customs-candidates'], queryFn: () => apiGet<Row[]>('/non-customs/candidates'), enabled: registerOpen && can('non_customs.operations') })
  const [selectedTally, setSelectedTally] = useState<string | null>(null)
  const [drafts, setDrafts] = useState<DraftRow[]>([emptyDraft(0)])
  const updateDraft = (key: number, change: Partial<DraftRow>) => setDrafts(previous => previous.map(row => row.key === key ? { ...row, ...change } : row))
  const tallyOptions = Array.from(new Map((candidates.data ?? []).map(row => [String(row.tally_id), {
    value: String(row.tally_id), label: `${row.tally_number} — ${row.owner_name || 'بدون نام'}`,
  }])).values())
  const tallyRows = (candidates.data ?? []).filter(row => String(row.tally_id) === selectedTally)
  const findSource = (draft: DraftRow) => tallyRows.find(row => rowKey(row) === draft.selection)
  const validDrafts = drafts.length > 0 && drafts.every(draft => {
    const source = findSource(draft)
    if (!source) return false
    const basis = ['yes', 'volumetric'].includes(source.cargo) ? 'pallets' : 'weight'
    return Number(draft[basis]) > 0 && (['weight', 'quantity', 'pallets'] as const).every(k =>
      Number.isFinite(Number(draft[k])) && Number(draft[k]) >= 0 && Number(draft[k]) <= Number(source[k]))
  }) && new Set(drafts.map(row => row.selection)).size === drafts.length
  const [amounts, setAmounts] = useState({ weight: '', quantity: '', pallets: '' })
  const [start, setStart] = useState('')
  const today = useQuery({ queryKey: ['non-customs-today'], queryFn: () => apiGet<{ today: string }>('/non-customs/today'), enabled: registerOpen, staleTime: 0 })
  useEffect(() => {
    if (registerOpen && today.data?.today) setStart(current => current || today.data.today)
  }, [registerOpen, today.data])
  const [settled, setSettled] = useState(false)
  const [request, setRequest] = useState('')
  const close = () => { setRegisterOpen(false); setExitRow(null) }
  const save = useMutation({
    mutationFn: () => {
      if (exitRow) return apiSend(`/non-customs/receipts/${exitRow.receipt_id}/rows/${exitRow.source_id}/exit`, 'POST', {
        ...Object.fromEntries(Object.entries(amounts).map(([k,v]) => [k, v || '0'])), request_id: request,
      })
      if (!selectedTally || !validDrafts) throw new Error('تالی، ردیف‌ها و مقادیر را بررسی کنید')
      return apiSend(`/non-customs/tallies/${selectedTally}/rows`, 'POST', {
        start_date: start, settlement_confirmed: settled,
        rows: drafts.map(draft => {
          const source = findSource(draft)!
          return { receipt_id: source.receipt_id, source_id: source.source_id,
            weight: draft.weight || '0', quantity: draft.quantity || '0', pallets: draft.pallets || '0' }
        }),
      })
    },
    onSuccess: async () => { close(); await qc.invalidateQueries({ queryKey: ['non-customs'] }); await qc.invalidateQueries({ queryKey: ['non-customs-candidates'] }); await qc.invalidateQueries({ queryKey: ['reports', 'non-customs-stock'] }); await qc.invalidateQueries({ queryKey: ['remaining-options'] }) },
  })
  function reset() { setAmounts({ weight: '', quantity: '', pallets: '' }); save.reset(); setSelectedTally(null); setDrafts([emptyDraft(0)]); setSettled(false); setStart('') }
  const rows = stock.data?.items.filter(r => `${r.tally_number} ${r.owner_name} ${r.description} ${r.hscode}`.includes(search)) ?? []
  return <Stack dir="rtl">
    <PageHeader title="انبار غیر گمرکی" actions={<BackButton to="/" />} />
    <Alert>کالای ترخیص‌شده و تسویه‌شده که هنوز در انبار است، اینجا ثبت می‌شود. موجودی این بخش را با موجودی گزارش‌گیری جمع کنید. صدور صورتحساب موجودی را کم نمی‌کند؛ خروج فیزیکی باید جدا ثبت شود.</Alert>
    {!can('non_customs.stock') && !can('non_customs.operations') && <Alert color="yellow">دسترسی تب موجودی انبار یا عملیات برای شما تعریف نشده است.</Alert>}
    <Tabs color="navy" value={activeTab} onChange={setActiveTab}>
      <Tabs.List mb="lg">
        {can('non_customs.stock') && <Tabs.Tab value="inventory">موجودی انبار</Tabs.Tab>}
        {can('non_customs.operations') && <Tabs.Tab value="operations">عملیات</Tabs.Tab>}
      </Tabs.List>
      {can('non_customs.stock') && <Tabs.Panel value="inventory">
        {can('non_customs.stock') ? <StockReport from="" to="" enabled={activeTab === 'inventory'} nonCustoms /> :
          <Text>برای مشاهده موجودی به دسترسی گزارش موجودی انبار نیاز دارید.</Text>}
      </Tabs.Panel>}
      {can('non_customs.operations') && <Tabs.Panel value="operations">
        <Stack>
          <Group justify="space-between">
            <Title order={4}>عملیات کالاهای انبار غیر گمرکی</Title>
            {can('non_customs.operations') && <Button onClick={() => { reset(); setRegisterOpen(true) }}>افزودن کالای باقی‌مانده</Button>}
          </Group>
          {stock.isPending && can('non_customs.operations') && <Text>در حال دریافت کالاها…</Text>}
          {stock.isError && <Alert color="red">دریافت کالاها ناموفق بود.</Alert>}
    {stock.data && <>
      <TextInput label="جستجو در کالاها" value={search} onChange={e => setSearch(e.currentTarget.value)} />
      <Table.ScrollContainer minWidth={1000}><Table striped withTableBorder><Table.Thead><Table.Tr>{['تالی / قبض', 'صاحب کالا', 'کالا / HS', 'شروع دوره', 'وزن (کیلوگرم)', 'تعداد', 'پالت', 'عملیات'].map(s => <Table.Th key={s}>{s}</Table.Th>)}</Table.Tr></Table.Thead><Table.Tbody>
        {rows.map(r => <Table.Tr key={rowKey(r)}><Table.Td><Link to={`/tally/id/${r.tally_id}`}>{r.tally_number}</Link> / {r.receipt_number}</Table.Td><Table.Td>{r.owner_name}</Table.Td><Table.Td>{r.description} / {r.hscode}</Table.Td><Table.Td>{jalali(r.start_date)}</Table.Td><Table.Td>{fmt(r.weight)}</Table.Td><Table.Td>{fmt(r.quantity)}</Table.Td><Table.Td>{fmt(r.pallets)}</Table.Td><Table.Td><Group>
          {can('invoice.issue') && r.invoice_active === 1 && <Button size="xs" onClick={() => setBilling(r.receipt_id)}>صدور صورتحساب باقی‌مانده</Button>}
          {r.invoice_active !== 1 && <Text c="red">صورتحساب اصلی باطل شده؛ بررسی لازم است</Text>}
          {can('non_customs.operations') && <Button size="xs" variant="light" onClick={() => { reset(); setRequest(crypto.randomUUID()); setExitRow(r) }}>ثبت خروج</Button>}
        </Group></Table.Td></Table.Tr>)}
        {!rows.length && <Table.Tr><Table.Td colSpan={8}>کالایی در این فهرست موجود نیست.</Table.Td></Table.Tr>}
      </Table.Tbody></Table></Table.ScrollContainer>
    </>}
        </Stack>
      </Tabs.Panel>}
    </Tabs>
    <Modal opened={registerOpen || !!exitRow} onClose={() => { if (!save.isPending) close() }} title={exitRow ? 'ثبت خروج فیزیکی کالا' : 'افزودن به انبار غیر گمرکی'} dir="rtl" size={exitRow ? "md" : "xl"} closeOnClickOutside={!save.isPending} withCloseButton={!save.isPending}>
      <Stack>
        {!exitRow && <>
          <Text size="sm">ابتدا تالی را انتخاب کنید، سپس ردیف‌های باقی‌مانده و مقدار هرکدام را وارد کنید.</Text>
          {candidates.isPending && <Text>در حال دریافت فهرست…</Text>}{candidates.isError && <Alert color="red">دریافت فهرست ناموفق بود.</Alert>}
          <Select searchable required label="انتخاب تالی" placeholder="شماره تالی یا نام صاحب کالا" value={selectedTally}
            disabled={save.isPending} onChange={value => { setSelectedTally(value); setDrafts([emptyDraft(0)]); save.reset() }} data={tallyOptions} />
          {candidates.data && !tallyOptions.length && <Text size="sm">تالی دارای ردیف قابل ثبت یافت نشد.</Text>}
          {selectedTally && <>
            {drafts.map((draft, index) => {
              const source = findSource(draft)
              return <Paper key={draft.key} withBorder p="md" radius="md"><Stack gap="sm">
                <Group justify="space-between"><Text fw={600}>ردیف {index + 1}</Text>
                  <Button variant="subtle" color="red" size="xs" disabled={save.isPending}
                    onClick={() => setDrafts(previous => previous.filter(row => row.key !== draft.key))}>حذف ردیف</Button></Group>
                <Select searchable clearable required label="ردیف باقی‌مانده از تالی" placeholder="کالا را انتخاب کنید" value={draft.selection}
                  disabled={save.isPending} onChange={value => updateDraft(draft.key, { selection: value, ...emptyAmounts() })}
                  data={tallyRows.filter(row => rowKey(row) === draft.selection || !drafts.some(other => other.selection === rowKey(row))).map(row => ({
                    value: rowKey(row), label: `${row.description || 'کالا'} — HS ${row.hscode || '—'} — قبض ${row.receipt_number} — ردیف ${fmt(row.row_number)} — ضریب محل: ${row.zarib_mahal || 'نامشخص'}`,
                  }))} />
                {source && <Text size="sm">حداکثر: {fmt(source.weight)} کیلوگرم، {fmt(source.quantity)} عدد، {fmt(source.pallets)} پالت</Text>}
                <SimpleGrid cols={{ base: 1, sm: 3 }}>
                  {(['weight', 'quantity', 'pallets'] as const).map((k,i) => <NumberInput key={k} onChangeCapture={normalizeNumberInput} thousandSeparator="," inputMode="decimal" label={['وزن باقی‌مانده (کیلوگرم)', 'تعداد کالای باقی‌مانده', 'تعداد پالت باقی‌مانده'][i]}
                    value={draft[k]} disabled={!source || save.isPending} min={0} max={source ? Number(source[k]) : undefined} decimalScale={4}
                    onChange={v => updateDraft(draft.key, { [k]: String(v) })} />)}
                </SimpleGrid>
              </Stack></Paper>
            })}
            {drafts.some(draft => !draft.selection) && tallyRows.every(row => drafts.some(draft => draft.selection === rowKey(row))) &&
              <Alert color="yellow">تمام ردیف‌های قابل ثبت این تالی انتخاب شده‌اند. ردیف خالی را حذف کنید یا انتخاب یکی از ردیف‌های قبلی را تغییر دهید.</Alert>}
            <Button variant="light" disabled={save.isPending || drafts.length >= 100}
              onClick={() => setDrafts(previous => [...previous, emptyDraft(Math.max(-1, ...previous.map(row => row.key)) + 1)])}>افزودن ردیف دیگر</Button>
          </>}
          <div style={{ pointerEvents: save.isPending ? 'none' : undefined }}>
            <JalaliDate label="شروع دوره انبارداری مجدد برای ردیف‌های انتخاب‌شده" value={start || null} onChange={value => setStart(value || '')} />
          </div>
          {today.isError && <Text c="red" size="sm">دریافت تاریخ امروز ناموفق بود؛ تاریخ شروع را انتخاب کنید.</Text>}
          <Checkbox label="تسویه صورتحساب اصلی و باقی‌ماندن فیزیکی کالاهای انتخاب‌شده را تأیید می‌کنم" checked={settled} disabled={save.isPending} onChange={e => setSettled(e.currentTarget.checked)} />
        </>}
        {exitRow && <>
          <Text size="sm">حداکثر: {fmt(exitRow.weight)} کیلوگرم، {fmt(exitRow.quantity)} عدد، {fmt(exitRow.pallets)} پالت</Text>
          {(['weight', 'quantity', 'pallets'] as const).map((k,i) => <NumberInput key={k} onChangeCapture={normalizeNumberInput} thousandSeparator="," inputMode="decimal" label={['وزن (کیلوگرم)', 'تعداد کالا', 'تعداد پالت'][i]}
            value={amounts[k]} disabled={save.isPending} min={0} max={Number(exitRow[k])} decimalScale={4} onChange={v => setAmounts(a => ({ ...a, [k]: String(v) }))} />)}
        </>}
        {save.isError && <Alert color="red">{errorMessage(save.error, 'ثبت انجام نشد؛ اطلاعات و موجودی را بررسی کنید.')}</Alert>}
        <Button loading={save.isPending} disabled={!exitRow && (!selectedTally || !validDrafts || !settled || !start)} onClick={() => save.mutate()}>{exitRow ? 'ثبت خروج' : `ثبت ${drafts.length.toLocaleString('en-US')} ردیف`}</Button>
      </Stack>
    </Modal>
    {billing !== null && <RemainingInvoiceModal receiptId={billing} nonCustoms close={() => setBilling(null)} />}
  </Stack>
}
