// import { useState, useEffect } from 'react'
// import { useNavigate, useParams } from 'react-router-dom'
// import { useQuery } from '@tanstack/react-query'
// import { Title, Paper, Grid, TextInput, Group, Button, LoadingOverlay } from '@mantine/core'
// import { RefSelect } from '../components/RefSelect'
// import { JalaliDate } from '../components/JalaliDate'
// import { apiSend, apiGet } from '../api/client'

// type GhabzState = {
//   number_ghabz: string
//   number_karaneh: string
//   number_tali: string
//   date_unloading: string | null
//   date_enter_marze: string | null
//   id_marze: number | null
//   id_country: number | null
//   id_company: number | null
//   id_product_ownear: number | null
//   id_anbar: number | null
//   id_tagh_anbara: number | null
//   weight: string
//   status_bimeh: string
//   number_bimeh: string
//   name_anbardar: string
//   name_maneger: string
//   tali_id: number | null
// }

// const EMPTY: GhabzState = {
//   number_ghabz: '', number_karaneh: '', number_tali: '', date_unloading: null,
//   date_enter_marze: null, id_marze: null, id_country: null, id_company: null,
//   id_product_ownear: null, id_anbar: null, id_tagh_anbara: null, weight: '',
//   status_bimeh: '', number_bimeh: '', name_anbardar: '', name_maneger: '',
//   tali_id: null,
// }

// function normalizeDigits(s: string): string {
//   return s.replace(/[\u06F0-\u06F9]/g, (d) => String(d.charCodeAt(0) - 0x06f0))
//           .replace(/[\u0660-\u0669]/g, (d) => String(d.charCodeAt(0) - 0x0660))
// }

// function toPayload(s: GhabzState) {
//   const numOrNull = (v: string) => (v.trim() === '' ? null : Number(normalizeDigits(v)))
//   const strOrNull = (v: string) => (v.trim() === '' ? null : v)
//   const codeOrNull = (v: string) => strOrNull(normalizeDigits(v))
//   return {
//     number_ghabz: numOrNull(s.number_ghabz),
//     number_karaneh: codeOrNull(s.number_karaneh),
//     number_tali: numOrNull(s.number_tali),
//     date_unloading: s.date_unloading,
//     date_enter_marze: s.date_enter_marze,
//     id_marze: s.id_marze, id_country: s.id_country, id_company: s.id_company,
//     id_product_ownear: s.id_product_ownear, id_anbar: s.id_anbar, id_tagh_anbara: s.id_tagh_anbara,
//     weight: strOrNull(s.weight), status_bimeh: strOrNull(s.status_bimeh),
//     number_bimeh: codeOrNull(s.number_bimeh), name_anbardar: strOrNull(s.name_anbardar),
//     name_maneger: strOrNull(s.name_maneger),
//     tali_id: s.tali_id,
//   }
// }

// function rowToState(r: Record<string, any>): GhabzState {
//   const s = (v: any) => (v == null ? '' : String(v))
//   return {
//     number_ghabz: s(r.number_ghabz), number_karaneh: s(r.number_karaneh),
//     number_tali: s(r.number_tali), date_unloading: r.date_unloading ?? null,
//     date_enter_marze: r.date_enter_marze ?? null, id_marze: r.id_marze ?? null,
//     id_country: r.id_country ?? null, id_company: r.id_company ?? null,
//     id_product_ownear: r.id_product_ownear ?? null, id_anbar: r.id_anbar ?? null,
//     id_tagh_anbara: r.id_tagh_anbara ?? null, weight: s(r.weight),
//     status_bimeh: s(r.status_bimeh), number_bimeh: s(r.number_bimeh),
//     name_anbardar: s(r.name_anbardar), name_maneger: s(r.name_maneger),
//     tali_id: r.tali_id ?? null,
//   }
// }

// const companyLabel = (r: Record<string, any>) =>
//   `${r.name ?? ''} ${r.family ?? ''} ${r.national_code ? `(${r.national_code})` : ''}`.trim()
// const ownerLabel = (r: Record<string, any>) => `${r.name ?? ''} ${r.family ?? ''}`.trim()
// const tallyLabel = (r: Record<string, any>) =>
//   `تالی ${r.tali_number ?? r.id_tali}${r.number_karaneh ? ` — کارنه ${r.number_karaneh}` : ''}`.trim()

// export function GhabzHeaderForm() {
//   const navigate = useNavigate()
//   const { id } = useParams<{ id: string }>()
//   const isEdit = id != null
//   const editId = isEdit ? Number(id) : null
//   const [form, setForm] = useState<GhabzState>(EMPTY)
//   const [saving, setSaving] = useState(false)
//   const [error, setError] = useState<string | null>(null)

//   const { data: existing } = useQuery({
//     queryKey: ['ghabz-header', editId],
//     queryFn: () => apiGet<Record<string, any>>(`/ghabz-header/${editId}`),
//     enabled: isEdit,
//   })
//   useEffect(() => { if (existing) setForm(rowToState(existing)) }, [existing])

//   const set = <K extends keyof GhabzState>(k: K, v: GhabzState[K]) => setForm((f) => ({ ...f, [k]: v }))

//   async function handleSave() {
//     if (!isEdit && form.tali_id == null) {
//       setError('انتخاب تالی برای صدور قبض الزامی است.')
//       return
//     }
//     setSaving(true); setError(null)
//     try {
//       if (isEdit) {
//         await apiSend(`/ghabz-header/${editId}`, 'PUT', toPayload(form))
//         navigate(`/ghabz/${editId}`)
//       } else {
//         const created = await apiSend<{ id_ghabz: number }>('/ghabz-header', 'POST', toPayload(form))
//         navigate(`/ghabz/${created.id_ghabz}`)
//       }
//     } catch (e) {
//       setError(`ذخیره قبض ناموفق بود. ${e instanceof Error ? e.message : ''}`)
//     } finally { setSaving(false) }
//   }

//   return (
//     <div dir="rtl" style={{ maxWidth: 1000, margin: '0 auto' }}>
//       <Group justify="space-between" mb="md">
//         <Title order={2}>{isEdit ? 'ویرایش قبض انبار' : 'ایجاد قبض انبار'}</Title>
//         <Button variant="subtle" onClick={() => navigate('/ghabz')}>بازگشت</Button>
//       </Group>
//       <Paper shadow="xs" p="lg" pos="relative">
//         <LoadingOverlay visible={saving} />
//         <Grid gutter="md">
//           {!isEdit && (
//             <Grid.Col span={12}><RefSelect label="تالی" path="/tally/list" required
//               valueKey="id_tali" labelKey={tallyLabel}
//               value={form.tali_id}
//               onChange={(v) => set('tali_id', v)}
//               onPick={(r) => { if (r) set('number_tali', String(r.tali_number ?? '')) }} /></Grid.Col>
//           )}
//           <Grid.Col span={{ base: 12, md: 6 }}><TextInput label="شماره قبض" inputMode="numeric"
//             value={form.number_ghabz} onChange={(e) => set('number_ghabz', e.currentTarget.value)} /></Grid.Col>
//           <Grid.Col span={{ base: 12, md: 6 }}><TextInput label="شماره کارنه"
//             value={form.number_karaneh} onChange={(e) => set('number_karaneh', e.currentTarget.value)} /></Grid.Col>
//           <Grid.Col span={{ base: 12, md: 6 }}><TextInput label="شماره تالی" inputMode="numeric"
//             value={form.number_tali} onChange={(e) => set('number_tali', e.currentTarget.value)} /></Grid.Col>
//           <Grid.Col span={{ base: 12, md: 6 }}><TextInput label="وزن"
//             value={form.weight} onChange={(e) => set('weight', e.currentTarget.value)} /></Grid.Col>
//           <Grid.Col span={{ base: 12, md: 6 }}><JalaliDate label="تاریخ تخلیه"
//             value={form.date_unloading} onChange={(v) => set('date_unloading', v)} /></Grid.Col>
//           <Grid.Col span={{ base: 12, md: 6 }}><JalaliDate label="تاریخ ورود به مرز"
//             value={form.date_enter_marze} onChange={(v) => set('date_enter_marze', v)} /></Grid.Col>
//           <Grid.Col span={{ base: 12, md: 6 }}><RefSelect label="نام مرز" path="/terms"
//             params={{ category_id: 1 }} valueKey="sys_term_id" labelKey="value"
//             value={form.id_marze} onChange={(v) => set('id_marze', v)} /></Grid.Col>
//           <Grid.Col span={{ base: 12, md: 6 }}><RefSelect label="کشور" path="/terms"
//             params={{ category_id: 2 }} valueKey="sys_term_id" labelKey="value"
//             value={form.id_country} onChange={(v) => set('id_country', v)} /></Grid.Col>
//           <Grid.Col span={{ base: 12, md: 6 }}><RefSelect label="شرکت حمل" path="/companies"
//             valueKey="id_repre_company" labelKey={companyLabel}
//             value={form.id_company} onChange={(v) => set('id_company', v)} /></Grid.Col>
//           <Grid.Col span={{ base: 12, md: 6 }}><RefSelect label="صاحب کالا" path="/owners"
//             valueKey="id_owner" labelKey={ownerLabel}
//             value={form.id_product_ownear} onChange={(v) => set('id_product_ownear', v)} /></Grid.Col>
//           <Grid.Col span={{ base: 12, md: 6 }}><RefSelect label="انبار" path="/anbar"
//             valueKey="id_anbar" labelKey="name_anbar"
//             value={form.id_anbar} onChange={(v) => set('id_anbar', v)} /></Grid.Col>
//           <Grid.Col span={{ base: 12, md: 6 }}><RefSelect label="طاق" path="/tagh"
//             valueKey="id_tagh" labelKey="name_tagh"
//             value={form.id_tagh_anbara} onChange={(v) => set('id_tagh_anbara', v)} /></Grid.Col>
//           <Grid.Col span={{ base: 12, md: 6 }}><TextInput label="شماره بیمه"
//             value={form.number_bimeh} onChange={(e) => set('number_bimeh', e.currentTarget.value)} /></Grid.Col>
//           <Grid.Col span={{ base: 12, md: 6 }}><TextInput label="نام انبار دار"
//             value={form.name_anbardar} onChange={(e) => set('name_anbardar', e.currentTarget.value)} /></Grid.Col>
//           <Grid.Col span={{ base: 12, md: 6 }}><TextInput label="نام مدیر"
//             value={form.name_maneger} onChange={(e) => set('name_maneger', e.currentTarget.value)} /></Grid.Col>
//         </Grid>
//         {error && <div style={{ color: 'var(--mantine-color-red-6)', marginTop: 16 }}>{error}</div>}
//         <Group justify="flex-start" mt="xl">
//           <Button onClick={handleSave} loading={saving}>{isEdit ? 'ذخیره تغییرات' : 'ایجاد قبض'}</Button>
//           <Button variant="subtle" onClick={() => navigate('/ghabz')}>لغو</Button>
//         </Group>
//       </Paper>
//     </div>
//   )
// }

import { useState, useEffect } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import { BackButton } from '../components/BackButton'
import { useQuery } from '@tanstack/react-query'
import { Title, Paper, Grid, TextInput, Group, Button, LoadingOverlay } from '@mantine/core'
import { RefSelect } from '../components/RefSelect'
import { JalaliDate } from '../components/JalaliDate'
import { apiSend, apiGet } from '../api/client'

type GhabzState = {
  number_ghabz: string
  number_karaneh: string
  number_tali: string
  date_unloading: string | null
  date_enter_marze: string | null
  id_marze: number | null
  id_country: number | null
  id_company: number | null
  id_product_ownear: number | null
  id_anbar: number | null
  id_tagh_anbara: number | null
  weight: string
  status_bimeh: string
  number_bimeh: string
  name_anbardar: string
  name_maneger: string
  tali_id: number | null
}

const EMPTY: GhabzState = {
  number_ghabz: '', number_karaneh: '', number_tali: '', date_unloading: null,
  date_enter_marze: null, id_marze: null, id_country: null, id_company: null,
  id_product_ownear: null, id_anbar: null, id_tagh_anbara: null, weight: '',
  status_bimeh: '', number_bimeh: '', name_anbardar: '', name_maneger: '',
  tali_id: null,
}

function normalizeDigits(s: string): string {
  return s.replace(/[\u06F0-\u06F9]/g, (d) => String(d.charCodeAt(0) - 0x06f0))
          .replace(/[\u0660-\u0669]/g, (d) => String(d.charCodeAt(0) - 0x0660))
}

function toPayload(s: GhabzState) {
  const numOrNull = (v: string) => (v.trim() === '' ? null : Number(normalizeDigits(v)))
  const strOrNull = (v: string) => (v.trim() === '' ? null : v)
  const codeOrNull = (v: string) => strOrNull(normalizeDigits(v))
  return {
    number_ghabz: numOrNull(s.number_ghabz),
    number_karaneh: codeOrNull(s.number_karaneh),
    number_tali: numOrNull(s.number_tali),
    date_unloading: s.date_unloading,
    date_enter_marze: s.date_enter_marze,
    id_marze: s.id_marze, id_country: s.id_country, id_company: s.id_company,
    id_product_ownear: s.id_product_ownear, id_anbar: s.id_anbar, id_tagh_anbara: s.id_tagh_anbara,
    weight: strOrNull(s.weight), status_bimeh: strOrNull(s.status_bimeh),
    number_bimeh: codeOrNull(s.number_bimeh), name_anbardar: strOrNull(s.name_anbardar),
    name_maneger: strOrNull(s.name_maneger),
    tali_id: s.tali_id,
  }
}

function rowToState(r: Record<string, any>): GhabzState {
  const s = (v: any) => (v == null ? '' : String(v))
  return {
    number_ghabz: s(r.number_ghabz), number_karaneh: s(r.number_karaneh),
    number_tali: s(r.number_tali), date_unloading: r.date_unloading ?? null,
    date_enter_marze: r.date_enter_marze ?? null, id_marze: r.id_marze ?? null,
    id_country: r.id_country ?? null, id_company: r.id_company ?? null,
    id_product_ownear: r.id_product_ownear ?? null, id_anbar: r.id_anbar ?? null,
    id_tagh_anbara: r.id_tagh_anbara ?? null, weight: s(r.weight),
    status_bimeh: s(r.status_bimeh), number_bimeh: s(r.number_bimeh),
    name_anbardar: s(r.name_anbardar), name_maneger: s(r.name_maneger),
    tali_id: r.tali_id ?? null,
  }
}

const companyLabel = (r: Record<string, any>) =>
  `${r.name ?? ''} ${r.family ?? ''} ${r.national_code ? `(${r.national_code})` : ''}`.trim()
const ownerLabel = (r: Record<string, any>) => `${r.name ?? ''} ${r.family ?? ''}`.trim()
const tallyLabel = (r: Record<string, any>) =>
  `تالی ${r.tali_number ?? r.id_tali}${r.number_karaneh ? ` — کارنه ${r.number_karaneh}` : ''}`.trim()

export function GhabzHeaderForm() {
  const navigate = useNavigate()
  const { id } = useParams<{ id: string }>()
  const isEdit = id != null
  const editId = isEdit ? Number(id) : null
  const [form, setForm] = useState<GhabzState>(EMPTY)
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const { data: existing } = useQuery({
    queryKey: ['ghabz-header', editId],
    queryFn: () => apiGet<Record<string, any>>(`/ghabz-header/${editId}`),
    enabled: isEdit,
  })
  useEffect(() => { if (existing) setForm(rowToState(existing)) }, [existing])

  const set = <K extends keyof GhabzState>(k: K, v: GhabzState[K]) => setForm((f) => ({ ...f, [k]: v }))

  async function handleSave() {
    if (!isEdit && form.tali_id == null) {
      setError('انتخاب تالی برای صدور قبض الزامی است.')
      return
    }
    setSaving(true); setError(null)
    try {
      if (isEdit) {
        await apiSend(`/ghabz-header/${editId}`, 'PUT', toPayload(form))
        navigate(`/ghabz/${editId}`)
      } else {
        const created = await apiSend<{ id_ghabz: number }>('/ghabz-header', 'POST', toPayload(form))
        navigate(`/ghabz/${created.id_ghabz}`)
      }
    } catch (e) {
      setError(`ذخیره قبض ناموفق بود. ${e instanceof Error ? e.message : ''}`)
    } finally { setSaving(false) }
  }

  return (
    <div dir="rtl" style={{ maxWidth: 1000, margin: '0 auto' }}>
      <Group justify="space-between" mb="md">
        <Title order={2} fw={700}>{isEdit ? 'ویرایش قبض انبار' : 'ایجاد قبض انبار'}</Title>
        
      </Group>
      <Paper shadow="xs" p="lg" pos="relative">
        <LoadingOverlay visible={saving} />
        <Grid gutter="md">
          {!isEdit && (
            <Grid.Col span={12}><RefSelect label="تالی" path="/tally/list" required
              valueKey="id_tali" labelKey={tallyLabel}
              value={form.tali_id}
              onChange={(v) => set('tali_id', v)}
              onPick={(r) => { if (r) set('number_tali', String(r.tali_number ?? '')) }} /></Grid.Col>
          )}
          <Grid.Col span={{ base: 12, md: 6 }}><TextInput label="شماره قبض" inputMode="numeric"
            value={form.number_ghabz} onChange={(e) => set('number_ghabz', e.currentTarget.value)} /></Grid.Col>
          <Grid.Col span={{ base: 12, md: 6 }}><TextInput label="شماره کارنه"
            value={form.number_karaneh} onChange={(e) => set('number_karaneh', e.currentTarget.value)} /></Grid.Col>
          <Grid.Col span={{ base: 12, md: 6 }}><TextInput label="شماره تالی" inputMode="numeric"
            value={form.number_tali} onChange={(e) => set('number_tali', e.currentTarget.value)} /></Grid.Col>
          <Grid.Col span={{ base: 12, md: 6 }}><TextInput label="وزن"
            value={form.weight} onChange={(e) => set('weight', e.currentTarget.value)} /></Grid.Col>
          <Grid.Col span={{ base: 12, md: 6 }}><JalaliDate label="تاریخ تخلیه"
            value={form.date_unloading} onChange={(v) => set('date_unloading', v)} /></Grid.Col>
          <Grid.Col span={{ base: 12, md: 6 }}><JalaliDate label="تاریخ ورود به مرز"
            value={form.date_enter_marze} onChange={(v) => set('date_enter_marze', v)} /></Grid.Col>
          <Grid.Col span={{ base: 12, md: 6 }}><RefSelect label="نام مرز" path="/terms"
            params={{ category_id: 1 }} valueKey="sys_term_id" labelKey="value"
            value={form.id_marze} onChange={(v) => set('id_marze', v)} /></Grid.Col>
          <Grid.Col span={{ base: 12, md: 6 }}><RefSelect label="کشور" path="/terms"
            params={{ category_id: 2 }} valueKey="sys_term_id" labelKey="value"
            value={form.id_country} onChange={(v) => set('id_country', v)} /></Grid.Col>
          <Grid.Col span={{ base: 12, md: 6 }}><RefSelect label="شرکت حمل" path="/companies"
            valueKey="id_repre_company" labelKey={companyLabel}
            value={form.id_company} onChange={(v) => set('id_company', v)} /></Grid.Col>
          <Grid.Col span={{ base: 12, md: 6 }}><RefSelect label="صاحب کالا" path="/owners"
            valueKey="id_owner" labelKey={ownerLabel}
            value={form.id_product_ownear} onChange={(v) => set('id_product_ownear', v)} /></Grid.Col>
          <Grid.Col span={{ base: 12, md: 6 }}><RefSelect label="انبار" path="/anbar"
            valueKey="id_anbar" labelKey="name_anbar"
            value={form.id_anbar} onChange={(v) => set('id_anbar', v)} /></Grid.Col>
          <Grid.Col span={{ base: 12, md: 6 }}><RefSelect label="طاق" path="/tagh"
            valueKey="id_tagh" labelKey="name_tagh"
            value={form.id_tagh_anbara} onChange={(v) => set('id_tagh_anbara', v)} /></Grid.Col>
          <Grid.Col span={{ base: 12, md: 6 }}><TextInput label="شماره بیمه"
            value={form.number_bimeh} onChange={(e) => set('number_bimeh', e.currentTarget.value)} /></Grid.Col>
          <Grid.Col span={{ base: 12, md: 6 }}><TextInput label="نام انبار دار"
            value={form.name_anbardar} onChange={(e) => set('name_anbardar', e.currentTarget.value)} /></Grid.Col>
          <Grid.Col span={{ base: 12, md: 6 }}><TextInput label="نام مدیر"
            value={form.name_maneger} onChange={(e) => set('name_maneger', e.currentTarget.value)} /></Grid.Col>
        </Grid>
        {error && <div style={{ color: 'var(--mantine-color-red-6)', marginTop: 16 }}>{error}</div>}
        <Group justify="flex-start" mt="xl">
          <Button onClick={handleSave} loading={saving}>{isEdit ? 'ذخیره تغییرات' : 'ایجاد قبض'}</Button>
          <BackButton to="/ghabz" />
        </Group>
      </Paper>
    </div>
  )
}