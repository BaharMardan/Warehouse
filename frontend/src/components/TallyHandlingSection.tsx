import { useState, type Dispatch, type SetStateAction } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { Alert, Button, Group, Modal, Paper, Radio, Select, Stack, Text, TextInput, Title } from '@mantine/core'
import { Boxes, Plus } from 'lucide-react'
import { apiGet, apiSend, errorMessage } from '../api/client'
import { usePermissions } from '../auth/usePermissions'
import { useHandoff } from './TallyHandoff'
import { IranianPlate } from './IranianPlate'

type Kind = 'strip' | 'stuffing' | 'crane'
type Choice = 'normal' | 'non_standard' | 'dangerous' | 'unloading' | 'loading' | null
type ServiceRow = {
  id: number
  service_kind?: Kind
  parent_service_id?: number
  is_auto_excess?: boolean
  number_hamel: string | null
  pricing_type: Choice
  rate_id: number | null
  code: string | null
  rate_title: string | null
  rate_code?: string | null
  number_service: number | null
  description: string | null
  calculated_amount: number | null
}
type ServiceForm = {
  choice: Choice
  rateId: number | null
  code: string | null
  quantity: string
  description: string
}
const emptyForm = (): ServiceForm => ({ choice: null, rateId: null, code: null, quantity: '', description: '' })
const fromRow = (row?: ServiceRow): ServiceForm => row ? {
  choice: row.pricing_type,
  rateId: row.rate_id,
  code: row.code ?? row.rate_code ?? null,
  quantity: row.number_service == null ? '' : String(row.number_service),
  description: row.description ?? '',
} : emptyForm()
const labels: Record<string, string> = {
  normal: 'عادی', non_standard: 'غیراستاندارد', dangerous: 'خطرناک',
  unloading: 'تخلیه', loading: 'بارگیری',
}
const digits = (value: string) => value.replace(/[۰-۹]/g, (digit) => String(digit.charCodeAt(0) - 0x06f0))

export function TallyHandlingSection({ tallyId }: { tallyId: number }) {
  const qc = useQueryClient()
  const { data: handoff } = useHandoff(tallyId)
  const canEdit = usePermissions().can('tally.services') && handoff?.can_edit_services === true
  const [opened, setOpened] = useState(false)
  const [carrier, setCarrier] = useState<string | null>(null)
  const [strip, setStrip] = useState<ServiceForm>(emptyForm)
  const [stuffing, setStuffing] = useState<ServiceForm>(emptyForm)
  const [crane, setCrane] = useState<ServiceForm>(emptyForm)
  const [craneAnswer, setCraneAnswer] = useState<'yes' | 'no'>('no')
  const [transport, setTransport] = useState<string | null>(null)

  const { data: details = [] } = useQuery({
    queryKey: ['tally-details', tallyId],
    queryFn: () => apiGet<Array<{ number_hamel: string | null; weighte: number | null }>>(`/tally/${tallyId}/details`),
  })
  const { data: stripRows = [] } = useQuery({
    queryKey: ['tally-junction', 'strip', tallyId],
    queryFn: () => apiGet<ServiceRow[]>(`/tally/${tallyId}/strip`),
  })
  const { data: stuffingRows = [] } = useQuery({
    queryKey: ['tally-junction', 'stuffing', tallyId],
    queryFn: () => apiGet<ServiceRow[]>(`/tally/${tallyId}/stuffing`),
  })
  const { data: craneRows = [] } = useQuery({
    queryKey: ['tally-junction', 'crane', tallyId],
    queryFn: () => apiGet<ServiceRow[]>(`/tally/${tallyId}/crane`),
  })
  const { data: transportationRows = [] } = useQuery({
    queryKey: ['tally-transportation', tallyId],
    queryFn: () => apiGet<Array<{ number_hamel: string; has_transportation: string }>>(`/tally/${tallyId}/transportation`),
  })
  const { data: settings = [] } = useQuery({
    queryKey: ['app-settings'],
    queryFn: () => apiGet<Array<{ key: string; value_number: string }>>('/settings'),
  })
  const { data: catalog = [] } = useQuery({
    queryKey: ['refselect', '/kala-strip', null],
    queryFn: () => apiGet<Array<{ id_kala_strip: number; code: string | null; title: string | null; normal: string | null; non_standard: string | null; dangerous: string | null }>>('/kala-strip'),
  })
  const freightRate = settings.find((item) => item.key === 'freight_rate')?.value_number
  const carriers = [...new Set(details.map((row) => row.number_hamel?.trim()).filter((value): value is string => Boolean(value)))]
  const carrierOptions = carriers.map((value) => ({ value, label: value }))
  const declaredWeight = details.filter((row) => row.number_hamel === carrier).reduce((sum, row) => sum + Number(row.weighte ?? 0), 0)
  const transportationFor = (number: string | null) => transportationRows.find((row) => row.number_hamel === number)?.has_transportation ?? null

  function openFor(selected: string | null) {
    setCarrier(selected)
    setStrip(fromRow(stripRows.find((row) => row.number_hamel === selected && !row.is_auto_excess)))
    setStuffing(fromRow(stuffingRows.find((row) => row.number_hamel === selected && !row.is_auto_excess)))
    const craneRow = craneRows.find((row) => row.number_hamel === selected && !row.is_auto_excess)
    setCrane(fromRow(craneRow))
    setCraneAnswer(craneRow ? 'yes' : 'no')
    setTransport(transportationFor(selected) ?? 'no')
    setOpened(true)
  }

  async function saveService(kind: Kind, form: ServiceForm) {
    const rows = await apiGet<ServiceRow[]>(`/tally/${tallyId}/${kind}`)
    const existing = rows.find((row) => row.number_hamel === carrier && !row.is_auto_excess)
    if (!form.choice) {
      if (existing) await apiSend(`/tali-kala-strip/${existing.id}`, 'DELETE')
      return
    }
    const automatic = form.choice === 'unloading' || form.choice === 'loading'
    const payload = {
      tali_id: tallyId,
      service_kind: kind,
      number_hamel: carrier,
      pricing_type: form.choice,
      kala_strip_id: automatic ? null : form.rateId,
      code: automatic ? null : form.code,
      number_service: automatic ? null : form.code === '201' || form.code === '401' ? 1 : !form.quantity ? null : Number(digits(form.quantity)),
      description: form.description.trim() || null,
    }
    await apiSend(existing ? `/tali-kala-strip/${existing.id}` : '/tali-kala-strip', existing ? 'PUT' : 'POST', payload)
  }

  const save = useMutation({
    mutationFn: async () => {
      await saveService('strip', strip)
      await saveService('stuffing', stuffing)
      await saveService('crane', craneAnswer === 'yes' ? crane : emptyForm())
      if (transport !== transportationFor(carrier) && transport) {
        await apiSend(`/tally/${tallyId}/transportation`, 'PUT', { number_hamel: carrier, has_transportation: transport })
      }
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['tally-junction', 'strip', tallyId] })
      qc.invalidateQueries({ queryKey: ['tally-junction', 'stuffing', tallyId] })
      qc.invalidateQueries({ queryKey: ['tally-junction', 'crane', tallyId] })
      qc.invalidateQueries({ queryKey: ['tally-transportation', tallyId] })
      qc.invalidateQueries({ queryKey: ['invoice-preview'] })
      setOpened(false)
    },
  })

  const valid = Boolean(carrier) && Boolean(transport) &&
    [strip, stuffing].every((form) => !form.choice || form.choice === 'unloading' || form.choice === 'loading' || form.rateId != null) &&
    (craneAnswer === 'no' || (crane.rateId != null && (crane.choice === 'normal' || crane.choice === 'non_standard' || crane.choice === 'dangerous')))

  function serviceBox(kind: Kind, form: ServiceForm, setForm: Dispatch<SetStateAction<ServiceForm>>) {
    const automatic = kind === 'strip' ? 'unloading' : 'loading'
    const title = kind === 'strip' ? 'استریپ یا تخلیه' : 'استافینگ یا بارگیری'
    const isAutomatic = form.choice === automatic
    const capacity = form.code === '201' ? 10000 : form.code === '401' ? 15000 : null
    const excess = capacity == null ? 0 : Math.max(0, (declaredWeight - capacity) / 1000)
    const excessCode = form.code === '201' ? '202' : form.code === '401' ? '402' : null
    const excessTitle = catalog.find((row) => row.code === excessCode)?.title ?? (form.code === '201' ? 'مازاد بر ۱۰ تن کانتینر ۲۰ فوت' : 'مازاد بر ۱۵ تن کانتینر ۴۰ فوت')
    return <Paper withBorder radius="md" p="md">
      <Stack gap="sm">
        <Text fw={700}>{title}</Text>
        <Select
          label={`انتخاب ${title}`}
          placeholder="انتخاب کنید"
          data={[
            ...catalog.map((row) => ({ value: String(row.id_kala_strip), label: `${row.code ?? ''} ${row.title ? `(${row.title})` : ''}`.trim(), disabled: row.code === '202' || row.code === '402' })),
            { value: automatic, label: labels[automatic] },
          ]}
          value={isAutomatic ? automatic : form.rateId == null ? null : String(form.rateId)}
          onChange={(value) => {
            if (value === automatic) setForm({ ...form, choice: automatic, rateId: null, code: null, quantity: '' })
            else if (value) {
              const row = catalog.find((item) => String(item.id_kala_strip) === value)
              setForm({ ...form, choice: form.choice === 'normal' || form.choice === 'non_standard' || form.choice === 'dangerous' ? form.choice : 'normal', rateId: Number(value), code: row?.code ?? null })
            } else setForm(emptyForm())
          }}
          clearable
        />
        {form.choice && !isAutomatic && <>
          <Select
            label="نوع قیمت"
            data={[{ value: 'normal', label: labels.normal }, { value: 'non_standard', label: labels.non_standard }, { value: 'dangerous', label: labels.dangerous }]}
            value={form.choice}
            onChange={(value) => setForm({ ...form, choice: value as Choice })}
            allowDeselect={false}
          />
          {(form.code === '201' || form.code === '401')
            ? <Text size="sm" c="dimmed">تعداد کانتینر: ۱. {excess > 0 ? `${excessTitle}: ${excess.toLocaleString('fa-IR')} تن (${labels[form.choice ?? '']})` : 'مازاد وزن ندارد.'}</Text>
            : <TextInput label="تعداد" inputMode="numeric" value={form.quantity} onChange={(event) => setForm({ ...form, quantity: event.currentTarget.value })} />}
        </>}
        {form.choice === automatic && <Text size="sm" c="dimmed">مبلغ از نرخ گروه کالا × وزن اظهارِ حامل انتخاب‌شده محاسبه می‌شود.</Text>}
        {form.choice && <TextInput label="توضیحات" value={form.description} onChange={(event) => setForm({ ...form, description: event.currentTarget.value })} />}
      </Stack>
    </Paper>
  }

  function craneBox() {
    const size = crane.code === '201' ? '20' : crane.code === '401' ? '40' : null
    const excessCode = size === '20' ? '202' : size === '40' ? '402' : null
    const excess = size === '20' ? Math.max(0, (declaredWeight - 10000) / 1000)
      : size === '40' ? Math.max(0, (declaredWeight - 15000) / 1000) : 0
    const mainRate = catalog.find((row) => row.code === crane.code)
    const excessRate = catalog.find((row) => row.code === excessCode)
    const rateField = crane.choice === 'dangerous' ? 'dangerous' : crane.choice === 'non_standard' ? 'non_standard' : 'normal'
    return <Paper withBorder radius="md" p="md">
      <Stack gap="sm">
        <Text fw={700}>آیا جابه‌جایی کانتینر با جرثقیل انجام می‌شود؟</Text>
        <Radio.Group value={craneAnswer} onChange={(value) => {
          if (value === 'yes' || value === 'no') {
            setCraneAnswer(value)
            if (value === 'no') setCrane(emptyForm())
          }
        }}><Group><Radio value="yes" label="بله" /><Radio value="no" label="خیر" /></Group></Radio.Group>
        {craneAnswer === 'yes' && <>
          <Select label="اندازه کانتینر" placeholder="انتخاب کنید"
            data={[{ value: '20', label: 'کانتینر ۲۰ فوت' }, { value: '40', label: 'کانتینر ۴۰ فوت' }]}
            value={size} onChange={(value) => {
              const row = catalog.find((item) => item.code === (value === '20' ? '201' : value === '40' ? '401' : null))
              setCrane({ ...crane, rateId: row?.id_kala_strip ?? null, code: row?.code ?? null, choice: crane.choice ?? 'normal', quantity: '1' })
            }} allowDeselect={false} />
          <Select label="نوع بار" data={[
            { value: 'normal', label: labels.normal },
            { value: 'non_standard', label: labels.non_standard },
            { value: 'dangerous', label: labels.dangerous },
          ]} value={crane.choice} onChange={(value) => setCrane({ ...crane, choice: value as Choice })} allowDeselect={false} />
          {size && <Text size="sm" c="dimmed">نرخ اصلی: {mainRate?.[rateField] == null ? 'ثبت نشده' : `${Number(mainRate[rateField]).toLocaleString('fa-IR')} ریال`}
            {excess > 0 && ` · مازاد: ${excess.toLocaleString('fa-IR')} تن × ${excessRate?.[rateField] == null ? 'نرخ ثبت نشده' : `${Number(excessRate[rateField]).toLocaleString('fa-IR')} ریال`}`}
          </Text>}
        </>}
      </Stack>
    </Paper>
  }

  return <Paper className="tally-detail-section tally-detail-junction-section" radius="xl" dir="rtl">
    <div className="tally-detail-section-header">
      <div className="tally-detail-section-heading">
        <span className="tally-detail-section-icon" aria-hidden><Boxes size={22} /></span>
        <div><Title order={3}>استریپ، استافینگ، جرثقیل و باربری</Title><Text>خدمات هر حامل را در یک پنجره ثبت کنید</Text></div>
      </div>
      {canEdit && <Button className="tally-detail-add-button" size="sm" leftSection={<Plus size={17} />} onClick={() => openFor(null)}>افزودن</Button>}
    </div>
    <div className="tally-detail-section-rule" />
    <Stack p="md" gap="xs">
      {carriers.length === 0 && <Text c="dimmed">ابتدا شماره حامل را در ردیف‌های کالا ثبت کنید.</Text>}
      {carriers.map((number) => {
        const stripRow = stripRows.find((row) => row.number_hamel === number && !row.is_auto_excess)
        const stuffingRow = stuffingRows.find((row) => row.number_hamel === number && !row.is_auto_excess)
        const craneRow = craneRows.find((row) => row.number_hamel === number && !row.is_auto_excess)
        const excessRows = [...stripRows, ...stuffingRows, ...craneRows].filter((row) => row.number_hamel === number && row.is_auto_excess)
        return <div className="tally-handling-carrier-row" key={number}>
          <Group className="tally-handling-carrier-details" gap="md"><IranianPlate value={number} /><Text size="sm" fw={600}>باربری: {transportationFor(number) === 'yes' ? 'بله' : transportationFor(number) === 'no' ? 'خیر' : 'ثبت نشده'}</Text><Text size="sm">استریپ/تخلیه: {stripRow?.rate_title ?? (stripRow ? labels[stripRow.pricing_type ?? ''] : '—')}</Text><Text size="sm">استافینگ/بارگیری: {stuffingRow?.rate_title ?? (stuffingRow ? labels[stuffingRow.pricing_type ?? ''] : '—')}</Text><Text size="sm">جرثقیل: {craneRow ? `${craneRow.rate_title ?? 'کانتینر'} (${labels[craneRow.pricing_type ?? '']})` : 'خیر'}</Text>{excessRows.map((row) => <Text key={`${row.parent_service_id}-${row.rate_code}`} size="sm" c="blue">{row.service_kind === 'strip' ? 'استریپ' : row.service_kind === 'stuffing' ? 'استافینگ' : 'جرثقیل'}: {row.rate_title}: {Number(row.number_service).toLocaleString('fa-IR')} تن ({labels[row.pricing_type ?? '']})</Text>)}</Group>
          {canEdit && <Button size="xs" variant="light" onClick={() => openFor(number)}>ویرایش خدمات</Button>}
        </div>
      })}
    </Stack>
    <Modal opened={opened} onClose={() => setOpened(false)} title="افزودن استریپ یا استافینگ" size="lg" centered classNames={{ content: 'tally-detail-modal', header: 'tally-detail-modal-header', body: 'tally-detail-modal-body', title: 'tally-detail-modal-title' }}>
      <div className="tally-detail-modal-form" dir="rtl">
      <Stack className="tally-detail-modal-scroll" gap="md">
        <Select label="شماره حامل" placeholder="از شماره‌حامل‌های ثبت‌شده انتخاب کنید" data={carrierOptions} value={carrier} onChange={(value) => {
          setCarrier(value)
          setStrip(fromRow(stripRows.find((row) => row.number_hamel === value && !row.is_auto_excess)))
          setStuffing(fromRow(stuffingRows.find((row) => row.number_hamel === value && !row.is_auto_excess)))
          const craneRow = craneRows.find((row) => row.number_hamel === value && !row.is_auto_excess)
          setCrane(fromRow(craneRow))
          setCraneAnswer(craneRow ? 'yes' : 'no')
          setTransport(transportationFor(value) ?? 'no')
        }} renderOption={({ option }) => <IranianPlate value={option.value} />} searchable />
        {serviceBox('strip', strip, setStrip)}
        {serviceBox('stuffing', stuffing, setStuffing)}
        {craneBox()}
        <Paper withBorder radius="md" p="md"><Stack gap="sm"><Text fw={700}>آیا بار شامل باربری می‌شود؟</Text><Radio.Group value={transport ?? ''} onChange={setTransport}><Group><Radio value="yes" label="بله" /><Radio value="no" label="خیر" /></Group></Radio.Group>{transport === 'yes' && <Text size="sm" c="dimmed">نرخ ثابت از تنظیمات: {freightRate == null ? '—' : `${Number(freightRate).toLocaleString('fa-IR')} ریال`}</Text>}</Stack></Paper>
        {save.isError && <Alert color="red">{errorMessage(save.error, 'ثبت خدمات ناموفق بود.')}</Alert>}
      </Stack>
      <Group className="tally-detail-modal-actions" justify="flex-start"><Button onClick={() => save.mutate()} loading={save.isPending} disabled={!valid}>ذخیره</Button><Button variant="default" onClick={() => setOpened(false)}>لغو</Button></Group>
      </div>
    </Modal>
  </Paper>
}
