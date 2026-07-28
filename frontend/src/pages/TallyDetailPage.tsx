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
//                 data={['انبارداری مسقف', 'انبارداری هانگار', 'انبارداری بارانداز', 'انبارداری محوطه']}
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
import { toJalaali } from 'jalaali-js'
import {
  Title, Button, Group, Table, Paper, Loader, Center, Text, Stack,
  Modal, TextInput, Select, Grid, ActionIcon, Tooltip,
} from '@mantine/core'
import {
  Bookmark,
  CalendarDays,
  ClipboardList,
  FileText,
  MapPin,
  PackageOpen,
  PencilLine,
  Plus,
  ReceiptText,
  Scale,
  ShieldCheck,
  Truck,
  UserRound,
} from 'lucide-react'
import { IconEdit, IconPrint, IconTrash } from '../components/icons'
import { apiGet, apiSend } from '../api/client'
import { RefSelect } from '../components/RefSelect'
import { CommodityPicker, type Commodity } from '../components/CommodityPicker'
import { PlateInput } from '../components/PlateInput'
import { ContainerFields } from '../components/ContainerFields'
// import { TallyDiamoundSection } from '../components/TallyDiamoundSection'
import { TallyJunctionSection } from '../components/TallyJunctionSection'
import { tallyJunctions } from '../components/junctions'
import { TallyNumber } from '../components/TallyNumber'
import './TallyDetailPage.css'
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
  number_pallet: number | null
  value_kala: number | string | null
  weighte: number
  type_number_kantiner: string | null
  number_ghabze_bskol: number | null
  weighte_baskol: number
  number_hamel: string | null
  zarib_mahal: string | null
  container_type: string | null
  container_number: string | null
}

type TallySummaryData = {
  number_karaneh: string | null
  radef_marze: number | null
  date_enter_marze: string | null
  number_bimeh: string | null
  company_bimeh: string | null
  owner_name: string | null
  country_name: string | null
  company_name: string | null
  representative_name: string | null
}

type LineForm = {
  id_anbar: number | null
  id_tagh_anbar: number | null
  code_groupe_kala: string
  description_kala: string
  hscode: string
  type_bastem: string
  number_kala: string
  number_pallet: string
  value_kala: string
  weighte: string
  number_ghabze_bskol: string
  weighte_baskol: string
  type_number_kantiner: string
  number_hamel: string
  zarib_mahal: string
  container_type: string
  container_number: string
}

const EMPTY_LINE: LineForm = {
  id_anbar: null, id_tagh_anbar: null, code_groupe_kala: '', description_kala: '',
  hscode: '', type_bastem: '', number_kala: '', number_pallet: '', value_kala: '', weighte: '',
  number_ghabze_bskol: '', weighte_baskol: '',
  type_number_kantiner: '', number_hamel: '', zarib_mahal: '',
  container_type: '', container_number: '',
}

// Persian/Arabic digits -> Latin, so numeric fields accept ۱۲۳
function normalizeDigits(s: string): string {
  return s
    .replace(/[\u06F0-\u06F9]/g, (d) => String(d.charCodeAt(0) - 0x06f0))
    .replace(/[\u0660-\u0669]/g, (d) => String(d.charCodeAt(0) - 0x0660))
}

function normalizeIntegerInput(s: string): string {
  return normalizeDigits(s).replace(/\D/g, '')
}

function normalizeDecimalInput(s: string): string {
  const normalized = normalizeDigits(s)
    .replace(/[,\u066C\s]/g, '')
    .replace(/\u066B/g, '.')
    .replace(/[^\d.]/g, '')
  const [whole, ...fractionParts] = normalized.split('.')
  return fractionParts.length === 0 ? whole : `${whole}.${fractionParts.join('')}`
}

function formatGoodsValue(value: number | string | null): string {
  if (value == null || String(value).trim() === '') return '—'
  const amount = Number(value)
  if (!Number.isFinite(amount)) return String(value)
  return amount.toLocaleString('en-US', { maximumFractionDigits: 2 })
}

function firstPresent(...values: unknown[]): unknown {
  return values.find((value) => value != null && String(value).trim() !== '') ?? null
}

function displayValue(value: unknown): string {
  return value == null || String(value).trim() === '' ? '—' : String(value)
}

function formatJalaliDate(value: unknown): string {
  if (value == null || String(value).trim() === '') return '—'
  const raw = String(value)
  const [gy, gm, gd] = raw.slice(0, 10).split('-').map(Number)
  if (!gy || !gm || !gd) return raw

  try {
    const { jy, jm, jd } = toJalaali(gy, gm, gd)
    return `${jy}/${String(jm).padStart(2, '0')}/${String(jd).padStart(2, '0')}`
  } catch {
    return raw
  }
}

function SummaryLine({
  icon,
  label,
  value,
  tone,
  ltr = false,
}: {
  icon: React.ReactNode
  label: string
  value: unknown
  tone: 'blue' | 'violet' | 'green'
  ltr?: boolean
}) {
  return (
    <div className="tally-detail-summary-line">
      <span
        className={`tally-detail-summary-icon tally-detail-summary-icon-${tone}`}
        aria-hidden
      >
        {icon}
      </span>
      <div className="tally-detail-summary-content">
        <span className="tally-detail-summary-label">{label}</span>
        <strong className="tally-detail-summary-value">
          <bdi dir={ltr ? 'ltr' : 'auto'}>{displayValue(value)}</bdi>
        </strong>
      </div>
    </div>
  )
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

  const { data: summary } = useQuery({
    queryKey: ['tally-summary', headerId],
    queryFn: () => apiGet<TallySummaryData>(`/tally/${headerId}/print`),
    enabled: headerId != null,
  })

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
    const numOrNull = (v: string) => {
      const normalized = normalizeIntegerInput(v)
      return normalized === '' ? null : Number(normalized)
    }
    const decimalOrNull = (v: string) => {
      const normalized = normalizeDecimalInput(v)
      return normalized === '' ? null : normalized
    }
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
      number_pallet: numOrNull(f.number_pallet),
      value_kala: decimalOrNull(f.value_kala),
      weighte: Number(normalizeDigits(f.weighte)),
      number_ghabze_bskol: numOrNull(f.number_ghabze_bskol),
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
    onError: () => {
      qc.invalidateQueries({ queryKey: ['tally-details', headerId] })
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
      number_pallet: String(row.number_pallet ?? ''),
      value_kala: String(row.value_kala ?? ''),
      weighte: String(row.weighte ?? ''),
      number_ghabze_bskol: String(row.number_ghabze_bskol ?? ''),
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
    line.number_ghabze_bskol.trim() !== '' &&
    line.weighte_baskol.trim() !== ''

  return (
    <div dir="rtl" className="tally-detail-page">
      <Paper className="tally-detail-hero" radius="xl">
        <div className="tally-detail-title-block">
          <span className="tally-detail-title-icon" aria-hidden>
            <ClipboardList size={29} strokeWidth={1.8} />
          </span>
          <div>
            <Text className="tally-detail-eyebrow">مدیریت اطلاعات تالی</Text>
            <Title order={2} className="tally-detail-title">
              جزئیات تالی شماره{' '}
              <TallyNumber value={header?.tali_number ?? tallyNumber} />
            </Title>
            <Text className="tally-detail-subtitle">
              ردیف‌های کالا و تمام خدمات مرتبط با این تالی را از این صفحه مدیریت کنید.
            </Text>
          </div>
        </div>

        <Group className="tally-detail-actions" gap="sm">
          <Button
            variant="filled"
            leftSection={<IconPrint size={18} />}
            onClick={() => window.open(
              `/tally/${encodeURIComponent(String(header?.tali_number ?? tallyNumber))}/print`,
              '_blank',
              'noopener,noreferrer',
            )}
            disabled={headerId == null}
          >
            چاپ تالی
          </Button>
          <Button
            variant="light"
            leftSection={<PencilLine size={17} />}
            onClick={() => navigate(`/tally/${encodeURIComponent(tallyNumber)}/edit`)}
          >
            ویرایش سربرگ
          </Button>
          <Button
            variant="light"
            color="teal"
            leftSection={<ReceiptText size={17} />}
            onClick={async () => {
              if (headerId == null) return
              const r = await apiSend<{ id_ghabz: number }>(`/ghabz/from-tally/${headerId}`, 'POST')
              navigate(`/ghabz/${r.id_ghabz}/edit`)
            }}
            disabled={headerId == null}
          >
            صدور قبض انبار
          </Button>
          <BackButton to="/tally" />
        </Group>
      </Paper>

      <section className="tally-detail-summary-grid" aria-label="خلاصه اطلاعات تالی">
        <Paper className="tally-detail-summary-card" radius="lg">
          <SummaryLine
            icon={<FileText size={20} strokeWidth={1.8} />}
            label="شماره کارنه / ترانزیت"
            value={firstPresent(summary?.number_karaneh, header?.number_karaneh)}
            tone="blue"
            ltr
          />
          <SummaryLine
            icon={<ShieldCheck size={20} strokeWidth={1.8} />}
            label="شماره بیمه‌نامه / بیمه‌گر"
            value={[
              firstPresent(summary?.number_bimeh, header?.number_bimeh),
              firstPresent(summary?.company_bimeh, header?.company_bimeh),
            ].filter((value) => value != null && String(value).trim() !== '').join(' / ')}
            tone="blue"
            ltr
          />
        </Paper>

        <Paper className="tally-detail-summary-card" radius="lg">
          <SummaryLine
            icon={<UserRound size={20} strokeWidth={1.8} />}
            label="صاحب کالا (الزاماً به اظهار شرکت حمل)"
            value={summary?.owner_name}
            tone="violet"
          />
          <SummaryLine
            icon={<MapPin size={20} strokeWidth={1.8} />}
            label="مبدأ حمل"
            value={summary?.country_name}
            tone="violet"
          />
        </Paper>

        <Paper className="tally-detail-summary-card" radius="lg">
          <SummaryLine
            icon={<Truck size={20} strokeWidth={1.8} />}
            label="نام شرکت حمل"
            value={summary?.company_name}
            tone="green"
          />
          <SummaryLine
            icon={<UserRound size={20} strokeWidth={1.8} />}
            label="نماینده شرکت حمل"
            value={summary?.representative_name}
            tone="green"
          />
        </Paper>

        <Paper className="tally-detail-summary-card" radius="lg">
          <SummaryLine
            icon={<Bookmark size={20} strokeWidth={1.8} />}
            label="ردیف مرزی"
            value={firstPresent(summary?.radef_marze, header?.radef_marze)}
            tone="blue"
            ltr
          />
          <SummaryLine
            icon={<CalendarDays size={20} strokeWidth={1.8} />}
            label="تاریخ ورود به مرز"
            value={formatJalaliDate(firstPresent(summary?.date_enter_marze, header?.date_enter_marze))}
            tone="blue"
            ltr
          />
        </Paper>
      </section>

      <Paper className="tally-detail-section tally-detail-goods-section" radius="xl">
        <div className="tally-detail-section-header">
          <div className="tally-detail-section-heading">
            <span className="tally-detail-section-icon" aria-hidden>
              <PackageOpen size={23} strokeWidth={1.8} />
            </span>
            <div>
              <Title order={3}>ردیف‌های کالا</Title>
              <Text>اطلاعات کالا، باسکول، محل نگهداری و حامل</Text>
            </div>
          </div>
          <Button
            className="tally-detail-add-button"
            leftSection={<Plus size={18} />}
            onClick={openAdd}
            disabled={headerId == null}
          >
            افزودن ردیف
          </Button>
        </div>
        <div className="tally-detail-section-rule" />

        {isLoading && (
          <Center className="tally-detail-state">
            <Loader size="sm" />
            <Text>در حال بارگذاری ردیف‌ها...</Text>
          </Center>
        )}
        {isError && (
          <Center className="tally-detail-state tally-detail-state-error">
            <Text>خطا در بارگذاری ردیف‌ها.</Text>
          </Center>
        )}

        {lines && lines.length === 0 && (
          <Center className="tally-detail-empty-state">
            <PackageOpen size={28} strokeWidth={1.6} aria-hidden />
            <Text fw={700}>هنوز ردیف کالایی ثبت نشده است.</Text>
            <Text size="sm">برای شروع، گزینه «افزودن ردیف» را انتخاب کنید.</Text>
          </Center>
        )}

        {lines && lines.length > 0 && (
          <div className="tally-detail-table-shell">
            <Table.ScrollContainer minWidth={1160}>
              <Table
                className="tally-detail-table"
                highlightOnHover
                verticalSpacing="md"
                horizontalSpacing="md"
                withRowBorders
              >
                <Table.Thead>
                  <Table.Tr>
                    <Table.Th>شرح کالا</Table.Th>
                    <Table.Th>HS Code</Table.Th>
                    <Table.Th>نوع بسته‌بندی</Table.Th>
                    <Table.Th>تعداد</Table.Th>
                    <Table.Th>تعداد پالت</Table.Th>
                    <Table.Th>ارزش کالا</Table.Th>
                    <Table.Th>وزن</Table.Th>
                    <Table.Th>شماره قبض باسکول</Table.Th>
                    <Table.Th>وزن باسکول</Table.Th>
                    <Table.Th>انبار</Table.Th>
                    <Table.Th>طاق</Table.Th>
                    <Table.Th className="tally-detail-actions-cell">عملیات</Table.Th>
                  </Table.Tr>
                </Table.Thead>
                <Table.Tbody>
                  {lines.map((row) => (
                    <Table.Tr key={row.id_tali_details}>
                      <Table.Td className="tally-detail-primary-cell">{row.description_kala ?? '—'}</Table.Td>
                      <Table.Td>{row.hscode ?? '—'}</Table.Td>
                      <Table.Td>{row.type_bastem ?? '—'}</Table.Td>
                      <Table.Td>{row.number_kala}</Table.Td>
                      <Table.Td>{row.number_pallet ?? '—'}</Table.Td>
                      <Table.Td>{formatGoodsValue(row.value_kala)}</Table.Td>
                      <Table.Td>{row.weighte}</Table.Td>
                      <Table.Td>{row.number_ghabze_bskol ?? '—'}</Table.Td>
                      <Table.Td>{row.weighte_baskol}</Table.Td>
                      <Table.Td>{row.anbar_name ?? '—'}</Table.Td>
                      <Table.Td>{row.tagh_name ?? '—'}</Table.Td>
                      <Table.Td className="tally-detail-actions-cell">
                        <Group gap={4} justify="center" wrap="nowrap">
                          <Tooltip label="ویرایش" withArrow>
                            <ActionIcon
                              className="tally-detail-row-action"
                              variant="light"
                              color="blue"
                              radius="md"
                              aria-label="ویرایش"
                              onClick={() => openEdit(row)}
                            >
                              <IconEdit size={18} />
                            </ActionIcon>
                          </Tooltip>
                          <Tooltip label="حذف" withArrow>
                            <ActionIcon
                              className="tally-detail-row-action"
                              variant="light"
                              color="red"
                              radius="md"
                              aria-label="حذف"
                              onClick={() => confirm('حذف این ردیف؟') && deleteMutation.mutate(row.id_tali_details)}
                            >
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
          </div>
        )}
      </Paper>

      <div className="tally-detail-junctions">
        {headerId != null && tallyJunctions.map((cfg) => (
          <TallyJunctionSection key={cfg.key} config={cfg} tallyId={headerId} />
        ))}
      </div>

      <Modal
        opened={modalOpen}
        onClose={() => setModalOpen(false)}
        title={editingId == null ? 'افزودن ردیف کالا' : 'ویرایش ردیف کالا'}
        size="xl"
        radius="lg"
        overlayProps={{ backgroundOpacity: 0.45, blur: 2 }}
        classNames={{
          content: 'tally-detail-modal',
          header: 'tally-detail-modal-header',
          title: 'tally-detail-modal-title',
          body: 'tally-detail-modal-body',
        }}
      >
        <Stack
          component="form"
          className="tally-detail-modal-form"
          gap={0}
          onSubmit={(event) => {
            event.preventDefault()
            if (canSave) saveMutation.mutate(line)
          }}
        >
          <div className="tally-detail-modal-scroll">
            <Stack gap="md">
              <Paper className="tally-detail-form-card" radius="lg">
                <div className="tally-detail-form-card-heading">
                  <PackageOpen size={20} strokeWidth={1.8} aria-hidden />
                  <Text fw={700}>اطلاعات کالا</Text>
                </div>
                <Stack gap="md">
                  <CommodityPicker
                    picked={picked}
                    onPick={onPickCommodity}
                    groupValue={line.code_groupe_kala.trim() === '' ? null : Number(line.code_groupe_kala)}
                    onGroupChange={(v) => set('code_groupe_kala', v == null ? '' : String(v))}
                  />
                  <Grid>
                    <Grid.Col span={{ base: 12, sm: 6 }}>
                      <TextInput
                        label="شرح کالا"
                        value={line.description_kala}
                        onChange={(e) => set('description_kala', e.currentTarget.value)}
                      />
                    </Grid.Col>
                    <Grid.Col span={{ base: 12, sm: 6 }}>
                      <TextInput
                        label="Hscode"
                        value={line.hscode}
                        onChange={(e) => set('hscode', e.currentTarget.value)}
                      />
                    </Grid.Col>
                    <Grid.Col span={{ base: 12, sm: 4 }}>
                      <Select
                        label="نوع بسته‌بندی"
                        placeholder="انتخاب کنید"
                        data={['کیسه‌ای', 'نگله', 'پالت']}
                        value={line.type_bastem || null}
                        onChange={(v) => set('type_bastem', v ?? '')}
                        clearable
                      />
                    </Grid.Col>
                    <Grid.Col span={{ base: 12, sm: 4 }}>
                      <TextInput
                        label="تعداد" required inputMode="numeric"
                        value={line.number_kala}
                        onChange={(e) => set('number_kala', e.currentTarget.value)}
                      />
                    </Grid.Col>
                    <Grid.Col span={{ base: 12, sm: 4 }}>
                      <TextInput
                        label="وزن" required inputMode="decimal"
                        value={line.weighte}
                        onChange={(e) => set('weighte', e.currentTarget.value)}
                      />
                    </Grid.Col>
                    <Grid.Col span={{ base: 12, sm: 6 }}>
                      <TextInput
                        label="تعداد پالت"
                        inputMode="numeric"
                        value={line.number_pallet}
                        onChange={(e) => set('number_pallet', normalizeIntegerInput(e.currentTarget.value))}
                      />
                    </Grid.Col>
                    <Grid.Col span={{ base: 12, sm: 6 }}>
                      <TextInput
                        label="ارزش کالا"
                        inputMode="decimal"
                        value={line.value_kala}
                        onChange={(e) => set('value_kala', normalizeDecimalInput(e.currentTarget.value))}
                      />
                    </Grid.Col>
                  </Grid>
                </Stack>
              </Paper>

              <Paper className="tally-detail-form-card" radius="lg">
                <div className="tally-detail-form-card-heading">
                  <Scale size={20} strokeWidth={1.8} aria-hidden />
                  <Text fw={700}>اطلاعات باسکول و محل نگهداری</Text>
                </div>
                <Grid>
                  <Grid.Col span={{ base: 12, sm: 6 }}>
                    <TextInput
                      label="شماره قبض باسکول"
                      required
                      inputMode="numeric"
                      value={line.number_ghabze_bskol}
                      onChange={(e) => set('number_ghabze_bskol', normalizeIntegerInput(e.currentTarget.value))}
                      // description="این شماره همراه ردیف ذخیره و در چاپ تالی نمایش داده می‌شود."
                    />
                  </Grid.Col>
                  <Grid.Col span={{ base: 12, sm: 6 }}>
                    <TextInput
                      label="وزن باسکول" required inputMode="decimal"
                      value={line.weighte_baskol}
                      onChange={(e) => set('weighte_baskol', e.currentTarget.value)}
                    />
                  </Grid.Col>
                  <Grid.Col span={{ base: 12, sm: 6 }}>
                    <RefSelect
                      label="انبار"
                      path="/anbar"
                      valueKey="id_anbar"
                      labelKey="name_anbar"
                      value={line.id_anbar}
                      onChange={(v) => set('id_anbar', v)}
                    />
                  </Grid.Col>
                  <Grid.Col span={{ base: 12, sm: 6 }}>
                    <RefSelect
                      label="طاق"
                      path="/tagh"
                      valueKey="id_tagh"
                      labelKey="name_tagh"
                      value={line.id_tagh_anbar}
                      onChange={(v) => set('id_tagh_anbar', v)}
                    />
                  </Grid.Col>
                </Grid>
              </Paper>

              <Paper className="tally-detail-form-card" radius="lg">
                <div className="tally-detail-form-card-heading">
                  <Truck size={20} strokeWidth={1.8} aria-hidden />
                  <Text fw={700}>اطلاعات حمل و کانتینر</Text>
                </div>
                <Grid>
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
                      data={['انبارداری مسقف', 'انبارداری هانگار', 'انبارداری بارانداز', 'انبارداری محوطه']}
                      value={line.zarib_mahal || null}
                      onChange={(v) => set('zarib_mahal', v ?? '')}
                      clearable
                    />
                  </Grid.Col>
                </Grid>
              </Paper>

              {saveMutation.isError && (
                <Text c="red" size="sm">
                  ذخیره انجام نشد: {(saveMutation.error as Error).message}
                </Text>
              )}
            </Stack>
          </div>

          <Group className="tally-detail-modal-actions" justify="flex-start">
            <Button
              className="tally-detail-save-button"
              type="submit"
              loading={saveMutation.isPending}
              disabled={!canSave}
            >
              ذخیره
            </Button>
            <Button variant="default" onClick={() => setModalOpen(false)}>لغو</Button>
          </Group>
        </Stack>
      </Modal>
    </div>
  )
}
