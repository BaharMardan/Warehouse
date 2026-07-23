// import { useState, useEffect } from 'react'
// import { useNavigate, useParams } from 'react-router-dom'
// import { BackButton } from '../components/BackButton'
// import { useQuery } from '@tanstack/react-query'
// import {
//   Title, Paper, Grid, TextInput, Radio, Group, Button, Stack, LoadingOverlay,
// } from '@mantine/core'
// import { RefSelect } from '../components/RefSelect'
// import { JalaliDate } from '../components/JalaliDate'
// import { apiSend, apiGet } from '../api/client'


// // Persian (۰۱۲۳) / Arabic-Indic (٠١٢٣) digits -> Latin (0123). Latin passes through.
// // Used on code/number fields so they store searchable ASCII digits, while
// // name fields keep whatever script the user typed.
// function normalizeDigits(s: string): string {
//   return s
//     .replace(/[\u06F0-\u06F9]/g, (d) => String(d.charCodeAt(0) - 0x06f0))
//     .replace(/[\u0660-\u0669]/g, (d) => String(d.charCodeAt(0) - 0x0660))
// }

// /**
//  * TallyHeaderForm — create a new tally (شمارهٔ تالی) shipment header.
//  *
//  * This is the header layer of the tally. Once saved it returns the new ID_TALI,
//  * which the detail-lines grid and the action sub-screens will hang off of.
//  *
//  * It reuses the two primitives we built:
//  *   - RefSelect   for the 5 foreign-key dropdowns (border, country, company x2, owner)
//  *   - JalaliDate  for the 2 Persian date fields (entry / unloading)
//  *
//  * The form's state mirrors the backend TaliHeaderInput model exactly (ISO dates,
//  * numeric FKs), so the payload posts straight to /tally-header with no mapping.
//  */

// // Shape matches the backend model field-for-field.
// type TallyHeaderState = {
//   number_karaneh: string
//   radef_marze: string // kept as string in the input, sent as number|null
//   date_enter_marze: string | null // ISO date
//   date_unloading: string | null // ISO date
//   id_marze: number | null
//   id_company: number | null
//   id_respons_company: number | null
//   id_product_ownear: number | null
//   id_country: number | null
//   number_bimeh: string
//   tali_number: string
//   number_ghabz: string
//   name_arzyab: string
//   number_barnameh: string
//   is_bimeh: string // "بله" | "خیر"
//   name_anbardar: string
//   accepted_gomrok: string
//   company_bimeh: string
// }

// const EMPTY: TallyHeaderState = {
//   number_karaneh: '', radef_marze: '', date_enter_marze: null, date_unloading: null,
//   id_marze: null, id_company: null, id_respons_company: null, id_product_ownear: null,
//   id_country: null, number_bimeh: '', tali_number: '', number_ghabz: '',
//   name_arzyab: '', number_barnameh: '', is_bimeh: 'خیر', name_anbardar: '',
//   accepted_gomrok: '', company_bimeh: '',
// }

// // turn "" into null and numeric strings into numbers, so the payload matches the
// // backend model (which expects number|null / str|null, never empty strings)
// function toPayload(s: TallyHeaderState) {
//   const numOrNull = (v: string) => (v.trim() === '' ? null : Number(v))
//   const strOrNull = (v: string) => (v.trim() === '' ? null : v)
//   // code/number fields: convert Persian/Arabic digits to Latin before storing
//   const codeOrNull = (v: string) => strOrNull(normalizeDigits(v))
//   return {
//     number_karaneh: codeOrNull(s.number_karaneh),   // ← normalized
//     radef_marze: numOrNull(normalizeDigits(s.radef_marze)),
//     date_enter_marze: s.date_enter_marze,
//     date_unloading: s.date_unloading,
//     id_marze: s.id_marze,
//     id_company: s.id_company,
//     id_respons_company: s.id_respons_company,
//     id_product_ownear: s.id_product_ownear,
//     id_country: s.id_country,
//     number_bimeh: codeOrNull(s.number_bimeh),        // ← normalized
//     tali_number: numOrNull(normalizeDigits(s.tali_number)),
//     number_ghabz: numOrNull(normalizeDigits(s.number_ghabz)),  // ← normalized
//     name_arzyab: strOrNull(s.name_arzyab),           // name — left as typed
//     number_barnameh: codeOrNull(s.number_barnameh),  // ← normalized
//     is_bimeh: strOrNull(s.is_bimeh),
//     name_anbardar: strOrNull(s.name_anbardar),       // name — left as typed
//     accepted_gomrok: strOrNull(s.accepted_gomrok),
//     company_bimeh: strOrNull(s.company_bimeh),
//   }
// }
// // A loaded tally row (from GET /tally-header/{id}) -> the form's state shape.
// // The API returns nulls and numbers; the form's text fields want strings.
// function rowToState(r: Record<string, any>): TallyHeaderState {
//   const s = (v: any) => (v == null ? '' : String(v))
//   return {
//     number_karaneh: s(r.number_karaneh),
//     radef_marze: s(r.radef_marze),
//     date_enter_marze: r.date_enter_marze ?? null,
//     date_unloading: r.date_unloading ?? null,
//     id_marze: r.id_marze ?? null,
//     id_company: r.id_company ?? null,
//     id_respons_company: r.id_respons_company ?? null,
//     id_product_ownear: r.id_product_ownear ?? null,
//     id_country: r.id_country ?? null,
//     number_bimeh: s(r.number_bimeh),
//     tali_number: s(r.tali_number),
//     number_ghabz: s(r.number_ghabz),
//     name_arzyab: s(r.name_arzyab),
//     number_barnameh: s(r.number_barnameh),
//     is_bimeh: r.is_bimeh ?? 'خیر',
//     name_anbardar: s(r.name_anbardar),
//     accepted_gomrok: s(r.accepted_gomrok),
//     company_bimeh: s(r.company_bimeh),
//   }
// }

// // build "name family (national_code)" — matches how the APEX app shows companies/reps
// const companyLabel = (r: Record<string, any>) =>
//   `${r.name ?? ''} ${r.family ?? ''} ${r.national_code ? `(${r.national_code})` : ''}`.trim()

// const ownerLabel = (r: Record<string, any>) =>
//   `${r.name ?? ''} ${r.family ?? ''}`.trim()

// export function TallyHeaderForm() {
//   const navigate = useNavigate()
//   const { id } = useParams<{ id: string }>()
//   const isEdit = id != null
//   const editId = isEdit ? Number(id) : null

//   // when editing, load the existing header once and populate the form
//   const { data: existing } = useQuery({
//     queryKey: ['tally-header', editId],
//     queryFn: () => apiGet<Record<string, any>>(`/tally-header/${editId}`),
//     enabled: isEdit, // only fetch in edit mode
//   })

//   useEffect(() => {
//     if (existing) setForm(rowToState(existing))
//   }, [existing])
//   const [form, setForm] = useState<TallyHeaderState>(EMPTY)
//   const [saving, setSaving] = useState(false)
//   const [error, setError] = useState<string | null>(null)

//   // one helper to update any field by key
//   const set = <K extends keyof TallyHeaderState>(key: K, value: TallyHeaderState[K]) =>
//     setForm((f) => ({ ...f, [key]: value }))

//   // async function handleSave() {
//   //   setSaving(true)
//   //   setError(null)
//   //   try {
//   //   //   const created = await apiPost<{ id_tali: number }>('/tally-header', toPayload(form))
//   //     const created = await apiSend<{ id_tali: number }>('/tally-header', 'POST', toPayload(form))
//   //     // once saved we have the new tally id — go to its detail view (built next).
//   //     // for now, navigate back to the tally list.
//   //     navigate('/tally')
//   //     return created
//   //   } catch (e) {
//   //     setError('ذخیره تالی ناموفق بود. لطفاً دوباره تلاش کنید.')
//   //   } finally {
//   //     setSaving(false)
//   //   }
//   // }
//   async function handleSave() {
//     setSaving(true)
//     setError(null)
//     try {
//       if (isEdit) {
//         await apiSend(`/tally-header/${editId}`, 'PUT', toPayload(form))
//         navigate(`/tally/${editId}`) // back to the detail page
//       } else {
//         const created = await apiSend<{ id_tali: number }>('/tally-header', 'POST', toPayload(form))
//         navigate(`/tally/${created.id_tali}`) // go to the new tally's detail page
//       }
//     } catch (e) {
//       setError('ذخیره تالی ناموفق بود. لطفاً دوباره تلاش کنید.')
//     } finally {
//       setSaving(false)
//     }
//   }
//   return (
//     <div dir="rtl" style={{ maxWidth: 1000, margin: '0 auto' }}>
//       <Group justify="space-between" mb="md">
//         <Title order={2} fw={700}>{isEdit ? 'ویرایش تالی' : 'ایجاد تالی جدید'}</Title>
//         <Button onClick={handleSave} loading={saving}>{isEdit ? 'ذخیره تغییرات' : 'ایجاد تالی'}</Button>
//       </Group>

//       <Paper shadow="xs" p="lg" pos="relative">
//         <LoadingOverlay visible={saving} />

//         <Grid gutter="md">
//           {/* --- row: karaneh / transit + border row number --- */}
//           <Grid.Col span={{ base: 12, md: 6 }}>
//             <TextInput
//               label="شماره کارنه / ترانزیت"
//               value={form.number_karaneh}
//               onChange={(e) => set('number_karaneh', e.currentTarget.value)}
//             />
//           </Grid.Col>
//           <Grid.Col span={{ base: 12, md: 6 }}>
//             <TextInput
//               label="ردیف مرزی"
//               inputMode="numeric"
//               value={form.radef_marze}
//               onChange={(e) => set('radef_marze', e.currentTarget.value)}
//             />
//           </Grid.Col>

//           {/* --- row: entry border (term cat 1) + origin country (term cat 2) --- */}
//           <Grid.Col span={{ base: 12, md: 6 }}>
//             <RefSelect
//               label="نام مرز ورودی"
//               path="/terms"
//               params={{ category_id: 1 }}
//               valueKey="sys_term_id"
//               labelKey="value"
//               value={form.id_marze}
//               onChange={(v) => set('id_marze', v)}
//             />
//           </Grid.Col>
//           <Grid.Col span={{ base: 12, md: 6 }}>
//             <RefSelect
//               label="مبدا حمل (کشور)"
//               path="/terms"
//               params={{ category_id: 2 }}
//               valueKey="sys_term_id"
//               labelKey="value"
//               value={form.id_country}
//               onChange={(v) => set('id_country', v)}
//             />
//           </Grid.Col>

//           {/* --- row: two Jalali dates --- */}
//           <Grid.Col span={{ base: 12, md: 6 }}>
//             <JalaliDate
//               label="تاریخ ورود به مرز"
//               value={form.date_enter_marze}
//               onChange={(iso) => set('date_enter_marze', iso)}
//             />
//           </Grid.Col>
//           <Grid.Col span={{ base: 12, md: 6 }}>
//             <JalaliDate
//               label="تاریخ تخلیه"
//               value={form.date_unloading}
//               onChange={(iso) => set('date_unloading', iso)}
//             />
//           </Grid.Col>

//           {/* --- row: transport company + its representative (both from companies) --- */}
//           <Grid.Col span={{ base: 12, md: 6 }}>
//             <RefSelect
//               label="نام شرکت حمل"
//               path="/companies"
//               valueKey="id_repre_company"
//               labelKey={companyLabel}
//               value={form.id_company}
//               onChange={(v) => set('id_company', v)}
//             />
//           </Grid.Col>
//           <Grid.Col span={{ base: 12, md: 6 }}>
//             <RefSelect
//               label="نام نماینده شرکت حمل"
//               path="/companies"
//               valueKey="id_repre_company"
//               labelKey={companyLabel}
//               value={form.id_respons_company}
//               onChange={(v) => set('id_respons_company', v)}
//             />
//           </Grid.Col>

//           {/* --- row: goods owner + assessor --- */}
//           <Grid.Col span={{ base: 12, md: 6 }}>
//             <RefSelect
//               label="صاحب کالا"
//               path="/owners"
//               valueKey="id_owner"
//               labelKey={ownerLabel}
//               value={form.id_product_ownear}
//               onChange={(v) => set('id_product_ownear', v)}
//             />
//           </Grid.Col>
//           <Grid.Col span={{ base: 12, md: 6 }}>
//             <TextInput
//               label="نام ارزیاب"
//               value={form.name_arzyab}
//               onChange={(e) => set('name_arzyab', e.currentTarget.value)}
//             />
//           </Grid.Col>

//           {/* --- row: insurance number + insurance company --- */}
//           <Grid.Col span={{ base: 12, md: 6 }}>
//             <TextInput
//               label="شماره بیمه نامه"
//               value={form.number_bimeh}
//               onChange={(e) => set('number_bimeh', e.currentTarget.value)}
//             />
//           </Grid.Col>
//           <Grid.Col span={{ base: 12, md: 6 }}>
//             <TextInput
//               label="شرکت بیمه گر"
//               value={form.company_bimeh}
//               onChange={(e) => set('company_bimeh', e.currentTarget.value)}
//             />
//           </Grid.Col>

//           {/* --- row: barnameh number + electronic receipt number --- */}
//           <Grid.Col span={{ base: 12, md: 6 }}>
//             <TextInput
//               label="شماره بارنامه"
//               value={form.number_barnameh}
//               onChange={(e) => set('number_barnameh', e.currentTarget.value)}
//             />
//           </Grid.Col>
//           <Grid.Col span={{ base: 12, md: 6 }}>
//             <TextInput
//               label="قبض الکترونیک"
//               inputMode="numeric"
//               value={form.number_ghabz}
//               onChange={(e) => set('number_ghabz', e.currentTarget.value)}
//             />
//           </Grid.Col>

//           {/* --- row: tally number + warehouse keeper --- */}
//           <Grid.Col span={{ base: 12, md: 6 }}>
//             <TextInput
//               label="شماره تالی"
//               inputMode="numeric"
//               value={form.tali_number}
//               onChange={(e) => set('tali_number', e.currentTarget.value)}
//             />
//           </Grid.Col>
//           <Grid.Col span={{ base: 12, md: 6 }}>
//             <TextInput
//               label="نام انبار دار"
//               value={form.name_anbardar}
//               onChange={(e) => set('name_anbardar', e.currentTarget.value)}
//             />
//           </Grid.Col>

//           {/* --- row: two yes/no radios --- */}
//           <Grid.Col span={{ base: 12, md: 6 }}>
//             <Radio.Group
//               label="آیا بیمه دارد؟"
//               value={form.is_bimeh}
//               onChange={(v) => set('is_bimeh', v)}
//             >
//               <Group mt="xs">
//                 <Radio value="بله" label="بله" />
//                 <Radio value="خیر" label="خیر" />
//               </Group>
//             </Radio.Group>
//           </Grid.Col>
//           <Grid.Col span={{ base: 12, md: 6 }}>
//             <Radio.Group
//               label="تایید گمرک"
//               value={form.accepted_gomrok}
//               onChange={(v) => set('accepted_gomrok', v)}
//             >
//               <Group mt="xs">
//                 <Radio value="بله" label="بله" />
//                 <Radio value="خیر" label="خیر" />
//               </Group>
//             </Radio.Group>
//           </Grid.Col>
//         </Grid>

//         {error && (
//           <div style={{ color: 'var(--mantine-color-red-6)', marginTop: 16 }}>{error}</div>
//         )}

//         <Group justify="flex-start" mt="xl">
//           <Button onClick={handleSave} loading={saving}>ایجاد تالی</Button>
//           <BackButton to="/tally" />
//         </Group>
//       </Paper>
//     </div>
//   )
// }

// import { useState, useEffect } from 'react'
// import { useNavigate, useParams } from 'react-router-dom'
// import { useQuery } from '@tanstack/react-query'
// import {
//   Title, Paper, Grid, TextInput, Radio, Group, Button, Stack, LoadingOverlay,
// } from '@mantine/core'
// import { RefSelect } from '../components/RefSelect'
// import { JalaliDate } from '../components/JalaliDate'
// import { apiSend, apiGet } from '../api/client'


// // Persian (۰۱۲۳) / Arabic-Indic (٠١٢٣) digits -> Latin (0123). Latin passes through.
// // Used on code/number fields so they store searchable ASCII digits, while
// // name fields keep whatever script the user typed.
// function normalizeDigits(s: string): string {
//   return s
//     .replace(/[\u06F0-\u06F9]/g, (d) => String(d.charCodeAt(0) - 0x06f0))
//     .replace(/[\u0660-\u0669]/g, (d) => String(d.charCodeAt(0) - 0x0660))
// }

// /**
//  * TallyHeaderForm — create a new tally (شمارهٔ تالی) shipment header.
//  *
//  * This is the header layer of the tally. Once saved it returns the new ID_TALI,
//  * which the detail-lines grid and the action sub-screens will hang off of.
//  *
//  * It reuses the two primitives we built:
//  *   - RefSelect   for the 5 foreign-key dropdowns (border, country, company x2, owner)
//  *   - JalaliDate  for the 2 Persian date fields (entry / unloading)
//  *
//  * The form's state mirrors the backend TaliHeaderInput model exactly (ISO dates,
//  * numeric FKs), so the payload posts straight to /tally-header with no mapping.
//  */

// // Shape matches the backend model field-for-field.
// type TallyHeaderState = {
//   number_karaneh: string
//   radef_marze: string // kept as string in the input, sent as number|null
//   date_enter_marze: string | null // ISO date
//   date_unloading: string | null // ISO date
//   id_marze: number | null
//   id_company: number | null
//   id_respons_company: number | null
//   id_product_ownear: number | null
//   id_country: number | null
//   number_bimeh: string
//   tali_number: string
//   number_ghabz: string
//   name_arzyab: string
//   number_barnameh: string
//   is_bimeh: string // "بله" | "خیر"
//   name_anbardar: string
//   accepted_gomrok: string
//   company_bimeh: string
// }

// const EMPTY: TallyHeaderState = {
//   number_karaneh: '', radef_marze: '', date_enter_marze: null, date_unloading: null,
//   id_marze: null, id_company: null, id_respons_company: null, id_product_ownear: null,
//   id_country: null, number_bimeh: '', tali_number: '', number_ghabz: '',
//   name_arzyab: '', number_barnameh: '', is_bimeh: 'خیر', name_anbardar: '',
//   accepted_gomrok: '', company_bimeh: '',
// }

// // turn "" into null and numeric strings into numbers, so the payload matches the
// // backend model (which expects number|null / str|null, never empty strings)
// function toPayload(s: TallyHeaderState) {
//   const numOrNull = (v: string) => (v.trim() === '' ? null : Number(v))
//   const strOrNull = (v: string) => (v.trim() === '' ? null : v)
//   // code/number fields: convert Persian/Arabic digits to Latin before storing
//   const codeOrNull = (v: string) => strOrNull(normalizeDigits(v))
//   return {
//     number_karaneh: codeOrNull(s.number_karaneh),   // ← normalized
//     radef_marze: numOrNull(normalizeDigits(s.radef_marze)),
//     date_enter_marze: s.date_enter_marze,
//     date_unloading: s.date_unloading,
//     id_marze: s.id_marze,
//     id_company: s.id_company,
//     id_respons_company: s.id_respons_company,
//     id_product_ownear: s.id_product_ownear,
//     id_country: s.id_country,
//     number_bimeh: codeOrNull(s.number_bimeh),        // ← normalized
//     tali_number: numOrNull(normalizeDigits(s.tali_number)),
//     number_ghabz: numOrNull(normalizeDigits(s.number_ghabz)),  // ← normalized
//     name_arzyab: strOrNull(s.name_arzyab),           // name — left as typed
//     number_barnameh: codeOrNull(s.number_barnameh),  // ← normalized
//     is_bimeh: strOrNull(s.is_bimeh),
//     name_anbardar: strOrNull(s.name_anbardar),       // name — left as typed
//     accepted_gomrok: strOrNull(s.accepted_gomrok),
//     company_bimeh: strOrNull(s.company_bimeh),
//   }
// }
// // A loaded tally row (from GET /tally-header/{id}) -> the form's state shape.
// // The API returns nulls and numbers; the form's text fields want strings.
// function rowToState(r: Record<string, any>): TallyHeaderState {
//   const s = (v: any) => (v == null ? '' : String(v))
//   return {
//     number_karaneh: s(r.number_karaneh),
//     radef_marze: s(r.radef_marze),
//     date_enter_marze: r.date_enter_marze ?? null,
//     date_unloading: r.date_unloading ?? null,
//     id_marze: r.id_marze ?? null,
//     id_company: r.id_company ?? null,
//     id_respons_company: r.id_respons_company ?? null,
//     id_product_ownear: r.id_product_ownear ?? null,
//     id_country: r.id_country ?? null,
//     number_bimeh: s(r.number_bimeh),
//     tali_number: s(r.tali_number),
//     number_ghabz: s(r.number_ghabz),
//     name_arzyab: s(r.name_arzyab),
//     number_barnameh: s(r.number_barnameh),
//     is_bimeh: r.is_bimeh ?? 'خیر',
//     name_anbardar: s(r.name_anbardar),
//     accepted_gomrok: s(r.accepted_gomrok),
//     company_bimeh: s(r.company_bimeh),
//   }
// }

// // build "name family (national_code)" — matches how the APEX app shows companies/reps
// const companyLabel = (r: Record<string, any>) =>
//   `${r.name ?? ''} ${r.family ?? ''} ${r.national_code ? `(${r.national_code})` : ''}`.trim()

// const ownerLabel = (r: Record<string, any>) =>
//   `${r.name ?? ''} ${r.family ?? ''}`.trim()

// export function TallyHeaderForm() {
//   const navigate = useNavigate()
//   const { id } = useParams<{ id: string }>()
//   const isEdit = id != null
//   const editId = isEdit ? Number(id) : null

//   // when editing, load the existing header once and populate the form
//   const { data: existing } = useQuery({
//     queryKey: ['tally-header', editId],
//     queryFn: () => apiGet<Record<string, any>>(`/tally-header/${editId}`),
//     enabled: isEdit, // only fetch in edit mode
//   })

//   useEffect(() => {
//     if (existing) setForm(rowToState(existing))
//   }, [existing])
//   const [form, setForm] = useState<TallyHeaderState>(EMPTY)
//   const [saving, setSaving] = useState(false)
//   const [error, setError] = useState<string | null>(null)

//   // one helper to update any field by key
//   const set = <K extends keyof TallyHeaderState>(key: K, value: TallyHeaderState[K]) =>
//     setForm((f) => ({ ...f, [key]: value }))

//   // async function handleSave() {
//   //   setSaving(true)
//   //   setError(null)
//   //   try {
//   //   //   const created = await apiPost<{ id_tali: number }>('/tally-header', toPayload(form))
//   //     const created = await apiSend<{ id_tali: number }>('/tally-header', 'POST', toPayload(form))
//   //     // once saved we have the new tally id — go to its detail view (built next).
//   //     // for now, navigate back to the tally list.
//   //     navigate('/tally')
//   //     return created
//   //   } catch (e) {
//   //     setError('ذخیره تالی ناموفق بود. لطفاً دوباره تلاش کنید.')
//   //   } finally {
//   //     setSaving(false)
//   //   }
//   // }
//   async function handleSave() {
//     setSaving(true)
//     setError(null)
//     try {
//       if (isEdit) {
//         await apiSend(`/tally-header/${editId}`, 'PUT', toPayload(form))
//         navigate(`/tally/${editId}`) // back to the detail page
//       } else {
//         const created = await apiSend<{ id_tali: number }>('/tally-header', 'POST', toPayload(form))
//         navigate(`/tally/${created.id_tali}`) // go to the new tally's detail page
//       }
//     } catch (e) {
//       setError('ذخیره تالی ناموفق بود. لطفاً دوباره تلاش کنید.')
//     } finally {
//       setSaving(false)
//     }
//   }
//   return (
//     <div dir="rtl" style={{ maxWidth: 1000, margin: '0 auto' }}>
//       <Group justify="space-between" mb="md">
//         <Title order={2}>{isEdit ? 'ویرایش تالی' : 'ایجاد تالی جدید'}</Title>
//         <Button onClick={handleSave} loading={saving}>{isEdit ? 'ذخیره تغییرات' : 'ایجاد تالی'}</Button>
//       </Group>

//       <Paper shadow="xs" p="lg" pos="relative">
//         <LoadingOverlay visible={saving} />

//         <Grid gutter="md">
//           {/* --- row: karaneh / transit + border row number --- */}
//           <Grid.Col span={{ base: 12, md: 6 }}>
//             <TextInput
//               label="شماره کارنه / ترانزیت"
//               value={form.number_karaneh}
//               onChange={(e) => set('number_karaneh', e.currentTarget.value)}
//             />
//           </Grid.Col>
//           <Grid.Col span={{ base: 12, md: 6 }}>
//             <TextInput
//               label="ردیف مرزی"
//               inputMode="numeric"
//               value={form.radef_marze}
//               onChange={(e) => set('radef_marze', e.currentTarget.value)}
//             />
//           </Grid.Col>

//           {/* --- row: entry border (term cat 1) + origin country (term cat 2) --- */}
//           <Grid.Col span={{ base: 12, md: 6 }}>
//             <RefSelect
//               label="نام مرز ورودی"
//               path="/terms"
//               params={{ category_id: 1 }}
//               valueKey="sys_term_id"
//               labelKey="value"
//               value={form.id_marze}
//               onChange={(v) => set('id_marze', v)}
//             />
//           </Grid.Col>
//           <Grid.Col span={{ base: 12, md: 6 }}>
//             <RefSelect
//               label="مبدا حمل (کشور)"
//               path="/terms"
//               params={{ category_id: 2 }}
//               valueKey="sys_term_id"
//               labelKey="value"
//               value={form.id_country}
//               onChange={(v) => set('id_country', v)}
//             />
//           </Grid.Col>

//           {/* --- row: two Jalali dates --- */}
//           <Grid.Col span={{ base: 12, md: 6 }}>
//             <JalaliDate
//               label="تاریخ ورود به مرز"
//               value={form.date_enter_marze}
//               onChange={(iso) => set('date_enter_marze', iso)}
//             />
//           </Grid.Col>
//           <Grid.Col span={{ base: 12, md: 6 }}>
//             <JalaliDate
//               label="تاریخ تخلیه"
//               value={form.date_unloading}
//               onChange={(iso) => set('date_unloading', iso)}
//             />
//           </Grid.Col>

//           {/* --- row: transport company + its representative (both from companies) --- */}
//           <Grid.Col span={{ base: 12, md: 6 }}>
//             <RefSelect
//               label="نام شرکت حمل"
//               path="/companies"
//               valueKey="id_repre_company"
//               labelKey={companyLabel}
//               value={form.id_company}
//               onChange={(v) => set('id_company', v)}
//             />
//           </Grid.Col>
//           <Grid.Col span={{ base: 12, md: 6 }}>
//             <RefSelect
//               label="نام نماینده شرکت حمل"
//               path="/companies"
//               valueKey="id_repre_company"
//               labelKey={companyLabel}
//               value={form.id_respons_company}
//               onChange={(v) => set('id_respons_company', v)}
//             />
//           </Grid.Col>

//           {/* --- row: goods owner + assessor --- */}
//           <Grid.Col span={{ base: 12, md: 6 }}>
//             <RefSelect
//               label="صاحب کالا"
//               path="/owners"
//               valueKey="id_owner"
//               labelKey={ownerLabel}
//               value={form.id_product_ownear}
//               onChange={(v) => set('id_product_ownear', v)}
//             />
//           </Grid.Col>
//           <Grid.Col span={{ base: 12, md: 6 }}>
//             <TextInput
//               label="نام ارزیاب"
//               value={form.name_arzyab}
//               onChange={(e) => set('name_arzyab', e.currentTarget.value)}
//             />
//           </Grid.Col>

//           {/* --- row: insurance number + insurance company --- */}
//           <Grid.Col span={{ base: 12, md: 6 }}>
//             <TextInput
//               label="شماره بیمه نامه"
//               value={form.number_bimeh}
//               onChange={(e) => set('number_bimeh', e.currentTarget.value)}
//             />
//           </Grid.Col>
//           <Grid.Col span={{ base: 12, md: 6 }}>
//             <TextInput
//               label="شرکت بیمه گر"
//               value={form.company_bimeh}
//               onChange={(e) => set('company_bimeh', e.currentTarget.value)}
//             />
//           </Grid.Col>

//           {/* --- row: barnameh number + electronic receipt number --- */}
//           <Grid.Col span={{ base: 12, md: 6 }}>
//             <TextInput
//               label="شماره بارنامه"
//               value={form.number_barnameh}
//               onChange={(e) => set('number_barnameh', e.currentTarget.value)}
//             />
//           </Grid.Col>
//           <Grid.Col span={{ base: 12, md: 6 }}>
//             <TextInput
//               label="قبض الکترونیک"
//               inputMode="numeric"
//               value={form.number_ghabz}
//               onChange={(e) => set('number_ghabz', e.currentTarget.value)}
//             />
//           </Grid.Col>

//           {/* --- row: tally number + warehouse keeper --- */}
//           <Grid.Col span={{ base: 12, md: 6 }}>
//             <TextInput
//               label="شماره تالی"
//               inputMode="numeric"
//               value={form.tali_number}
//               onChange={(e) => set('tali_number', e.currentTarget.value)}
//             />
//           </Grid.Col>
//           <Grid.Col span={{ base: 12, md: 6 }}>
//             <TextInput
//               label="نام انبار دار"
//               value={form.name_anbardar}
//               onChange={(e) => set('name_anbardar', e.currentTarget.value)}
//             />
//           </Grid.Col>

//           {/* --- row: two yes/no radios --- */}
//           <Grid.Col span={{ base: 12, md: 6 }}>
//             <Radio.Group
//               label="آیا بیمه دارد؟"
//               value={form.is_bimeh}
//               onChange={(v) => set('is_bimeh', v)}
//             >
//               <Group mt="xs">
//                 <Radio value="بله" label="بله" />
//                 <Radio value="خیر" label="خیر" />
//               </Group>
//             </Radio.Group>
//           </Grid.Col>
//           <Grid.Col span={{ base: 12, md: 6 }}>
//             <Radio.Group
//               label="تایید گمرک"
//               value={form.accepted_gomrok}
//               onChange={(v) => set('accepted_gomrok', v)}
//             >
//               <Group mt="xs">
//                 <Radio value="بله" label="بله" />
//                 <Radio value="خیر" label="خیر" />
//               </Group>
//             </Radio.Group>
//           </Grid.Col>
//         </Grid>

//         {error && (
//           <div style={{ color: 'var(--mantine-color-red-6)', marginTop: 16 }}>{error}</div>
//         )}

//         <Group justify="flex-start" mt="xl">
//           <Button onClick={handleSave} loading={saving}>ایجاد تالی</Button>
//           <Button variant="subtle" onClick={() => navigate('/tally')}>لغو</Button>
//         </Group>
//       </Paper>
//     </div>
//   )
// }

import { useState, useEffect } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import { BackButton } from '../components/BackButton'
import { useQuery } from '@tanstack/react-query'
import {
  Title, Paper, Grid, TextInput, Radio, Group, Button, Stack, LoadingOverlay,
} from '@mantine/core'
import { RefSelect } from '../components/RefSelect'
import { JalaliDate } from '../components/JalaliDate'
import { apiSend, apiGet } from '../api/client'


// Persian (۰۱۲۳) / Arabic-Indic (٠١٢٣) digits -> Latin (0123). Latin passes through.
// Used on code/number fields so they store searchable ASCII digits, while
// name fields keep whatever script the user typed.
function normalizeDigits(s: string): string {
  return s
    .replace(/[\u06F0-\u06F9]/g, (d) => String(d.charCodeAt(0) - 0x06f0))
    .replace(/[\u0660-\u0669]/g, (d) => String(d.charCodeAt(0) - 0x0660))
}

/**
 * TallyHeaderForm — create a new tally (شمارهٔ تالی) shipment header.
 *
 * This is the header layer of the tally. Once saved it returns the new ID_TALI,
 * which the detail-lines grid and the action sub-screens will hang off of.
 *
 * It reuses the two primitives we built:
 *   - RefSelect   for the 5 foreign-key dropdowns (border, country, company x2, owner)
 *   - JalaliDate  for the 2 Persian date fields (entry / unloading)
 *
 * The form sends the editable header fields to /tally-header. The backend owns
 * tali_number and allocates it only after a successful create transaction.
 */

// Editable form fields. The generated tally number is deliberately excluded.
type TallyHeaderState = {
  number_karaneh: string
  radef_marze: string // kept as string in the input, sent as number|null
  date_enter_marze: string | null // ISO date
  date_unloading: string | null // ISO date
  id_marze: number | null
  id_company: number | null
  id_respons_company: number | null
  id_product_ownear: number | null
  id_country: number | null
  number_bimeh: string
  number_ghabz: string
  name_arzyab: string
  number_barnameh: string
  is_bimeh: string // "بله" | "خیر"
  name_anbardar: string
  accepted_gomrok: string
  company_bimeh: string
}

const EMPTY: TallyHeaderState = {
  number_karaneh: '', radef_marze: '', date_enter_marze: null, date_unloading: null,
  id_marze: null, id_company: null, id_respons_company: null, id_product_ownear: null,
  id_country: null, number_bimeh: '', number_ghabz: '',
  name_arzyab: '', number_barnameh: '', is_bimeh: 'خیر', name_anbardar: '',
  accepted_gomrok: '', company_bimeh: '',
}

// turn "" into null and numeric strings into numbers, so the payload matches the
// backend model (which expects number|null / str|null, never empty strings)
function toPayload(s: TallyHeaderState) {
  const numOrNull = (v: string) => (v.trim() === '' ? null : Number(v))
  const strOrNull = (v: string) => (v.trim() === '' ? null : v)
  // code/number fields: convert Persian/Arabic digits to Latin before storing
  const codeOrNull = (v: string) => strOrNull(normalizeDigits(v))
  return {
    number_karaneh: codeOrNull(s.number_karaneh),   // ← normalized
    radef_marze: numOrNull(normalizeDigits(s.radef_marze)),
    date_enter_marze: s.date_enter_marze,
    date_unloading: s.date_unloading,
    id_marze: s.id_marze,
    id_company: s.id_company,
    id_respons_company: s.id_respons_company,
    id_product_ownear: s.id_product_ownear,
    id_country: s.id_country,
    number_bimeh: codeOrNull(s.number_bimeh),        // ← normalized
    number_ghabz: numOrNull(normalizeDigits(s.number_ghabz)),  // ← normalized
    name_arzyab: strOrNull(s.name_arzyab),           // name — left as typed
    number_barnameh: codeOrNull(s.number_barnameh),  // ← normalized
    is_bimeh: strOrNull(s.is_bimeh),
    name_anbardar: strOrNull(s.name_anbardar),       // name — left as typed
    accepted_gomrok: strOrNull(s.accepted_gomrok),
    company_bimeh: strOrNull(s.company_bimeh),
  }
}
// A loaded tally row (from GET /tally-header/{id}) -> the form's state shape.
// The API returns nulls and numbers; the form's text fields want strings.
function rowToState(r: Record<string, any>): TallyHeaderState {
  const s = (v: any) => (v == null ? '' : String(v))
  return {
    number_karaneh: s(r.number_karaneh),
    radef_marze: s(r.radef_marze),
    date_enter_marze: r.date_enter_marze ?? null,
    date_unloading: r.date_unloading ?? null,
    id_marze: r.id_marze ?? null,
    id_company: r.id_company ?? null,
    id_respons_company: r.id_respons_company ?? null,
    id_product_ownear: r.id_product_ownear ?? null,
    id_country: r.id_country ?? null,
    number_bimeh: s(r.number_bimeh),
    number_ghabz: s(r.number_ghabz),
    name_arzyab: s(r.name_arzyab),
    number_barnameh: s(r.number_barnameh),
    is_bimeh: r.is_bimeh ?? 'خیر',
    name_anbardar: s(r.name_anbardar),
    accepted_gomrok: s(r.accepted_gomrok),
    company_bimeh: s(r.company_bimeh),
  }
}

// build "name family (national_code)" — matches how the APEX app shows companies/reps
const companyLabel = (r: Record<string, any>) =>
  `${r.name ?? ''} ${r.family ?? ''} ${r.national_code ? `(${r.national_code})` : ''}`.trim()

const ownerLabel = (r: Record<string, any>) =>
  `${r.name ?? ''} ${r.family ?? ''}`.trim()

export function TallyHeaderForm() {
  const navigate = useNavigate()
  const { tallyNumber } = useParams<{ tallyNumber: string }>()
  const isEdit = tallyNumber != null
  const isLegacyId = Boolean(tallyNumber && /^\d+$/.test(tallyNumber))

  // when editing, load the existing header once and populate the form
  const { data: existing } = useQuery({
    queryKey: ['tally-header', tallyNumber],
    queryFn: () => apiGet<Record<string, any>>(
      isLegacyId
        ? `/tally-header/${tallyNumber}`
        : `/tally-header/by-number/${encodeURIComponent(tallyNumber!)}`
    ),
    enabled: isEdit, // only fetch in edit mode
  })
  const editId = existing?.id_tali == null ? null : Number(existing.id_tali)

  useEffect(() => {
    if (existing) setForm(rowToState(existing))
  }, [existing])
  const [form, setForm] = useState<TallyHeaderState>(EMPTY)
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState<string | null>(null)

  // one helper to update any field by key
  const set = <K extends keyof TallyHeaderState>(key: K, value: TallyHeaderState[K]) =>
    setForm((f) => ({ ...f, [key]: value }))

  // async function handleSave() {
  //   setSaving(true)
  //   setError(null)
  //   try {
  //   //   const created = await apiPost<{ id_tali: number }>('/tally-header', toPayload(form))
  //     const created = await apiSend<{ id_tali: number }>('/tally-header', 'POST', toPayload(form))
  //     // once saved we have the new tally id — go to its detail view (built next).
  //     // for now, navigate back to the tally list.
  //     navigate('/tally')
  //     return created
  //   } catch (e) {
  //     setError('ذخیره تالی ناموفق بود. لطفاً دوباره تلاش کنید.')
  //   } finally {
  //     setSaving(false)
  //   }
  // }
  async function handleSave() {
    setSaving(true)
    setError(null)
    try {
      if (isEdit) {
        if (editId == null) {
          throw new Error('اطلاعات تالی هنوز بارگذاری نشده است.')
        }
        await apiSend(`/tally-header/${editId}`, 'PUT', toPayload(form))
        const publicNumber = String(existing?.tali_number ?? tallyNumber)
        navigate(`/tally/${encodeURIComponent(publicNumber)}`)
      } else {
        const created = await apiSend<{ id_tali: number; tali_number: string }>('/tally-header', 'POST', toPayload(form))
        navigate(`/tally/${encodeURIComponent(created.tali_number)}`)
      }
    } catch (e) {
      setError('ذخیره تالی ناموفق بود. لطفاً دوباره تلاش کنید.')
    } finally {
      setSaving(false)
    }
  }
  return (
    <div dir="rtl" style={{ maxWidth: 1000, margin: '0 auto' }}>
      <Group justify="space-between" mb="md">
        <Title order={2} fw={700}>{isEdit ? 'ویرایش تالی' : 'ایجاد تالی جدید'}</Title>
        <Button onClick={handleSave} loading={saving}>{isEdit ? 'ذخیره تغییرات' : 'ایجاد تالی'}</Button>
      </Group>

      <Paper shadow="xs" p="lg" pos="relative">
        <LoadingOverlay visible={saving} />

        <Grid gutter="md">
          {/* --- row: karaneh / transit + border row number --- */}
          <Grid.Col span={{ base: 12, md: 6 }}>
            <TextInput
              label="شماره کارنه / ترانزیت"
              value={form.number_karaneh}
              onChange={(e) => set('number_karaneh', e.currentTarget.value)}
            />
          </Grid.Col>
          <Grid.Col span={{ base: 12, md: 6 }}>
            <TextInput
              label="ردیف مرزی"
              inputMode="numeric"
              value={form.radef_marze}
              onChange={(e) => set('radef_marze', e.currentTarget.value)}
            />
          </Grid.Col>

          {/* --- row: entry border (term cat 1) + origin country (term cat 2) --- */}
          <Grid.Col span={{ base: 12, md: 6 }}>
            <RefSelect
              label="نام مرز ورودی"
              path="/terms"
              params={{ category_id: 1 }}
              valueKey="sys_term_id"
              labelKey="value"
              value={form.id_marze}
              onChange={(v) => set('id_marze', v)}
            />
          </Grid.Col>
          <Grid.Col span={{ base: 12, md: 6 }}>
            <RefSelect
              label="مبدا حمل (کشور)"
              path="/terms"
              params={{ category_id: 2 }}
              valueKey="sys_term_id"
              labelKey="value"
              value={form.id_country}
              onChange={(v) => set('id_country', v)}
            />
          </Grid.Col>

          {/* --- row: two Jalali dates --- */}
          <Grid.Col span={{ base: 12, md: 6 }}>
            <JalaliDate
              label="تاریخ ورود به مرز"
              value={form.date_enter_marze}
              onChange={(iso) => set('date_enter_marze', iso)}
            />
          </Grid.Col>
          <Grid.Col span={{ base: 12, md: 6 }}>
            <JalaliDate
              label="تاریخ تخلیه"
              value={form.date_unloading}
              onChange={(iso) => set('date_unloading', iso)}
            />
          </Grid.Col>

          {/* --- row: transport company + its representative (both from companies) --- */}
          <Grid.Col span={{ base: 12, md: 6 }}>
            <RefSelect
              label="نام شرکت حمل"
              path="/companies"
              valueKey="id_repre_company"
              labelKey={companyLabel}
              value={form.id_company}
              onChange={(v) => set('id_company', v)}
            />
          </Grid.Col>
          <Grid.Col span={{ base: 12, md: 6 }}>
            <RefSelect
              label="نام نماینده شرکت حمل"
              path="/companies"
              valueKey="id_repre_company"
              labelKey={companyLabel}
              value={form.id_respons_company}
              onChange={(v) => set('id_respons_company', v)}
            />
          </Grid.Col>

          {/* --- row: goods owner + assessor --- */}
          <Grid.Col span={{ base: 12, md: 6 }}>
            <RefSelect
              label="صاحب کالا"
              path="/owners"
              valueKey="id_owner"
              labelKey={ownerLabel}
              value={form.id_product_ownear}
              onChange={(v) => set('id_product_ownear', v)}
            />
          </Grid.Col>
          <Grid.Col span={{ base: 12, md: 6 }}>
            <TextInput
              label="نام ارزیاب"
              value={form.name_arzyab}
              onChange={(e) => set('name_arzyab', e.currentTarget.value)}
            />
          </Grid.Col>

          {/* --- row: insurance number + insurance company --- */}
          <Grid.Col span={{ base: 12, md: 6 }}>
            <TextInput
              label="شماره بیمه نامه"
              value={form.number_bimeh}
              onChange={(e) => set('number_bimeh', e.currentTarget.value)}
            />
          </Grid.Col>
          <Grid.Col span={{ base: 12, md: 6 }}>
            <TextInput
              label="شرکت بیمه گر"
              value={form.company_bimeh}
              onChange={(e) => set('company_bimeh', e.currentTarget.value)}
            />
          </Grid.Col>

          {/* --- row: barnameh number + electronic receipt number --- */}
          <Grid.Col span={{ base: 12, md: 6 }}>
            <TextInput
              label="شماره بارنامه"
              value={form.number_barnameh}
              onChange={(e) => set('number_barnameh', e.currentTarget.value)}
            />
          </Grid.Col>
          <Grid.Col span={{ base: 12, md: 6 }}>
            <TextInput
              label="شناسه ملی صاحب کالا"
              inputMode="numeric"
              value={form.number_ghabz}
              onChange={(e) => set('number_ghabz', e.currentTarget.value)}
            />
          </Grid.Col>

          {/* --- row: tally number + warehouse keeper --- */}
          <Grid.Col span={{ base: 12, md: 6 }}>
            <TextInput
              label="شماره تالی"
              value={isEdit ? String(existing?.tali_number ?? '') : 'پس از ثبت، به‌صورت خودکار تخصیص داده می‌شود'}
              readOnly
              disabled={!isEdit}
              styles={isEdit ? { input: { direction: 'ltr', textAlign: 'right' } } : undefined}
            />
          </Grid.Col>
          <Grid.Col span={{ base: 12, md: 6 }}>
            <TextInput
              label="نام انبار دار"
              value={form.name_anbardar}
              onChange={(e) => set('name_anbardar', e.currentTarget.value)}
            />
          </Grid.Col>

          {/* --- row: two yes/no radios --- */}
          <Grid.Col span={{ base: 12, md: 6 }}>
            <Radio.Group
              label="آیا بیمه دارد؟"
              value={form.is_bimeh}
              onChange={(v) => set('is_bimeh', v)}
            >
              <Group mt="xs">
                <Radio value="بله" label="بله" />
                <Radio value="خیر" label="خیر" />
              </Group>
            </Radio.Group>
          </Grid.Col>
          <Grid.Col span={{ base: 12, md: 6 }}>
            <Radio.Group
              label="تایید گمرک"
              value={form.accepted_gomrok}
              onChange={(v) => set('accepted_gomrok', v)}
            >
              <Group mt="xs">
                <Radio value="بله" label="بله" />
                <Radio value="خیر" label="خیر" />
              </Group>
            </Radio.Group>
          </Grid.Col>
        </Grid>

        {error && (
          <div style={{ color: 'var(--mantine-color-red-6)', marginTop: 16 }}>{error}</div>
        )}

        <Group justify="flex-start" mt="xl">
          <Button onClick={handleSave} loading={saving}>ایجاد تالی</Button>
          <BackButton to="/tally" />
        </Group>
      </Paper>
    </div>
  )
}
