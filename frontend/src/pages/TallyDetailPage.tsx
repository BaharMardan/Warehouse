// import { useState } from 'react'
// import { useParams, useNavigate } from 'react-router-dom'
// import { BackButton } from '../components/BackButton'
// import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
// import {
//   Title, Button, Group, Table, Paper, Loader, Center, Text, Stack, Divider,
//   Modal, TextInput, Select, Grid,
// } from '@mantine/core'
// import { apiGet, apiSend } from '../api/client'
// import { RefSelect } from '../components/RefSelect'
// import { CommodityPicker, type Commodity } from '../components/CommodityPicker'
// import { PlateInput } from '../components/PlateInput'
// import { ContainerFields } from '../components/ContainerFields'
// // import { TallyDiamoundSection } from '../components/TallyDiamoundSection'
// import { TallyJunctionSection } from '../components/TallyJunctionSection'
// import { tallyJunctions } from '../components/junctions'
// /**
//  * TallyDetailPage — one tally's detail view at /tally/:id.
//  * Top: header actions (edit button returns to the form).
//  * Below: the goods-lines grid (جزئیات تالی) — add / edit / delete rows, each line
//  * scoped to this tally via id_headers_tali.
//  */

// type DetailRow = {
//   id_tali_details: number
//   id_headers_tali: number
//   id_anbar: number | null
//   anbar_name: string | null
//   id_tagh_anbar: number | null
//   tagh_name: string | null
//   number_ghabze_anbar: number | null
//   code_groupe_kala: number
//   description_kala: string | null
//   hscode: string | null
//   type_bastem: string | null
//   number_kala: number
//   weighte: number
//   type_number_kantiner: string | null
//   number_ghabze_bskol: number | null
//   weighte_baskol: number
//   number_hamel: string | null
//   zarib_mahal: string | null
//   container_type: string | null
//   container_number: string | null
// }

// type LineForm = {
//   id_anbar: number | null
//   id_tagh_anbar: number | null
//   code_groupe_kala: string
//   description_kala: string
//   hscode: string
//   type_bastem: string
//   number_kala: string
//   weighte: string
//   weighte_baskol: string
//   type_number_kantiner: string
//   number_hamel: string
//   zarib_mahal: string
//   container_type: string
//   container_number: string
// }

// const EMPTY_LINE: LineForm = {
//   id_anbar: null, id_tagh_anbar: null, code_groupe_kala: '', description_kala: '',
//   hscode: '', type_bastem: '', number_kala: '', weighte: '', weighte_baskol: '',
//   type_number_kantiner: '', number_hamel: '', zarib_mahal: '',
//   container_type: '', container_number: '',
// }

// // Persian/Arabic digits -> Latin, so numeric fields accept ۱۲۳
// function normalizeDigits(s: string): string {
//   return s
//     .replace(/[\u06F0-\u06F9]/g, (d) => String(d.charCodeAt(0) - 0x06f0))
//     .replace(/[\u0660-\u0669]/g, (d) => String(d.charCodeAt(0) - 0x0660))
// }

// export function TallyDetailPage() {
//   const { id } = useParams<{ id: string }>()
//   const headerId = Number(id)
//   const navigate = useNavigate()
//   const qc = useQueryClient()

//   const [modalOpen, setModalOpen] = useState(false)
//   const [editingId, setEditingId] = useState<number | null>(null) // null = adding
//   const [line, setLine] = useState<LineForm>(EMPTY_LINE)
//   // the commodity picked from the catalog for this line (drives autofill + info display)
//   const [picked, setPicked] = useState<Commodity | null>(null)

//   const { data: lines, isLoading, isError } = useQuery({
//     queryKey: ['tally-details', headerId],
//     queryFn: () => apiGet<DetailRow[]>(`/tally/${headerId}/details`),
//   })
//   // load the header so we can show its business tally number (TALI_NUMBER),
//   // not the internal ID_TALI that's in the URL
//   const { data: header } = useQuery({
//     queryKey: ['tally-header', headerId],
//     queryFn: () => apiGet<Record<string, any>>(`/tally-header/${headerId}`),
//   })

//   function toPayload(f: LineForm) {
//     const numOrNull = (v: string) => (v.trim() === '' ? null : Number(normalizeDigits(v)))
//     const strOrNull = (v: string) => (v.trim() === '' ? null : v)
//     return {
//       id_headers_tali: headerId,
//       id_anbar: f.id_anbar,
//       id_tagh_anbar: f.id_tagh_anbar,
//       code_groupe_kala: Number(normalizeDigits(f.code_groupe_kala)),
//       description_kala: strOrNull(f.description_kala),
//       hscode: strOrNull(f.hscode),
//       type_bastem: strOrNull(f.type_bastem),
//       number_kala: Number(normalizeDigits(f.number_kala)),
//       weighte: Number(normalizeDigits(f.weighte)),
//       weighte_baskol: Number(normalizeDigits(f.weighte_baskol)),
//       type_number_kantiner: strOrNull(f.type_number_kantiner),
//       number_hamel: strOrNull(f.number_hamel),
//       zarib_mahal: strOrNull(f.zarib_mahal),
//       container_type: strOrNull(f.container_type),
//       container_number: strOrNull(f.container_number),
//     }
//   }

//   const saveMutation = useMutation({
//     mutationFn: (f: LineForm) =>
//       editingId == null
//         ? apiSend('/tally-details', 'POST', toPayload(f))
//         : apiSend(`/tally-details/${editingId}`, 'PUT', toPayload(f)),
//     onSuccess: () => {
//       qc.invalidateQueries({ queryKey: ['tally-details', headerId] })
//       setModalOpen(false)
//     },
//   })

//   const deleteMutation = useMutation({
//     mutationFn: (lineId: number) => apiSend(`/tally-details/${lineId}`, 'DELETE'),
//     onSuccess: () => qc.invalidateQueries({ queryKey: ['tally-details', headerId] }),
//   })

//   function openAdd() {
//     setEditingId(null)
//     setLine(EMPTY_LINE)
//     setPicked(null)
//     setModalOpen(true)
//   }

//   // Snapshot the descriptive fields this line has columns for. The storage group
//   // (code_groupe_kala) is handled by CommodityPicker via onGroupChange.
//   function onPickCommodity(c: Commodity | null) {
//     setPicked(c)
//     if (!c) return
//     setLine((l) => ({
//       ...l,
//       description_kala: c.description_fa ?? '',
//       hscode: c.hs_code ?? '',
//     }))
//   }

//   function openEdit(row: DetailRow) {
//     setEditingId(row.id_tali_details)
//     setPicked(null)
//     setLine({
//       id_anbar: row.id_anbar,
//       id_tagh_anbar: row.id_tagh_anbar,
//       code_groupe_kala: String(row.code_groupe_kala ?? ''),
//       description_kala: row.description_kala ?? '',
//       hscode: row.hscode ?? '',
//       type_bastem: row.type_bastem ?? '',
//       number_kala: String(row.number_kala ?? ''),
//       weighte: String(row.weighte ?? ''),
//       weighte_baskol: String(row.weighte_baskol ?? ''),
//       type_number_kantiner: row.type_number_kantiner ?? '',
//       number_hamel: row.number_hamel ?? '',
//       zarib_mahal: row.zarib_mahal != null ? String(row.zarib_mahal) : '',
//       container_type: row.container_type ?? '',
//       container_number: row.container_number ?? '',
//     })
//     setModalOpen(true)
//   }

//   const set = <K extends keyof LineForm>(k: K, v: LineForm[K]) =>
//     setLine((l) => ({ ...l, [k]: v }))

//   // the 4 NOT NULL fields must be filled before save is allowed
//   const canSave =
//     line.code_groupe_kala.trim() !== '' &&
//     line.number_kala.trim() !== '' &&
//     line.weighte.trim() !== '' &&
//     line.weighte_baskol.trim() !== ''

//   return (
//     <div dir="rtl">
//       <Group justify="space-between" mb="md">
//         <Title order={2}>
//           جزئیات تالی {header?.tali_number ? `شماره ${header.tali_number}` : `#${headerId}`}
//         </Title>
//         <Group>
          
//           <Button variant="light" onClick={() => navigate(`/tally/${headerId}/edit`)}>ویرایش سربرگ</Button>
//           <Button variant="light" color="teal" onClick={async () => {
//             const r = await apiSend<{ id_ghabz: number }>(`/ghabz/from-tally/${headerId}`, 'POST')
//             navigate(`/ghabz/${r.id_ghabz}/edit`)
//           }}>صدور قبض انبار</Button><BackButton to="/tally" />
//         </Group>
//       </Group>

//       <Paper shadow="xs" p="md">
//         <Group justify="space-between" mb="sm">
//           <Text fw={600}>ردیف‌های کالا</Text>
//           <Button onClick={openAdd}>افزودن ردیف</Button>
//         </Group>
//         <Divider mb="sm" />

//         {isLoading && <Center py="xl"><Loader /></Center>}
//         {isError && <Center py="xl"><Text c="red">خطا در بارگذاری ردیف‌ها.</Text></Center>}

//         {lines && lines.length === 0 && (
//           <Center py="xl">
//             <Text c="dimmed">هنوز ردیفی ثبت نشده است. «افزودن ردیف» را بزنید.</Text>
//           </Center>
//         )}

//         {lines && lines.length > 0 && (
//           <Table striped highlightOnHover withTableBorder>
//             <Table.Thead>
//               <Table.Tr>
//                 <Table.Th>کد گروه کالا</Table.Th>
//                 <Table.Th>شرح کالا</Table.Th>
//                 <Table.Th>Hscode</Table.Th>
//                 <Table.Th>نوع بسته‌بندی</Table.Th>
//                 <Table.Th>تعداد</Table.Th>
//                 <Table.Th>وزن</Table.Th>
//                 <Table.Th>وزن باسکول</Table.Th>
//                 <Table.Th>انبار</Table.Th>
//                 <Table.Th>طاق</Table.Th>
//                 <Table.Th>عملیات</Table.Th>
//               </Table.Tr>
//             </Table.Thead>
//             <Table.Tbody>
//               {lines.map((row) => (
//                 <Table.Tr key={row.id_tali_details}>
//                   <Table.Td>{row.code_groupe_kala}</Table.Td>
//                   <Table.Td>{row.description_kala ?? '—'}</Table.Td>
//                   <Table.Td>{row.hscode ?? '—'}</Table.Td>
//                   <Table.Td>{row.type_bastem ?? '—'}</Table.Td>
//                   <Table.Td>{row.number_kala}</Table.Td>
//                   <Table.Td>{row.weighte}</Table.Td>
//                   <Table.Td>{row.weighte_baskol}</Table.Td>
//                   <Table.Td>{row.anbar_name ?? '—'}</Table.Td>
//                   <Table.Td>{row.tagh_name ?? '—'}</Table.Td>
//                   <Table.Td>
//                     <Group gap="xs">
//                       <Button size="xs" variant="light" onClick={() => openEdit(row)}>ویرایش</Button>
//                       <Button
//                         size="xs" variant="light" color="red"
//                         onClick={() => deleteMutation.mutate(row.id_tali_details)}
//                       >
//                         حذف
//                       </Button>
//                     </Group>
//                   </Table.Td>
//                 </Table.Tr>
//               ))}
//             </Table.Tbody>
//           </Table>
//         )}
//       </Paper>
//       {tallyJunctions.map((cfg) => (
//         <TallyJunctionSection key={cfg.key} config={cfg} tallyId={headerId} />
//       ))}
//       <Modal
//         opened={modalOpen}
//         onClose={() => setModalOpen(false)}
//         title={editingId == null ? 'افزودن ردیف کالا' : 'ویرایش ردیف کالا'}
//         size="lg"
//       >
//         <Stack>
//           <CommodityPicker
//             picked={picked}
//             onPick={onPickCommodity}
//             groupValue={line.code_groupe_kala.trim() === '' ? null : Number(line.code_groupe_kala)}
//             onGroupChange={(v) => set('code_groupe_kala', v == null ? '' : String(v))}
//           />
//           <Divider />
//           <Grid>
//             <Grid.Col span={6}>
//               <TextInput
//                 label="شرح کالا"
//                 value={line.description_kala}
//                 onChange={(e) => set('description_kala', e.currentTarget.value)}
//               />
//             </Grid.Col>
//             <Grid.Col span={6}>
//               <TextInput
//                 label="Hscode"
//                 value={line.hscode}
//                 onChange={(e) => set('hscode', e.currentTarget.value)}
//               />
//             </Grid.Col>
//             <Grid.Col span={6}>
//               <Select
//                 label="نوع بسته‌بندی"
//                 placeholder="انتخاب کنید"
//                 data={['کیسه‌ای', 'نگله', 'پالت']}
//                 value={line.type_bastem || null}
//                 onChange={(v) => set('type_bastem', v ?? '')}
//                 clearable
//               />
//             </Grid.Col>
//             <Grid.Col span={4}>
//               <TextInput
//                 label="تعداد" required inputMode="numeric"
//                 value={line.number_kala}
//                 onChange={(e) => set('number_kala', e.currentTarget.value)}
//               />
//             </Grid.Col>
//             <Grid.Col span={4}>
//               <TextInput
//                 label="وزن" required inputMode="numeric"
//                 value={line.weighte}
//                 onChange={(e) => set('weighte', e.currentTarget.value)}
//               />
//             </Grid.Col>
//             <Grid.Col span={4}>
//               <TextInput
//                 label="وزن باسکول" required inputMode="numeric"
//                 value={line.weighte_baskol}
//                 onChange={(e) => set('weighte_baskol', e.currentTarget.value)}
//               />
//             </Grid.Col>
//             <Grid.Col span={6}>
//               <RefSelect
//                 label="انبار"
//                 path="/anbar"
//                 valueKey="id_anbar"
//                 labelKey="name_anbar"
//                 value={line.id_anbar}
//                 onChange={(v) => set('id_anbar', v)}
//               />
//             </Grid.Col>
//             <Grid.Col span={6}>
//               <RefSelect
//                 label="طاق"
//                 path="/tagh"
//                 valueKey="id_tagh"
//                 labelKey="name_tagh"
//                 value={line.id_tagh_anbar}
//                 onChange={(v) => set('id_tagh_anbar', v)}
//               />
//             </Grid.Col>
//             <Grid.Col span={12}>
//               <PlateInput
//                 label="شماره حامل"
//                 value={line.number_hamel}
//                 onChange={(v) => set('number_hamel', v)}
//               />
//             </Grid.Col>
//             <ContainerFields
//               type={line.container_type}
//               number={line.container_number}
//               onTypeChange={(v) => set('container_type', v)}
//               onNumberChange={(v) => set('container_number', v)}
//             />
//             <Grid.Col span={6}>
//               <Select
//                 label="ضریب محل"
//                 placeholder="انتخاب کنید"
//                 data={['انبارداری مسقف', 'انبارداری تانگارد', 'انبارداری بارانداز', 'انبارداری محوطه']}
//                 value={line.zarib_mahal || null}
//                 onChange={(v) => set('zarib_mahal', v ?? '')}
//                 clearable
//               />
//             </Grid.Col>
//           </Grid>

//           <Group justify="flex-start" mt="md">
//             <Button
//               onClick={() => saveMutation.mutate(line)}
//               loading={saveMutation.isPending}
//               disabled={!canSave}
//             >
//               ذخیره
//             </Button>
//             <Button variant="subtle" onClick={() => setModalOpen(false)}>لغو</Button>
//           </Group>
//         </Stack>
//       </Modal>
//     </div>
//   )
// }

// import { useState } from 'react'
// import { useParams, useNavigate } from 'react-router-dom'
// import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
// import {
//   Title, Button, Group, Table, Paper, Loader, Center, Text, Stack, Divider,
//   Modal, TextInput, Grid,
// } from '@mantine/core'
// import { apiGet, apiSend } from '../api/client'
// import { RefSelect } from '../components/RefSelect'
// import { CommodityPicker, type Commodity } from '../components/CommodityPicker'
// import { PlateInput } from '../components/PlateInput'
// import { ContainerFields } from '../components/ContainerFields'
// // import { TallyDiamoundSection } from '../components/TallyDiamoundSection'
// import { TallyJunctionSection } from '../components/TallyJunctionSection'
// import { tallyJunctions } from '../components/junctions'
// /**
//  * TallyDetailPage — one tally's detail view at /tally/:id.
//  * Top: header actions (edit button returns to the form).
//  * Below: the goods-lines grid (جزئیات تالی) — add / edit / delete rows, each line
//  * scoped to this tally via id_headers_tali.
//  */

// type DetailRow = {
//   id_tali_details: number
//   id_headers_tali: number
//   id_anbar: number | null
//   anbar_name: string | null
//   id_tagh_anbar: number | null
//   tagh_name: string | null
//   number_ghabze_anbar: number | null
//   code_groupe_kala: number
//   description_kala: string | null
//   hscode: string | null
//   type_bastem: string | null
//   number_kala: number
//   weighte: number
//   type_number_kantiner: string | null
//   number_ghabze_bskol: number | null
//   weighte_baskol: number
//   number_hamel: string | null
//   zarib_mahal: number | null
//   container_type: string | null
//   container_number: string | null
// }

// type LineForm = {
//   id_anbar: number | null
//   id_tagh_anbar: number | null
//   code_groupe_kala: string
//   description_kala: string
//   hscode: string
//   type_bastem: string
//   number_kala: string
//   weighte: string
//   weighte_baskol: string
//   type_number_kantiner: string
//   number_hamel: string
//   zarib_mahal: string
//   container_type: string
//   container_number: string
// }

// const EMPTY_LINE: LineForm = {
//   id_anbar: null, id_tagh_anbar: null, code_groupe_kala: '', description_kala: '',
//   hscode: '', type_bastem: '', number_kala: '', weighte: '', weighte_baskol: '',
//   type_number_kantiner: '', number_hamel: '', zarib_mahal: '',
//   container_type: '', container_number: '',
// }

// // Persian/Arabic digits -> Latin, so numeric fields accept ۱۲۳
// function normalizeDigits(s: string): string {
//   return s
//     .replace(/[\u06F0-\u06F9]/g, (d) => String(d.charCodeAt(0) - 0x06f0))
//     .replace(/[\u0660-\u0669]/g, (d) => String(d.charCodeAt(0) - 0x0660))
// }

// export function TallyDetailPage() {
//   const { id } = useParams<{ id: string }>()
//   const headerId = Number(id)
//   const navigate = useNavigate()
//   const qc = useQueryClient()

//   const [modalOpen, setModalOpen] = useState(false)
//   const [editingId, setEditingId] = useState<number | null>(null) // null = adding
//   const [line, setLine] = useState<LineForm>(EMPTY_LINE)
//   // the commodity picked from the catalog for this line (drives autofill + info display)
//   const [picked, setPicked] = useState<Commodity | null>(null)

//   const { data: lines, isLoading, isError } = useQuery({
//     queryKey: ['tally-details', headerId],
//     queryFn: () => apiGet<DetailRow[]>(`/tally/${headerId}/details`),
//   })
//   // load the header so we can show its business tally number (TALI_NUMBER),
//   // not the internal ID_TALI that's in the URL
//   const { data: header } = useQuery({
//     queryKey: ['tally-header', headerId],
//     queryFn: () => apiGet<Record<string, any>>(`/tally-header/${headerId}`),
//   })

//   function toPayload(f: LineForm) {
//     const numOrNull = (v: string) => (v.trim() === '' ? null : Number(normalizeDigits(v)))
//     const strOrNull = (v: string) => (v.trim() === '' ? null : v)
//     return {
//       id_headers_tali: headerId,
//       id_anbar: f.id_anbar,
//       id_tagh_anbar: f.id_tagh_anbar,
//       code_groupe_kala: Number(normalizeDigits(f.code_groupe_kala)),
//       description_kala: strOrNull(f.description_kala),
//       hscode: strOrNull(f.hscode),
//       type_bastem: strOrNull(f.type_bastem),
//       number_kala: Number(normalizeDigits(f.number_kala)),
//       weighte: Number(normalizeDigits(f.weighte)),
//       weighte_baskol: Number(normalizeDigits(f.weighte_baskol)),
//       type_number_kantiner: strOrNull(f.type_number_kantiner),
//       number_hamel: strOrNull(f.number_hamel),
//       zarib_mahal: numOrNull(f.zarib_mahal),
//       container_type: strOrNull(f.container_type),
//       container_number: strOrNull(f.container_number),
//     }
//   }

//   const saveMutation = useMutation({
//     mutationFn: (f: LineForm) =>
//       editingId == null
//         ? apiSend('/tally-details', 'POST', toPayload(f))
//         : apiSend(`/tally-details/${editingId}`, 'PUT', toPayload(f)),
//     onSuccess: () => {
//       qc.invalidateQueries({ queryKey: ['tally-details', headerId] })
//       setModalOpen(false)
//     },
//   })

//   const deleteMutation = useMutation({
//     mutationFn: (lineId: number) => apiSend(`/tally-details/${lineId}`, 'DELETE'),
//     onSuccess: () => qc.invalidateQueries({ queryKey: ['tally-details', headerId] }),
//   })

//   function openAdd() {
//     setEditingId(null)
//     setLine(EMPTY_LINE)
//     setPicked(null)
//     setModalOpen(true)
//   }

//   // Snapshot the descriptive fields this line has columns for. The storage group
//   // (code_groupe_kala) is handled by CommodityPicker via onGroupChange.
//   function onPickCommodity(c: Commodity | null) {
//     setPicked(c)
//     if (!c) return
//     setLine((l) => ({
//       ...l,
//       description_kala: c.description_fa ?? '',
//       hscode: c.hs_code ?? '',
//     }))
//   }

//   function openEdit(row: DetailRow) {
//     setEditingId(row.id_tali_details)
//     setPicked(null)
//     setLine({
//       id_anbar: row.id_anbar,
//       id_tagh_anbar: row.id_tagh_anbar,
//       code_groupe_kala: String(row.code_groupe_kala ?? ''),
//       description_kala: row.description_kala ?? '',
//       hscode: row.hscode ?? '',
//       type_bastem: row.type_bastem ?? '',
//       number_kala: String(row.number_kala ?? ''),
//       weighte: String(row.weighte ?? ''),
//       weighte_baskol: String(row.weighte_baskol ?? ''),
//       type_number_kantiner: row.type_number_kantiner ?? '',
//       number_hamel: row.number_hamel ?? '',
//       zarib_mahal: row.zarib_mahal != null ? String(row.zarib_mahal) : '',
//       container_type: row.container_type ?? '',
//       container_number: row.container_number ?? '',
//     })
//     setModalOpen(true)
//   }

//   const set = <K extends keyof LineForm>(k: K, v: LineForm[K]) =>
//     setLine((l) => ({ ...l, [k]: v }))

//   // the 4 NOT NULL fields must be filled before save is allowed
//   const canSave =
//     line.code_groupe_kala.trim() !== '' &&
//     line.number_kala.trim() !== '' &&
//     line.weighte.trim() !== '' &&
//     line.weighte_baskol.trim() !== ''

//   return (
//     <div dir="rtl">
//       <Group justify="space-between" mb="md">
//         <Title order={2}>
//           جزئیات تالی {header?.tali_number ? `شماره ${header.tali_number}` : `#${headerId}`}
//         </Title>
//         <Group>
//           <Button variant="subtle" onClick={() => navigate('/tally')}>بازگشت</Button>
//           <Button variant="light" onClick={() => navigate(`/tally/${headerId}/edit`)}>ویرایش سربرگ</Button>
//           <Button variant="light" color="teal" onClick={async () => {
//             const r = await apiSend<{ id_ghabz: number }>(`/ghabz/from-tally/${headerId}`, 'POST')
//             navigate(`/ghabz/${r.id_ghabz}/edit`)
//           }}>صدور قبض انبار</Button>
//         </Group>
//       </Group>

//       <Paper shadow="xs" p="md">
//         <Group justify="space-between" mb="sm">
//           <Text fw={600}>ردیف‌های کالا</Text>
//           <Button onClick={openAdd}>افزودن ردیف</Button>
//         </Group>
//         <Divider mb="sm" />

//         {isLoading && <Center py="xl"><Loader /></Center>}
//         {isError && <Center py="xl"><Text c="red">خطا در بارگذاری ردیف‌ها.</Text></Center>}

//         {lines && lines.length === 0 && (
//           <Center py="xl">
//             <Text c="dimmed">هنوز ردیفی ثبت نشده است. «افزودن ردیف» را بزنید.</Text>
//           </Center>
//         )}

//         {lines && lines.length > 0 && (
//           <Table striped highlightOnHover withTableBorder>
//             <Table.Thead>
//               <Table.Tr>
//                 <Table.Th>کد گروه کالا</Table.Th>
//                 <Table.Th>شرح کالا</Table.Th>
//                 <Table.Th>Hscode</Table.Th>
//                 <Table.Th>نوع بسته‌بندی</Table.Th>
//                 <Table.Th>تعداد</Table.Th>
//                 <Table.Th>وزن</Table.Th>
//                 <Table.Th>وزن باسکول</Table.Th>
//                 <Table.Th>انبار</Table.Th>
//                 <Table.Th>طاق</Table.Th>
//                 <Table.Th>عملیات</Table.Th>
//               </Table.Tr>
//             </Table.Thead>
//             <Table.Tbody>
//               {lines.map((row) => (
//                 <Table.Tr key={row.id_tali_details}>
//                   <Table.Td>{row.code_groupe_kala}</Table.Td>
//                   <Table.Td>{row.description_kala ?? '—'}</Table.Td>
//                   <Table.Td>{row.hscode ?? '—'}</Table.Td>
//                   <Table.Td>{row.type_bastem ?? '—'}</Table.Td>
//                   <Table.Td>{row.number_kala}</Table.Td>
//                   <Table.Td>{row.weighte}</Table.Td>
//                   <Table.Td>{row.weighte_baskol}</Table.Td>
//                   <Table.Td>{row.anbar_name ?? '—'}</Table.Td>
//                   <Table.Td>{row.tagh_name ?? '—'}</Table.Td>
//                   <Table.Td>
//                     <Group gap="xs">
//                       <Button size="xs" variant="light" onClick={() => openEdit(row)}>ویرایش</Button>
//                       <Button
//                         size="xs" variant="light" color="red"
//                         onClick={() => deleteMutation.mutate(row.id_tali_details)}
//                       >
//                         حذف
//                       </Button>
//                     </Group>
//                   </Table.Td>
//                 </Table.Tr>
//               ))}
//             </Table.Tbody>
//           </Table>
//         )}
//       </Paper>
//       {tallyJunctions.map((cfg) => (
//         <TallyJunctionSection key={cfg.key} config={cfg} tallyId={headerId} />
//       ))}
//       <Modal
//         opened={modalOpen}
//         onClose={() => setModalOpen(false)}
//         title={editingId == null ? 'افزودن ردیف کالا' : 'ویرایش ردیف کالا'}
//         size="lg"
//       >
//         <Stack>
//           <CommodityPicker
//             picked={picked}
//             onPick={onPickCommodity}
//             groupValue={line.code_groupe_kala.trim() === '' ? null : Number(line.code_groupe_kala)}
//             onGroupChange={(v) => set('code_groupe_kala', v == null ? '' : String(v))}
//           />
//           <Divider />
//           <Grid>
//             <Grid.Col span={6}>
//               <TextInput
//                 label="شرح کالا"
//                 value={line.description_kala}
//                 onChange={(e) => set('description_kala', e.currentTarget.value)}
//               />
//             </Grid.Col>
//             <Grid.Col span={6}>
//               <TextInput
//                 label="Hscode"
//                 value={line.hscode}
//                 onChange={(e) => set('hscode', e.currentTarget.value)}
//               />
//             </Grid.Col>
//             <Grid.Col span={6}>
//               <TextInput
//                 label="نوع بسته‌بندی"
//                 value={line.type_bastem}
//                 onChange={(e) => set('type_bastem', e.currentTarget.value)}
//               />
//             </Grid.Col>
//             <Grid.Col span={4}>
//               <TextInput
//                 label="تعداد" required inputMode="numeric"
//                 value={line.number_kala}
//                 onChange={(e) => set('number_kala', e.currentTarget.value)}
//               />
//             </Grid.Col>
//             <Grid.Col span={4}>
//               <TextInput
//                 label="وزن" required inputMode="numeric"
//                 value={line.weighte}
//                 onChange={(e) => set('weighte', e.currentTarget.value)}
//               />
//             </Grid.Col>
//             <Grid.Col span={4}>
//               <TextInput
//                 label="وزن باسکول" required inputMode="numeric"
//                 value={line.weighte_baskol}
//                 onChange={(e) => set('weighte_baskol', e.currentTarget.value)}
//               />
//             </Grid.Col>
//             <Grid.Col span={6}>
//               <RefSelect
//                 label="انبار"
//                 path="/anbar"
//                 valueKey="id_anbar"
//                 labelKey="name_anbar"
//                 value={line.id_anbar}
//                 onChange={(v) => set('id_anbar', v)}
//               />
//             </Grid.Col>
//             <Grid.Col span={6}>
//               <RefSelect
//                 label="طاق"
//                 path="/tagh"
//                 valueKey="id_tagh"
//                 labelKey="name_tagh"
//                 value={line.id_tagh_anbar}
//                 onChange={(v) => set('id_tagh_anbar', v)}
//               />
//             </Grid.Col>
//             <Grid.Col span={12}>
//               <PlateInput
//                 label="شماره حامل"
//                 value={line.number_hamel}
//                 onChange={(v) => set('number_hamel', v)}
//               />
//             </Grid.Col>
//             <ContainerFields
//               type={line.container_type}
//               number={line.container_number}
//               onTypeChange={(v) => set('container_type', v)}
//               onNumberChange={(v) => set('container_number', v)}
//             />
//             <Grid.Col span={6}>
//               <TextInput
//                 label="ضریب محل"
//                 value={line.zarib_mahal}
//                 onChange={(e) => set('zarib_mahal', e.currentTarget.value)}
//               />
//             </Grid.Col>
//           </Grid>

//           <Group justify="flex-start" mt="md">
//             <Button
//               onClick={() => saveMutation.mutate(line)}
//               loading={saveMutation.isPending}
//               disabled={!canSave}
//             >
//               ذخیره
//             </Button>
//             <Button variant="subtle" onClick={() => setModalOpen(false)}>لغو</Button>
//           </Group>
//         </Stack>
//       </Modal>
//     </div>
//   )
// }

// import { useState } from 'react'
// import { useParams, useNavigate } from 'react-router-dom'
// import { BackButton } from '../components/BackButton'
// import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
// import {
//   Title, Button, Group, Table, Paper, Loader, Center, Text, Stack, Divider,
//   Modal, TextInput, Grid,
// } from '@mantine/core'
// import { apiGet, apiSend } from '../api/client'
// import { RefSelect } from '../components/RefSelect'
// import { CommodityPicker, type Commodity } from '../components/CommodityPicker'
// import { PlateInput } from '../components/PlateInput'
// import { ContainerFields } from '../components/ContainerFields'
// // import { TallyDiamoundSection } from '../components/TallyDiamoundSection'
// import { TallyJunctionSection } from '../components/TallyJunctionSection'
// import { tallyJunctions } from '../components/junctions'
// /**
//  * TallyDetailPage — one tally's detail view at /tally/:id.
//  * Top: header actions (edit button returns to the form).
//  * Below: the goods-lines grid (جزئیات تالی) — add / edit / delete rows, each line
//  * scoped to this tally via id_headers_tali.
//  */

// type DetailRow = {
//   id_tali_details: number
//   id_headers_tali: number
//   id_anbar: number | null
//   anbar_name: string | null
//   id_tagh_anbar: number | null
//   tagh_name: string | null
//   number_ghabze_anbar: number | null
//   code_groupe_kala: number
//   description_kala: string | null
//   hscode: string | null
//   type_bastem: string | null
//   number_kala: number
//   weighte: number
//   type_number_kantiner: string | null
//   number_ghabze_bskol: number | null
//   weighte_baskol: number
//   number_hamel: string | null
//   zarib_mahal: number | null
//   container_type: string | null
//   container_number: string | null
// }

// type LineForm = {
//   id_anbar: number | null
//   id_tagh_anbar: number | null
//   code_groupe_kala: string
//   description_kala: string
//   hscode: string
//   type_bastem: string
//   number_kala: string
//   weighte: string
//   weighte_baskol: string
//   type_number_kantiner: string
//   number_hamel: string
//   zarib_mahal: string
//   container_type: string
//   container_number: string
// }

// const EMPTY_LINE: LineForm = {
//   id_anbar: null, id_tagh_anbar: null, code_groupe_kala: '', description_kala: '',
//   hscode: '', type_bastem: '', number_kala: '', weighte: '', weighte_baskol: '',
//   type_number_kantiner: '', number_hamel: '', zarib_mahal: '',
//   container_type: '', container_number: '',
// }

// // Persian/Arabic digits -> Latin, so numeric fields accept ۱۲۳
// function normalizeDigits(s: string): string {
//   return s
//     .replace(/[\u06F0-\u06F9]/g, (d) => String(d.charCodeAt(0) - 0x06f0))
//     .replace(/[\u0660-\u0669]/g, (d) => String(d.charCodeAt(0) - 0x0660))
// }

// export function TallyDetailPage() {
//   const { id } = useParams<{ id: string }>()
//   const headerId = Number(id)
//   const navigate = useNavigate()
//   const qc = useQueryClient()

//   const [modalOpen, setModalOpen] = useState(false)
//   const [editingId, setEditingId] = useState<number | null>(null) // null = adding
//   const [line, setLine] = useState<LineForm>(EMPTY_LINE)
//   // the commodity picked from the catalog for this line (drives autofill + info display)
//   const [picked, setPicked] = useState<Commodity | null>(null)

//   const { data: lines, isLoading, isError } = useQuery({
//     queryKey: ['tally-details', headerId],
//     queryFn: () => apiGet<DetailRow[]>(`/tally/${headerId}/details`),
//   })
//   // load the header so we can show its business tally number (TALI_NUMBER),
//   // not the internal ID_TALI that's in the URL
//   const { data: header } = useQuery({
//     queryKey: ['tally-header', headerId],
//     queryFn: () => apiGet<Record<string, any>>(`/tally-header/${headerId}`),
//   })

//   function toPayload(f: LineForm) {
//     const numOrNull = (v: string) => (v.trim() === '' ? null : Number(normalizeDigits(v)))
//     const strOrNull = (v: string) => (v.trim() === '' ? null : v)
//     return {
//       id_headers_tali: headerId,
//       id_anbar: f.id_anbar,
//       id_tagh_anbar: f.id_tagh_anbar,
//       code_groupe_kala: Number(normalizeDigits(f.code_groupe_kala)),
//       description_kala: strOrNull(f.description_kala),
//       hscode: strOrNull(f.hscode),
//       type_bastem: strOrNull(f.type_bastem),
//       number_kala: Number(normalizeDigits(f.number_kala)),
//       weighte: Number(normalizeDigits(f.weighte)),
//       weighte_baskol: Number(normalizeDigits(f.weighte_baskol)),
//       type_number_kantiner: strOrNull(f.type_number_kantiner),
//       number_hamel: strOrNull(f.number_hamel),
//       zarib_mahal: numOrNull(f.zarib_mahal),
//       container_type: strOrNull(f.container_type),
//       container_number: strOrNull(f.container_number),
//     }
//   }

//   const saveMutation = useMutation({
//     mutationFn: (f: LineForm) =>
//       editingId == null
//         ? apiSend('/tally-details', 'POST', toPayload(f))
//         : apiSend(`/tally-details/${editingId}`, 'PUT', toPayload(f)),
//     onSuccess: () => {
//       qc.invalidateQueries({ queryKey: ['tally-details', headerId] })
//       setModalOpen(false)
//     },
//   })

//   const deleteMutation = useMutation({
//     mutationFn: (lineId: number) => apiSend(`/tally-details/${lineId}`, 'DELETE'),
//     onSuccess: () => qc.invalidateQueries({ queryKey: ['tally-details', headerId] }),
//   })

//   function openAdd() {
//     setEditingId(null)
//     setLine(EMPTY_LINE)
//     setPicked(null)
//     setModalOpen(true)
//   }

//   // Snapshot the descriptive fields this line has columns for. The storage group
//   // (code_groupe_kala) is handled by CommodityPicker via onGroupChange.
//   function onPickCommodity(c: Commodity | null) {
//     setPicked(c)
//     if (!c) return
//     setLine((l) => ({
//       ...l,
//       description_kala: c.description_fa ?? '',
//       hscode: c.hs_code ?? '',
//     }))
//   }

//   function openEdit(row: DetailRow) {
//     setEditingId(row.id_tali_details)
//     setPicked(null)
//     setLine({
//       id_anbar: row.id_anbar,
//       id_tagh_anbar: row.id_tagh_anbar,
//       code_groupe_kala: String(row.code_groupe_kala ?? ''),
//       description_kala: row.description_kala ?? '',
//       hscode: row.hscode ?? '',
//       type_bastem: row.type_bastem ?? '',
//       number_kala: String(row.number_kala ?? ''),
//       weighte: String(row.weighte ?? ''),
//       weighte_baskol: String(row.weighte_baskol ?? ''),
//       type_number_kantiner: row.type_number_kantiner ?? '',
//       number_hamel: row.number_hamel ?? '',
//       zarib_mahal: row.zarib_mahal != null ? String(row.zarib_mahal) : '',
//       container_type: row.container_type ?? '',
//       container_number: row.container_number ?? '',
//     })
//     setModalOpen(true)
//   }

//   const set = <K extends keyof LineForm>(k: K, v: LineForm[K]) =>
//     setLine((l) => ({ ...l, [k]: v }))

//   // the 4 NOT NULL fields must be filled before save is allowed
//   const canSave =
//     line.code_groupe_kala.trim() !== '' &&
//     line.number_kala.trim() !== '' &&
//     line.weighte.trim() !== '' &&
//     line.weighte_baskol.trim() !== ''

//   return (
//     <div dir="rtl">
//       <Group justify="space-between" mb="md">
//         <Title order={2}>
//           جزئیات تالی {header?.tali_number ? `شماره ${header.tali_number}` : `#${headerId}`}
//         </Title>
//         <Group>
//           <BackButton to="/tally" />
//           <Button variant="light" onClick={() => navigate(`/tally/${headerId}/edit`)}>ویرایش سربرگ</Button>
//           <Button variant="light" color="teal" onClick={async () => {
//             const r = await apiSend<{ id_ghabz: number }>(`/ghabz/from-tally/${headerId}`, 'POST')
//             navigate(`/ghabz/${r.id_ghabz}/edit`)
//           }}>صدور قبض انبار</Button>
//         </Group>
//       </Group>

//       <Paper shadow="xs" p="md">
//         <Group justify="space-between" mb="sm">
//           <Text fw={600}>ردیف‌های کالا</Text>
//           <Button onClick={openAdd}>افزودن ردیف</Button>
//         </Group>
//         <Divider mb="sm" />

//         {isLoading && <Center py="xl"><Loader /></Center>}
//         {isError && <Center py="xl"><Text c="red">خطا در بارگذاری ردیف‌ها.</Text></Center>}

//         {lines && lines.length === 0 && (
//           <Center py="xl">
//             <Text c="dimmed">هنوز ردیفی ثبت نشده است. «افزودن ردیف» را بزنید.</Text>
//           </Center>
//         )}

//         {lines && lines.length > 0 && (
//           <Table striped highlightOnHover withTableBorder>
//             <Table.Thead>
//               <Table.Tr>
//                 <Table.Th>کد گروه کالا</Table.Th>
//                 <Table.Th>شرح کالا</Table.Th>
//                 <Table.Th>Hscode</Table.Th>
//                 <Table.Th>نوع بسته‌بندی</Table.Th>
//                 <Table.Th>تعداد</Table.Th>
//                 <Table.Th>وزن</Table.Th>
//                 <Table.Th>وزن باسکول</Table.Th>
//                 <Table.Th>انبار</Table.Th>
//                 <Table.Th>طاق</Table.Th>
//                 <Table.Th>عملیات</Table.Th>
//               </Table.Tr>
//             </Table.Thead>
//             <Table.Tbody>
//               {lines.map((row) => (
//                 <Table.Tr key={row.id_tali_details}>
//                   <Table.Td>{row.code_groupe_kala}</Table.Td>
//                   <Table.Td>{row.description_kala ?? '—'}</Table.Td>
//                   <Table.Td>{row.hscode ?? '—'}</Table.Td>
//                   <Table.Td>{row.type_bastem ?? '—'}</Table.Td>
//                   <Table.Td>{row.number_kala}</Table.Td>
//                   <Table.Td>{row.weighte}</Table.Td>
//                   <Table.Td>{row.weighte_baskol}</Table.Td>
//                   <Table.Td>{row.anbar_name ?? '—'}</Table.Td>
//                   <Table.Td>{row.tagh_name ?? '—'}</Table.Td>
//                   <Table.Td>
//                     <Group gap="xs">
//                       <Button size="xs" variant="light" onClick={() => openEdit(row)}>ویرایش</Button>
//                       <Button
//                         size="xs" variant="light" color="red"
//                         onClick={() => deleteMutation.mutate(row.id_tali_details)}
//                       >
//                         حذف
//                       </Button>
//                     </Group>
//                   </Table.Td>
//                 </Table.Tr>
//               ))}
//             </Table.Tbody>
//           </Table>
//         )}
//       </Paper>
//       {tallyJunctions.map((cfg) => (
//         <TallyJunctionSection key={cfg.key} config={cfg} tallyId={headerId} />
//       ))}
//       <Modal
//         opened={modalOpen}
//         onClose={() => setModalOpen(false)}
//         title={editingId == null ? 'افزودن ردیف کالا' : 'ویرایش ردیف کالا'}
//         size="lg"
//       >
//         <Stack>
//           <CommodityPicker
//             picked={picked}
//             onPick={onPickCommodity}
//             groupValue={line.code_groupe_kala.trim() === '' ? null : Number(line.code_groupe_kala)}
//             onGroupChange={(v) => set('code_groupe_kala', v == null ? '' : String(v))}
//           />
//           <Divider />
//           <Grid>
//             <Grid.Col span={6}>
//               <TextInput
//                 label="شرح کالا"
//                 value={line.description_kala}
//                 onChange={(e) => set('description_kala', e.currentTarget.value)}
//               />
//             </Grid.Col>
//             <Grid.Col span={6}>
//               <TextInput
//                 label="Hscode"
//                 value={line.hscode}
//                 onChange={(e) => set('hscode', e.currentTarget.value)}
//               />
//             </Grid.Col>
//             <Grid.Col span={6}>
//               <TextInput
//                 label="نوع بسته‌بندی"
//                 value={line.type_bastem}
//                 onChange={(e) => set('type_bastem', e.currentTarget.value)}
//               />
//             </Grid.Col>
//             <Grid.Col span={4}>
//               <TextInput
//                 label="تعداد" required inputMode="numeric"
//                 value={line.number_kala}
//                 onChange={(e) => set('number_kala', e.currentTarget.value)}
//               />
//             </Grid.Col>
//             <Grid.Col span={4}>
//               <TextInput
//                 label="وزن" required inputMode="numeric"
//                 value={line.weighte}
//                 onChange={(e) => set('weighte', e.currentTarget.value)}
//               />
//             </Grid.Col>
//             <Grid.Col span={4}>
//               <TextInput
//                 label="وزن باسکول" required inputMode="numeric"
//                 value={line.weighte_baskol}
//                 onChange={(e) => set('weighte_baskol', e.currentTarget.value)}
//               />
//             </Grid.Col>
//             <Grid.Col span={6}>
//               <RefSelect
//                 label="انبار"
//                 path="/anbar"
//                 valueKey="id_anbar"
//                 labelKey="name_anbar"
//                 value={line.id_anbar}
//                 onChange={(v) => set('id_anbar', v)}
//               />
//             </Grid.Col>
//             <Grid.Col span={6}>
//               <RefSelect
//                 label="طاق"
//                 path="/tagh"
//                 valueKey="id_tagh"
//                 labelKey="name_tagh"
//                 value={line.id_tagh_anbar}
//                 onChange={(v) => set('id_tagh_anbar', v)}
//               />
//             </Grid.Col>
//             <Grid.Col span={12}>
//               <PlateInput
//                 label="شماره حامل"
//                 value={line.number_hamel}
//                 onChange={(v) => set('number_hamel', v)}
//               />
//             </Grid.Col>
//             <ContainerFields
//               type={line.container_type}
//               number={line.container_number}
//               onTypeChange={(v) => set('container_type', v)}
//               onNumberChange={(v) => set('container_number', v)}
//             />
//             <Grid.Col span={6}>
//               <TextInput
//                 label="ضریب محل"
//                 value={line.zarib_mahal}
//                 onChange={(e) => set('zarib_mahal', e.currentTarget.value)}
//               />
//             </Grid.Col>
//           </Grid>

//           <Group justify="flex-start" mt="md">
//             <Button
//               onClick={() => saveMutation.mutate(line)}
//               loading={saveMutation.isPending}
//               disabled={!canSave}
//             >
//               ذخیره
//             </Button>
//             <Button variant="subtle" onClick={() => setModalOpen(false)}>لغو</Button>
//           </Group>
//         </Stack>
//       </Modal>
//     </div>
//   )
// }

import { useEffect, useState } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { BackButton } from '../components/BackButton'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import {
  Title, Button, Group, Table, Paper, Loader, Center, Text, Stack, Divider,
  Modal, TextInput, Select, Grid, ActionIcon, Tooltip,
} from '@mantine/core'
import { IconEdit, IconTrash } from '../components/icons'
import { apiGet, apiSend } from '../api/client'
import { RefSelect } from '../components/RefSelect'
import { CommodityPicker, type Commodity } from '../components/CommodityPicker'
import { PlateInput } from '../components/PlateInput'
import { ContainerFields } from '../components/ContainerFields'
// import { TallyDiamoundSection } from '../components/TallyDiamoundSection'
import { TallyJunctionSection } from '../components/TallyJunctionSection'
import { tallyJunctions } from '../components/junctions'
import { TallyNumber } from '../components/TallyNumber'
/**
 * TallyDetailPage — one tally's detail view at /tally/:tallyNumber.
 * Top: header actions (edit button returns to the form).
 * Below: the goods-lines grid (جزئیات تالی) — add / edit / delete rows, each line
 * scoped to this tally via id_headers_tali.
 */

type DetailRow = {
  id_tali_details: number
  id_headers_tali: number
  id_anbar: number | null
  anbar_name: string | null
  id_tagh_anbar: number | null
  tagh_name: string | null
  number_ghabze_anbar: number | null
  code_groupe_kala: number
  description_kala: string | null
  hscode: string | null
  type_bastem: string | null
  number_kala: number
  weighte: number
  type_number_kantiner: string | null
  number_ghabze_bskol: number | null
  weighte_baskol: number
  number_hamel: string | null
  zarib_mahal: string | null
  container_type: string | null
  container_number: string | null
}

type LineForm = {
  id_anbar: number | null
  id_tagh_anbar: number | null
  code_groupe_kala: string
  description_kala: string
  hscode: string
  type_bastem: string
  number_kala: string
  weighte: string
  weighte_baskol: string
  type_number_kantiner: string
  number_hamel: string
  zarib_mahal: string
  container_type: string
  container_number: string
}

const EMPTY_LINE: LineForm = {
  id_anbar: null, id_tagh_anbar: null, code_groupe_kala: '', description_kala: '',
  hscode: '', type_bastem: '', number_kala: '', weighte: '', weighte_baskol: '',
  type_number_kantiner: '', number_hamel: '', zarib_mahal: '',
  container_type: '', container_number: '',
}

// Persian/Arabic digits -> Latin, so numeric fields accept ۱۲۳
function normalizeDigits(s: string): string {
  return s
    .replace(/[\u06F0-\u06F9]/g, (d) => String(d.charCodeAt(0) - 0x06f0))
    .replace(/[\u0660-\u0669]/g, (d) => String(d.charCodeAt(0) - 0x0660))
}

export function TallyDetailPage() {
  const { tallyNumber = '' } = useParams<{ tallyNumber: string }>()
  const isLegacyId = /^\d+$/.test(tallyNumber)
  const navigate = useNavigate()
  const qc = useQueryClient()

  const [modalOpen, setModalOpen] = useState(false)
  const [editingId, setEditingId] = useState<number | null>(null) // null = adding
  const [line, setLine] = useState<LineForm>(EMPTY_LINE)
  // the commodity picked from the catalog for this line (drives autofill + info display)
  const [picked, setPicked] = useState<Commodity | null>(null)

  // The public URL uses TALI_NUMBER. The database ID is resolved once and then
  // retained only for relational API calls below this page.
  const {
    data: header,
    isLoading: isHeaderLoading,
    isError: isHeaderError,
  } = useQuery({
    queryKey: ['tally-header', tallyNumber],
    queryFn: () => apiGet<Record<string, any>>(
      isLegacyId
        ? `/tally-header/${tallyNumber}`
        : `/tally-header/by-number/${encodeURIComponent(tallyNumber)}`
    ),
  })
  const headerId = header?.id_tali == null ? undefined : Number(header.id_tali)

  useEffect(() => {
    if (isLegacyId && header?.tali_number) {
      navigate(`/tally/${encodeURIComponent(String(header.tali_number))}`, { replace: true })
    }
  }, [header?.tali_number, isLegacyId, navigate])

  const {
    data: lines,
    isLoading: areLinesLoading,
    isError: areLinesError,
  } = useQuery({
    queryKey: ['tally-details', headerId],
    queryFn: () => apiGet<DetailRow[]>(`/tally/${headerId}/details`),
    enabled: headerId != null,
  })
  const isLoading = isHeaderLoading || areLinesLoading
  const isError = isHeaderError || areLinesError

  function toPayload(f: LineForm) {
    if (headerId == null) throw new Error('شناسه داخلی تالی بارگذاری نشده است.')
    const numOrNull = (v: string) => (v.trim() === '' ? null : Number(normalizeDigits(v)))
    const strOrNull = (v: string) => (v.trim() === '' ? null : v)
    return {
      id_headers_tali: headerId,
      id_anbar: f.id_anbar,
      id_tagh_anbar: f.id_tagh_anbar,
      code_groupe_kala: Number(normalizeDigits(f.code_groupe_kala)),
      description_kala: strOrNull(f.description_kala),
      hscode: strOrNull(f.hscode),
      type_bastem: strOrNull(f.type_bastem),
      number_kala: Number(normalizeDigits(f.number_kala)),
      weighte: Number(normalizeDigits(f.weighte)),
      weighte_baskol: Number(normalizeDigits(f.weighte_baskol)),
      type_number_kantiner: strOrNull(f.type_number_kantiner),
      number_hamel: strOrNull(f.number_hamel),
      zarib_mahal: strOrNull(f.zarib_mahal),
      container_type: strOrNull(f.container_type),
      container_number: strOrNull(f.container_number),
    }
  }

  const saveMutation = useMutation({
    mutationFn: (f: LineForm) =>
      editingId == null
        ? apiSend('/tally-details', 'POST', toPayload(f))
        : apiSend(`/tally-details/${editingId}`, 'PUT', toPayload(f)),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['tally-details', headerId] })
      setModalOpen(false)
    },
  })

  const deleteMutation = useMutation({
    mutationFn: (lineId: number) => apiSend(`/tally-details/${lineId}`, 'DELETE'),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['tally-details', headerId] }),
    onError: (e) => alert(`حذف ناموفق بود: ${(e as Error).message}`),
  })

  function openAdd() {
    setEditingId(null)
    setLine(EMPTY_LINE)
    setPicked(null)
    setModalOpen(true)
  }

  // Snapshot the descriptive fields this line has columns for. The storage group
  // (code_groupe_kala) is handled by CommodityPicker via onGroupChange.
  function onPickCommodity(c: Commodity | null) {
    setPicked(c)
    if (!c) return
    setLine((l) => ({
      ...l,
      description_kala: c.description_fa ?? '',
      hscode: c.hs_code ?? '',
    }))
  }

  function openEdit(row: DetailRow) {
    setEditingId(row.id_tali_details)
    setPicked(null)
    setLine({
      id_anbar: row.id_anbar,
      id_tagh_anbar: row.id_tagh_anbar,
      code_groupe_kala: String(row.code_groupe_kala ?? ''),
      description_kala: row.description_kala ?? '',
      hscode: row.hscode ?? '',
      type_bastem: row.type_bastem ?? '',
      number_kala: String(row.number_kala ?? ''),
      weighte: String(row.weighte ?? ''),
      weighte_baskol: String(row.weighte_baskol ?? ''),
      type_number_kantiner: row.type_number_kantiner ?? '',
      number_hamel: row.number_hamel ?? '',
      zarib_mahal: row.zarib_mahal != null ? String(row.zarib_mahal) : '',
      container_type: row.container_type ?? '',
      container_number: row.container_number ?? '',
    })
    setModalOpen(true)
  }

  const set = <K extends keyof LineForm>(k: K, v: LineForm[K]) =>
    setLine((l) => ({ ...l, [k]: v }))

  // the 4 NOT NULL fields must be filled before save is allowed
  const canSave =
    line.code_groupe_kala.trim() !== '' &&
    line.number_kala.trim() !== '' &&
    line.weighte.trim() !== '' &&
    line.weighte_baskol.trim() !== ''

  return (
    <div dir="rtl">
      <Group justify="space-between" mb="md">
        <Title order={2}>
          جزئیات تالی شماره{' '}
          <TallyNumber value={header?.tali_number ?? tallyNumber} />
        </Title>
        <Group>
          
          <Button variant="light" onClick={() => navigate(`/tally/${encodeURIComponent(tallyNumber)}/edit`)}>ویرایش سربرگ</Button>
          <Button variant="light" color="teal" onClick={async () => {
            if (headerId == null) return
            const r = await apiSend<{ id_ghabz: number }>(`/ghabz/from-tally/${headerId}`, 'POST')
            navigate(`/ghabz/${r.id_ghabz}/edit`)
          }} disabled={headerId == null}>صدور قبض انبار</Button><BackButton to="/tally" />
        </Group>
      </Group>

      <Paper shadow="xs" p="md">
        <Group justify="space-between" mb="sm">
          <Text fw={600}>ردیف‌های کالا</Text>
          <Button onClick={openAdd} disabled={headerId == null}>افزودن ردیف</Button>
        </Group>
        <Divider mb="sm" />

        {isLoading && <Center py="xl"><Loader /></Center>}
        {isError && <Center py="xl"><Text c="red">خطا در بارگذاری ردیف‌ها.</Text></Center>}

        {lines && lines.length === 0 && (
          <Center py="xl">
            <Text c="dimmed">هنوز ردیفی ثبت نشده است. «افزودن ردیف» را بزنید.</Text>
          </Center>
        )}

        {lines && lines.length > 0 && (
          <Table.ScrollContainer minWidth={900}>
          <Table striped highlightOnHover stickyHeader verticalSpacing="sm" horizontalSpacing="md" withRowBorders>
            <Table.Thead style={{ background: 'var(--mantine-color-gray-light)' }}>
              <Table.Tr>
                <Table.Th>کد گروه کالا</Table.Th>
                <Table.Th>شرح کالا</Table.Th>
                <Table.Th>Hscode</Table.Th>
                <Table.Th>نوع بسته‌بندی</Table.Th>
                <Table.Th>تعداد</Table.Th>
                <Table.Th>وزن</Table.Th>
                <Table.Th>وزن باسکول</Table.Th>
                <Table.Th>انبار</Table.Th>
                <Table.Th>طاق</Table.Th>
                <Table.Th style={{ textAlign: 'center' }}>عملیات</Table.Th>
              </Table.Tr>
            </Table.Thead>
            <Table.Tbody>
              {lines.map((row) => (
                <Table.Tr key={row.id_tali_details}>
                  <Table.Td>{row.code_groupe_kala}</Table.Td>
                  <Table.Td>{row.description_kala ?? '—'}</Table.Td>
                  <Table.Td>{row.hscode ?? '—'}</Table.Td>
                  <Table.Td>{row.type_bastem ?? '—'}</Table.Td>
                  <Table.Td>{row.number_kala}</Table.Td>
                  <Table.Td>{row.weighte}</Table.Td>
                  <Table.Td>{row.weighte_baskol}</Table.Td>
                  <Table.Td>{row.anbar_name ?? '—'}</Table.Td>
                  <Table.Td>{row.tagh_name ?? '—'}</Table.Td>
                  <Table.Td style={{ textAlign: 'center' }}>
                    <Group gap={4} justify="center" wrap="nowrap">
                      <Tooltip label="ویرایش" withArrow>
                        <ActionIcon variant="subtle" color="blue" radius="md" aria-label="ویرایش"
                          onClick={() => openEdit(row)}>
                          <IconEdit size={18} />
                        </ActionIcon>
                      </Tooltip>
                      <Tooltip label="حذف" withArrow>
                        <ActionIcon variant="subtle" color="red" radius="md" aria-label="حذف"
                          onClick={() => confirm('حذف این ردیف؟') && deleteMutation.mutate(row.id_tali_details)}>
                          <IconTrash size={18} />
                        </ActionIcon>
                      </Tooltip>
                    </Group>
                  </Table.Td>
                </Table.Tr>
              ))}
            </Table.Tbody>
          </Table>
          </Table.ScrollContainer>
        )}
      </Paper>
      {headerId != null && tallyJunctions.map((cfg) => (
        <TallyJunctionSection key={cfg.key} config={cfg} tallyId={headerId} />
      ))}
      <Modal
        opened={modalOpen}
        onClose={() => setModalOpen(false)}
        title={editingId == null ? 'افزودن ردیف کالا' : 'ویرایش ردیف کالا'}
        size="lg"
      >
        <Stack>
          <CommodityPicker
            picked={picked}
            onPick={onPickCommodity}
            groupValue={line.code_groupe_kala.trim() === '' ? null : Number(line.code_groupe_kala)}
            onGroupChange={(v) => set('code_groupe_kala', v == null ? '' : String(v))}
          />
          <Divider />
          <Grid>
            <Grid.Col span={6}>
              <TextInput
                label="شرح کالا"
                value={line.description_kala}
                onChange={(e) => set('description_kala', e.currentTarget.value)}
              />
            </Grid.Col>
            <Grid.Col span={6}>
              <TextInput
                label="Hscode"
                value={line.hscode}
                onChange={(e) => set('hscode', e.currentTarget.value)}
              />
            </Grid.Col>
            <Grid.Col span={6}>
              <Select
                label="نوع بسته‌بندی"
                placeholder="انتخاب کنید"
                data={['کیسه‌ای', 'نگله', 'پالت']}
                value={line.type_bastem || null}
                onChange={(v) => set('type_bastem', v ?? '')}
                clearable
              />
            </Grid.Col>
            <Grid.Col span={4}>
              <TextInput
                label="تعداد" required inputMode="numeric"
                value={line.number_kala}
                onChange={(e) => set('number_kala', e.currentTarget.value)}
              />
            </Grid.Col>
            <Grid.Col span={4}>
              <TextInput
                label="وزن" required inputMode="numeric"
                value={line.weighte}
                onChange={(e) => set('weighte', e.currentTarget.value)}
              />
            </Grid.Col>
            <Grid.Col span={4}>
              <TextInput
                label="وزن باسکول" required inputMode="numeric"
                value={line.weighte_baskol}
                onChange={(e) => set('weighte_baskol', e.currentTarget.value)}
              />
            </Grid.Col>
            <Grid.Col span={6}>
              <RefSelect
                label="انبار"
                path="/anbar"
                valueKey="id_anbar"
                labelKey="name_anbar"
                value={line.id_anbar}
                onChange={(v) => set('id_anbar', v)}
              />
            </Grid.Col>
            <Grid.Col span={6}>
              <RefSelect
                label="طاق"
                path="/tagh"
                valueKey="id_tagh"
                labelKey="name_tagh"
                value={line.id_tagh_anbar}
                onChange={(v) => set('id_tagh_anbar', v)}
              />
            </Grid.Col>
            <Grid.Col span={12}>
              <PlateInput
                label="شماره حامل"
                value={line.number_hamel}
                onChange={(v) => set('number_hamel', v)}
              />
            </Grid.Col>
            <ContainerFields
              type={line.container_type}
              number={line.container_number}
              onTypeChange={(v) => set('container_type', v)}
              onNumberChange={(v) => set('container_number', v)}
            />
            <Grid.Col span={6}>
              <Select
                label="ضریب محل"
                placeholder="انتخاب کنید"
                data={['انبارداری مسقف', 'انبارداری تانگارد', 'انبارداری بارانداز', 'انبارداری محوطه']}
                value={line.zarib_mahal || null}
                onChange={(v) => set('zarib_mahal', v ?? '')}
                clearable
              />
            </Grid.Col>
          </Grid>

          <Group justify="flex-start" mt="md">
            <Button
              onClick={() => saveMutation.mutate(line)}
              loading={saveMutation.isPending}
              disabled={!canSave}
            >
              ذخیره
            </Button>
            <Button variant="subtle" onClick={() => setModalOpen(false)}>لغو</Button>
          </Group>
        </Stack>
      </Modal>
    </div>
  )
}
