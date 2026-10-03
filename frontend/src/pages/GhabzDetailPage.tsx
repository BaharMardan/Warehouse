// import { useEffect, useState } from 'react'
// import { useParams } from 'react-router-dom'
// import { BackButton } from '../components/BackButton'
// import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
// import {
//   Badge, Title, Button, Group, Table, Paper, Loader, Center, Text, Divider,
//   Modal, TextInput, Textarea, Grid,
// } from '@mantine/core'
// import { apiGet, apiSend } from '../api/client'
// import { IconPrint } from '../components/icons'

// type DetailRow = {
//   id_ghabz_anbar_details: number
//   id_ghabz_anbar_headar: number
//   code_kala: number | null
//   code_kala_kantiner: number | null
//   description_kala: string | null
//   hscode: string | null
//   type_basteh: string | null
//   number_kala: number | null
//   number_kantiner: number | null
//   weighte_asnad: number | null
//   weighte_baskol: number | null
//   number_hamel: string | null
//   id_tagh_anbar: number | null
//   tagh_name: string | null
// }

// type GhabzSummary = {
//   id_ghabz: number
//   ghabz_number: string | null
//   is_master: string | null
//   number_ghabz: number | null
//   number_tali: string | null
//   tali_id: number | null
//   created_by_username: string | null
//   created_by_full_name: string | null
//   number_ghabz_uniqe: number | null
//   description: string | null
// }

// function normalizeDigits(s: string): string {
//   return s.replace(/[\u06F0-\u06F9]/g, (d) => String(d.charCodeAt(0) - 0x06f0))
//           .replace(/[\u0660-\u0669]/g, (d) => String(d.charCodeAt(0) - 0x0660))
// }

// export function GhabzDetailPage() {
//   const { id } = useParams<{ id: string }>()
//   const headerId = Number(id)
//   const qc = useQueryClient()
//   const [selectedLine, setSelectedLine] = useState<DetailRow | null>(null)

//   const { data: summary } = useQuery({
//     queryKey: ['ghabz-summary', headerId],
//     queryFn: () => apiGet<GhabzSummary>(`/ghabz/${headerId}/summary`),
//     enabled: Number.isFinite(headerId),
//   })

//   const { data: lines, isLoading } = useQuery({
//     queryKey: ['ghabz-details', headerId],
//     queryFn: () => apiGet<DetailRow[]>(`/ghabz/${headerId}/details`),
//   })

//   const deleteMutation = useMutation({
//     mutationFn: (lineId: number) => apiSend(`/ghabz-details/${lineId}`, 'DELETE'),
//     onSuccess: () => qc.invalidateQueries({ queryKey: ['ghabz-details', headerId] }),
//   })

//   // Operator enters these two directly on this page; PUT only sends these
//   // fields, and the factory updates only the provided columns.
//   const [uniqeId, setUniqeId] = useState('')
//   const [description, setDescription] = useState('')
//   useEffect(() => {
//     setUniqeId(summary?.number_ghabz_uniqe == null ? '' : String(summary.number_ghabz_uniqe))
//     setDescription(summary?.description ?? '')
//   }, [summary?.number_ghabz_uniqe, summary?.description])

//   const saveExtras = useMutation({
//     mutationFn: () => apiSend(`/ghabz-header/${headerId}`, 'PUT', {
//       number_ghabz_uniqe: uniqeId.trim() === '' ? null : Number(normalizeDigits(uniqeId)),
//       description: description.trim() === '' ? null : description,
//     }),
//     onSuccess: () => Promise.all([qc.invalidateQueries({ queryKey: ['ghabz-summary'] }), qc.invalidateQueries({ queryKey: ['receipt-workflow'] })]),
//   })

//   // The printed receipt number, not the table's primary key.
//   const receiptNumber = summary?.ghabz_number ?? summary?.number_ghabz ?? null
//   const createdBy = summary?.created_by_full_name?.trim() || summary?.created_by_username?.trim()

//   return (
//     <div dir="rtl">
//       <Group justify="space-between" mb="md">
//         <Group gap="sm" align="baseline">
//           <Title order={2}>
//             قبض انبار <bdi dir="ltr">{receiptNumber ?? '—'}</bdi>
//             {summary?.is_master === 'yes' && (
//               <Badge ml="xs" color="indigo" variant="light">مادر</Badge>
//             )}
//           </Title>
//           {summary?.number_tali && (
//             <Text c="dimmed" size="sm">تالی <bdi dir="ltr">{summary.number_tali}</bdi></Text>
//           )}
//           {createdBy && <Text c="dimmed" size="sm">ثبت‌کننده: {createdBy}</Text>}
//         </Group>
//         <Group>
//           <Button
//             className="ghabz-print-launch-button"
//             variant="filled"
//             leftSection={<IconPrint size={18} />}
//             onClick={() => window.open(`/ghabz/${headerId}/print`, '_blank', 'noopener,noreferrer')}
//           >
//             چاپ قبض انبار
//           </Button>
//           <BackButton to="/ghabz" />
//         </Group>
//       </Group>
//       <Paper shadow="xs" p="md" mb="md">
//         <Grid align="flex-end">
//           <Grid.Col span={{ base: 12, md: 4 }}>
//             <TextInput label="شناسه یکتا" inputMode="numeric" value={uniqeId}
//               onChange={(e) => { setUniqeId(e.currentTarget.value); saveExtras.reset() }} />
//           </Grid.Col>
//           <Grid.Col span={{ base: 12, md: 8 }}>
//             <Textarea label="توضیحات" autosize minRows={2} value={description}
//               onChange={(e) => { setDescription(e.currentTarget.value); saveExtras.reset() }} />
//           </Grid.Col>
//         </Grid>
//         <Group mt="sm" gap="sm">
//           <Button size="xs" loading={saveExtras.isPending} onClick={() => saveExtras.mutate()}>ذخیره</Button>
//           {saveExtras.isSuccess && <Text size="xs" c="teal">ذخیره شد</Text>}
//           {saveExtras.isError && <Text size="xs" c="red">خطا در ذخیره</Text>}
//         </Group>
//       </Paper>
//       <Paper shadow="xs" p="md">
//         <Text fw={600} mb="sm">ردیف‌های کالا</Text>
//         <Divider mb="sm" />
//         {isLoading && <Center py="xl"><Loader /></Center>}
//         {lines && lines.length === 0 && <Center py="xl"><Text c="dimmed">ردیفی ثبت نشده است.</Text></Center>}
//         {lines && lines.length > 0 && (
//           <Table striped withTableBorder>
//             <Table.Thead><Table.Tr>
//               <Table.Th>کد گروه کالا</Table.Th><Table.Th>Hscode</Table.Th>
//               <Table.Th>شرح</Table.Th><Table.Th>نوع بسته</Table.Th>
//               <Table.Th>تعداد</Table.Th><Table.Th>وزن اسناد</Table.Th><Table.Th>وزن باسکول</Table.Th>
//               <Table.Th>طاق</Table.Th><Table.Th>عملیات</Table.Th>
//             </Table.Tr></Table.Thead>
//             <Table.Tbody>
//               {lines.map((r) => (
//                 <Table.Tr key={r.id_ghabz_anbar_details}>
//                   <Table.Td><bdi dir="ltr">{r.code_kala ?? '—'}</bdi></Table.Td>
//                   <Table.Td><bdi dir="ltr">{r.hscode ?? '—'}</bdi></Table.Td>
//                   <Table.Td>{r.description_kala ?? '—'}</Table.Td>
//                   <Table.Td>{r.type_basteh ?? '—'}</Table.Td>
//                   <Table.Td>{r.number_kala ?? '—'}</Table.Td>
//                   <Table.Td>{r.weighte_asnad ?? '—'}</Table.Td>
//                   <Table.Td>{r.weighte_baskol ?? '—'}</Table.Td>
//                   <Table.Td>{r.tagh_name ?? '—'}</Table.Td>
//                   <Table.Td>
//                     <Group gap="xs">
//                       <Button size="xs" variant="light" onClick={() => setSelectedLine(r)}>
//                         مشاهده جزئیات
//                       </Button>
//                       <Button
//                         size="xs"
//                         variant="light"
//                         color="red"
//                         loading={deleteMutation.isPending && deleteMutation.variables === r.id_ghabz_anbar_details}
//                         onClick={() => deleteMutation.mutate(r.id_ghabz_anbar_details)}
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
//       <Modal opened={selectedLine != null} onClose={() => setSelectedLine(null)}
//         title="مشاهده جزئیات ردیف" size="lg">
//         {selectedLine && (
//           <Grid>
//             <Grid.Col span={6}><TextInput label="کد گروه کالا" readOnly value={selectedLine.code_kala ?? '—'} /></Grid.Col>
//             <Grid.Col span={6}><TextInput label="HS Code" readOnly value={selectedLine.hscode ?? '—'} /></Grid.Col>
//             <Grid.Col span={12}><TextInput label="شرح کالا" readOnly value={selectedLine.description_kala ?? '—'} /></Grid.Col>
//             <Grid.Col span={6}><TextInput label="نوع بسته‌بندی" readOnly value={selectedLine.type_basteh ?? '—'} /></Grid.Col>
//             <Grid.Col span={6}><TextInput label="تعداد" readOnly value={selectedLine.number_kala ?? '—'} /></Grid.Col>
//             <Grid.Col span={6}><TextInput label="وزن اسناد" readOnly value={selectedLine.weighte_asnad ?? '—'} /></Grid.Col>
//             <Grid.Col span={6}><TextInput label="وزن باسکول" readOnly value={selectedLine.weighte_baskol ?? '—'} /></Grid.Col>
//             <Grid.Col span={6}><TextInput label="طاق" readOnly value={selectedLine.tagh_name ?? '—'} /></Grid.Col>
//             <Grid.Col span={12}><Textarea label="شماره‌های حامل" readOnly autosize minRows={2} maxRows={8} value={(selectedLine.carriers ?? [selectedLine.number_hamel ?? '']).filter(Boolean).join('\n') || '—'} /></Grid.Col>
//           </Grid>
//         )}
//       </Modal>
//     </div>
//   )
// }


// import { useEffect, useState } from 'react'
// import { useParams } from 'react-router-dom'
// import { BackButton } from '../components/BackButton'
// import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
// import {
//   Badge, Title, Button, Group, Table, Paper, Loader, Center, Text, Divider,
//   Modal, TextInput, Textarea, Grid,
// } from '@mantine/core'
// import { apiGet, apiSend } from '../api/client'
// import { IconPrint } from '../components/icons'

// type DetailRow = {
//   id_ghabz_anbar_details: number
//   id_ghabz_anbar_headar: number
//   code_kala: number | null
//   code_kala_kantiner: number | null
//   description_kala: string | null
//   hscode: string | null
//   type_basteh: string | null
//   number_kala: number | null
//   number_kantiner: number | null
//   weighte_asnad: number | null
//   weighte_baskol: number | null
//   number_hamel: string | null
//   id_tagh_anbar: number | null
//   tagh_name: string | null
// }

// type GhabzSummary = {
//   id_ghabz: number
//   ghabz_number: string | null
//   is_master: string | null
//   number_ghabz: number | null
//   number_tali: string | null
//   tali_id: number | null
//   created_by_username: string | null
//   created_by_full_name: string | null
//   number_ghabz_uniqe: number | null
//   description: string | null
// }

// function normalizeDigits(s: string): string {
//   return s.replace(/[\u06F0-\u06F9]/g, (d) => String(d.charCodeAt(0) - 0x06f0))
//           .replace(/[\u0660-\u0669]/g, (d) => String(d.charCodeAt(0) - 0x0660))
// }

// export function GhabzDetailPage() {
//   const { id } = useParams<{ id: string }>()
//   const headerId = Number(id)
//   const qc = useQueryClient()
//   const [selectedLine, setSelectedLine] = useState<DetailRow | null>(null)

//   const { data: summary } = useQuery({
//     queryKey: ['ghabz-summary', headerId],
//     queryFn: () => apiGet<GhabzSummary>(`/ghabz/${headerId}/summary`),
//     enabled: Number.isFinite(headerId),
//   })

//   const { data: lines, isLoading } = useQuery({
//     queryKey: ['ghabz-details', headerId],
//     queryFn: () => apiGet<DetailRow[]>(`/ghabz/${headerId}/details`),
//   })

//   const deleteMutation = useMutation({
//     mutationFn: (lineId: number) => apiSend(`/ghabz-details/${lineId}`, 'DELETE'),
//     onSuccess: () => qc.invalidateQueries({ queryKey: ['ghabz-details', headerId] }),
//   })

//   // Operator enters these two directly on this page; PUT only sends these
//   // fields, and the factory updates only the provided columns.
//   const [uniqeId, setUniqeId] = useState('')
//   const [description, setDescription] = useState('')
//   useEffect(() => {
//     setUniqeId(summary?.number_ghabz_uniqe == null ? '' : String(summary.number_ghabz_uniqe))
//     setDescription(summary?.description ?? '')
//   }, [summary?.number_ghabz_uniqe, summary?.description])

//   const saveExtras = useMutation({
//     mutationFn: () => apiSend(`/ghabz-header/${headerId}`, 'PUT', {
//       number_ghabz_uniqe: uniqeId.trim() === '' ? null : Number(normalizeDigits(uniqeId)),
//       description: description.trim() === '' ? null : description,
//     }),
//     onSuccess: () => Promise.all([qc.invalidateQueries({ queryKey: ['ghabz-summary'] }), qc.invalidateQueries({ queryKey: ['receipt-workflow'] })]),
//   })

//   // The printed receipt number, not the table's primary key.
//   const receiptNumber = summary?.ghabz_number ?? summary?.number_ghabz ?? null
//   const createdBy = summary?.created_by_full_name?.trim() || summary?.created_by_username?.trim()
//   const savedUniqueId = summary?.number_ghabz_uniqe == null ? '' : String(summary.number_ghabz_uniqe)
//   const extrasChanged = uniqeId.trim() !== savedUniqueId || description !== (summary?.description ?? '')

//   return (
//     <div dir="rtl">
//       <Group justify="space-between" mb="md">
//         <Group gap="sm" align="baseline">
//           <Title order={2}>
//             قبض انبار <bdi dir="ltr">{receiptNumber ?? '—'}</bdi>
//             {summary?.is_master === 'yes' && (
//               <Badge ml="xs" color="indigo" variant="light">مادر</Badge>
//             )}
//           </Title>
//           {summary?.number_tali && (
//             <Text c="dimmed" size="sm">تالی <bdi dir="ltr">{summary.number_tali}</bdi></Text>
//           )}
//           {createdBy && <Text c="dimmed" size="sm">ثبت‌کننده: {createdBy}</Text>}
//         </Group>
//         <Group>
//           <Button
//             className="ghabz-print-launch-button"
//             variant="filled"
//             leftSection={<IconPrint size={18} />}
//             onClick={() => window.open(`/ghabz/${headerId}/print`, '_blank', 'noopener,noreferrer')}
//           >
//             چاپ قبض انبار
//           </Button>
//           <BackButton to="/ghabz" />
//         </Group>
//       </Group>
//       <Paper shadow="sm" radius="lg" p="lg" mb="md" withBorder>
//         <Group justify="space-between" align="flex-start" mb="md">
//           <div>
//             <Text fw={700}>اطلاعات تکمیلی قبض</Text>
//             <Text size="xs" c="dimmed" mt={3}>
//               شناسه یکتا و توضیحات موردنیاز برای چاپ قبض را وارد کنید.
//             </Text>
//           </div>
//           {saveExtras.isSuccess && <Badge color="teal" variant="light">ذخیره شد</Badge>}
//           {saveExtras.isError && <Badge color="red" variant="light">خطا در ذخیره</Badge>}
//         </Group>

//         <Grid gutter="md" align="stretch">
//           <Grid.Col span={{ base: 12, md: 6 }}>
//             <TextInput
//               label="شناسه یکتا"
//               inputMode="numeric"
//               size="md"
//               radius="md"
//               value={uniqeId}
//               styles={{ input: { minHeight: 72 } }}
//               onChange={(e) => { setUniqeId(e.currentTarget.value); saveExtras.reset() }} />
//           </Grid.Col>
//           <Grid.Col span={{ base: 12, md: 6 }}>
//             <Textarea
//               label="توضیحات"
//               minRows={2}
//               size="md"
//               radius="md"
//               value={description}
//               styles={{ input: { minHeight: 72, resize: 'vertical' } }}
//               onChange={(e) => { setDescription(e.currentTarget.value); saveExtras.reset() }} />
//           </Grid.Col>
//         </Grid>
//         <Group justify="flex-start" mt="md">
//           <Button
//             radius="md"
//             loading={saveExtras.isPending}
//             disabled={!extrasChanged}
//             onClick={() => saveExtras.mutate()}
//           >
//             ذخیره اطلاعات
//           </Button>
//         </Group>
//       </Paper>
//       <Paper shadow="xs" p="md">
//         <Text fw={600} mb="sm">ردیف‌های کالا</Text>
//         <Divider mb="sm" />
//         {isLoading && <Center py="xl"><Loader /></Center>}
//         {lines && lines.length === 0 && <Center py="xl"><Text c="dimmed">ردیفی ثبت نشده است.</Text></Center>}
//         {lines && lines.length > 0 && (
//           <Table striped withTableBorder>
//             <Table.Thead><Table.Tr>
//               <Table.Th>کد گروه کالا</Table.Th><Table.Th>Hscode</Table.Th>
//               <Table.Th>شرح</Table.Th><Table.Th>نوع بسته</Table.Th>
//               <Table.Th>تعداد</Table.Th><Table.Th>وزن اسناد</Table.Th><Table.Th>وزن باسکول</Table.Th>
//               <Table.Th>طاق</Table.Th><Table.Th>عملیات</Table.Th>
//             </Table.Tr></Table.Thead>
//             <Table.Tbody>
//               {lines.map((r) => (
//                 <Table.Tr key={r.id_ghabz_anbar_details}>
//                   <Table.Td><bdi dir="ltr">{r.code_kala ?? '—'}</bdi></Table.Td>
//                   <Table.Td><bdi dir="ltr">{r.hscode ?? '—'}</bdi></Table.Td>
//                   <Table.Td>{r.description_kala ?? '—'}</Table.Td>
//                   <Table.Td>{r.type_basteh ?? '—'}</Table.Td>
//                   <Table.Td>{r.number_kala ?? '—'}</Table.Td>
//                   <Table.Td>{r.weighte_asnad ?? '—'}</Table.Td>
//                   <Table.Td>{r.weighte_baskol ?? '—'}</Table.Td>
//                   <Table.Td>{r.tagh_name ?? '—'}</Table.Td>
//                   <Table.Td>
//                     <Group gap="xs">
//                       <Button size="xs" variant="light" onClick={() => setSelectedLine(r)}>
//                         مشاهده جزئیات
//                       </Button>
//                       <Button
//                         size="xs"
//                         variant="light"
//                         color="red"
//                         loading={deleteMutation.isPending && deleteMutation.variables === r.id_ghabz_anbar_details}
//                         onClick={() => deleteMutation.mutate(r.id_ghabz_anbar_details)}
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
//       <Modal opened={selectedLine != null} onClose={() => setSelectedLine(null)}
//         title="مشاهده جزئیات ردیف" size="lg">
//         {selectedLine && (
//           <Grid>
//             <Grid.Col span={6}><TextInput label="کد گروه کالا" readOnly value={selectedLine.code_kala ?? '—'} /></Grid.Col>
//             <Grid.Col span={6}><TextInput label="HS Code" readOnly value={selectedLine.hscode ?? '—'} /></Grid.Col>
//             <Grid.Col span={12}><TextInput label="شرح کالا" readOnly value={selectedLine.description_kala ?? '—'} /></Grid.Col>
//             <Grid.Col span={6}><TextInput label="نوع بسته‌بندی" readOnly value={selectedLine.type_basteh ?? '—'} /></Grid.Col>
//             <Grid.Col span={6}><TextInput label="تعداد" readOnly value={selectedLine.number_kala ?? '—'} /></Grid.Col>
//             <Grid.Col span={6}><TextInput label="وزن اسناد" readOnly value={selectedLine.weighte_asnad ?? '—'} /></Grid.Col>
//             <Grid.Col span={6}><TextInput label="وزن باسکول" readOnly value={selectedLine.weighte_baskol ?? '—'} /></Grid.Col>
//             <Grid.Col span={6}><TextInput label="طاق" readOnly value={selectedLine.tagh_name ?? '—'} /></Grid.Col>
//             <Grid.Col span={12}><Textarea label="شماره‌های حامل" readOnly autosize minRows={2} maxRows={8} value={(selectedLine.carriers ?? [selectedLine.number_hamel ?? '']).filter(Boolean).join('\n') || '—'} /></Grid.Col>
//           </Grid>
//         )}
//       </Modal>
//     </div>
//   )
// }


import { useEffect, useState } from 'react'
import { useParams } from 'react-router-dom'
import { BackButton } from '../components/BackButton'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import {
  Badge, Title, Button, Group, Table, Paper, Loader, Center, Text, Divider,
  Modal, TextInput, Textarea, Grid,
} from '@mantine/core'
import { apiGet, apiSend, errorMessage } from '../api/client'
import { IconPrint } from '../components/icons'
import { usePermissions } from '../auth/usePermissions'
import { ReceiptWorkflow, useReceiptWorkflow } from '../components/ReceiptWorkflow'

type DetailRow = {
  id_ghabz_anbar_details: number
  id_ghabz_anbar_headar: number
  code_kala: number | null
  code_kala_kantiner: number | null
  description_kala: string | null
  hscode: string | null
  type_basteh: string | null
  number_kala: number | null
  number_kantiner: number | null
  weighte_asnad: number | null
  weighte_baskol: number | null
  carriers?: string[]
  number_hamel: string | null
  id_tagh_anbar: number | null
  tagh_name: string | null
}

type GhabzSummary = {
  id_ghabz: number
  ghabz_number: string | null
  is_master: string | null
  number_ghabz: number | null
  number_tali: string | null
  tali_id: number | null
  created_by_username: string | null
  created_by_full_name: string | null
  number_ghabz_uniqe: number | null
  description: string | null
  pallet_quantity: number | null
  cargo_type: string | null
  total_pallet_quantity: number | null
  available_pallet_quantity: number | null
}

function normalizeDigits(s: string): string {
  return s.replace(/[\u06F0-\u06F9]/g, (d) => String(d.charCodeAt(0) - 0x06f0))
          .replace(/[\u0660-\u0669]/g, (d) => String(d.charCodeAt(0) - 0x0660))
}

export function GhabzDetailPage() {
  const { id } = useParams<{ id: string }>()
  const headerId = Number(id)
  const qc = useQueryClient()
  const { data: workflow } = useReceiptWorkflow(headerId)
  const canEdit = usePermissions().can('ghabz.edit') && workflow != null && !['finalized', 'invoice_issued'].includes(workflow.status)
  const [selectedLine, setSelectedLine] = useState<DetailRow | null>(null)

  const { data: summary } = useQuery({
    queryKey: ['ghabz-summary', headerId],
    queryFn: () => apiGet<GhabzSummary>(`/ghabz/${headerId}/summary`),
    enabled: Number.isFinite(headerId),
  })

  const { data: lines, isLoading } = useQuery({
    queryKey: ['ghabz-details', headerId],
    queryFn: () => apiGet<DetailRow[]>(`/ghabz/${headerId}/details`),
  })

  const deleteMutation = useMutation({
    mutationFn: (lineId: number) => apiSend(`/ghabz-details/${lineId}`, 'DELETE'),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['ghabz-details', headerId] }),
  })

  // Completion fields are saved through the validated receipt extras endpoint.
  const [uniqeId, setUniqeId] = useState('')
  const [description, setDescription] = useState('')
  const [palletQuantity, setPalletQuantity] = useState('')
  const showPalletQuantity = summary != null && summary.is_master !== 'yes' && summary.cargo_type === 'volumetric'
  const palletText = normalizeDigits(palletQuantity.trim())
  const palletValue = palletText === '' ? null : Number(palletText)
  const palletError = showPalletQuantity && palletValue !== null
    ? (!/^\d+$/.test(palletText) || !Number.isSafeInteger(palletValue) || palletValue < 1
      ? 'تعداد پالت باید عدد صحیح مثبت باشد'
      : summary?.available_pallet_quantity == null || palletValue > summary.available_pallet_quantity
        ? 'تعداد پالت نباید بیشتر از پالت باقی‌مانده قابل تخصیص باشد' : null)
    : null
  useEffect(() => {
    setUniqeId(summary?.number_ghabz_uniqe == null ? '' : String(summary.number_ghabz_uniqe))
    setDescription(summary?.description ?? '')
    setPalletQuantity(summary?.pallet_quantity == null ? '' : String(summary.pallet_quantity))
  }, [headerId, summary?.number_ghabz_uniqe, summary?.description, summary?.pallet_quantity])

  const saveExtras = useMutation({
    mutationFn: () => apiSend(`/ghabz/${headerId}/extras`, 'PUT', {
      number_ghabz_uniqe: uniqeId.trim() === '' ? null : Number(normalizeDigits(uniqeId)),
      description: description.trim() === '' ? null : description,
      ...(showPalletQuantity ? { pallet_quantity: palletValue } : {}),
    }),
    onSuccess: () => Promise.all([qc.invalidateQueries({ queryKey: ['ghabz-summary'] }), qc.invalidateQueries({ queryKey: ['receipt-workflow'] })]),
  })

  // The printed receipt number, not the table's primary key.
  const receiptNumber = summary?.ghabz_number ?? summary?.number_ghabz ?? null
  const createdBy = summary?.created_by_full_name?.trim() || summary?.created_by_username?.trim()
  const savedUniqueId = summary?.number_ghabz_uniqe == null ? '' : String(summary.number_ghabz_uniqe)
  const extrasChanged = uniqeId.trim() !== savedUniqueId || description !== (summary?.description ?? '') || (showPalletQuantity && palletValue !== (summary?.pallet_quantity ?? null))

  return (
    <div dir="rtl">
      <Group justify="space-between" mb="md">
        <Group gap="sm" align="baseline">
          <Title order={2}>
            قبض انبار <bdi dir="ltr">{receiptNumber ?? '—'}</bdi>
            {summary?.is_master !== 'yes' && (
              <Badge ml="xs" color="indigo" variant="light">تفکیکی</Badge>
            )}
          </Title>
          {summary?.number_tali && (
            <Text c="dimmed" size="sm">تالی <bdi dir="ltr">{summary.number_tali}</bdi></Text>
          )}
          {createdBy && <Text c="dimmed" size="sm">ثبت‌کننده: {createdBy}</Text>}
        </Group>
        <Group>
          <Button
            className="ghabz-print-launch-button"
            variant="filled"
            leftSection={<IconPrint size={18} />}
            onClick={() => window.open(`/ghabz/${headerId}/print`, '_blank', 'noopener,noreferrer')}
          >
            چاپ قبض انبار
          </Button>
          <ReceiptWorkflow id={headerId} />
          <BackButton to="/ghabz" />
        </Group>
      </Group>
      <Paper shadow="sm" radius="lg" p="lg" mb="md" withBorder>
        <Group justify="space-between" align="flex-start" mb="md">
          <div>
            <Text fw={700}>اطلاعات تکمیلی قبض</Text>
            <Text size="xs" c="dimmed" mt={3}>
              شناسه یکتا و توضیحات موردنیاز برای چاپ قبض را وارد کنید.
            </Text>
          </div>
          {saveExtras.isSuccess && <Badge color="teal" variant="light">ذخیره شد</Badge>}
          {saveExtras.isError && <Badge color="red" variant="light">خطا در ذخیره</Badge>}
        </Group>

        <Grid gutter="md" align="stretch">
          <Grid.Col span={{ base: 12, md: showPalletQuantity ? 4 : 6 }}>
            <TextInput
              label="شناسه یکتا"
              inputMode="numeric"
              size="md"
              radius="md"
              value={uniqeId}
              readOnly={!canEdit}
              styles={{ input: { minHeight: 72 } }}
              onChange={(e) => { setUniqeId(e.currentTarget.value); saveExtras.reset() }} />
          </Grid.Col>
          {showPalletQuantity && (
            <Grid.Col span={{ base: 12, md: 4 }}>
              <TextInput
                label="تعداد پالت"
                description={summary?.total_pallet_quantity == null
                  ? 'تعداد کل پالت در تالی ثبت نشده است'
                  : `تعداد کل پالت تالی: ${summary.total_pallet_quantity.toLocaleString('fa-IR')} | قابل تخصیص به این قبض: ${summary.available_pallet_quantity?.toLocaleString('fa-IR') ?? '—'}`}
                inputMode="numeric"
                size="md"
                radius="md"
                inputWrapperOrder={['label', 'input', 'description', 'error']}
                value={palletQuantity}
                readOnly={!canEdit}
                error={palletError}
                styles={{ input: { minHeight: 72 } }}
                onChange={(e) => { setPalletQuantity(e.currentTarget.value); saveExtras.reset() }} />
            </Grid.Col>
          )}
          <Grid.Col span={{ base: 12, md: showPalletQuantity ? 4 : 6 }}>
            <Textarea
              label="توضیحات"
              minRows={2}
              size="md"
              radius="md"
              value={description}
              readOnly={!canEdit}
              styles={{ input: { minHeight: 72, resize: 'vertical' } }}
              onChange={(e) => { setDescription(e.currentTarget.value); saveExtras.reset() }} />
          </Grid.Col>
        </Grid>
        {saveExtras.isError && <Text c="red" size="sm" mt="xs">
          {errorMessage(saveExtras.error, 'ذخیره اطلاعات انجام نشد')}
        </Text>}
        {canEdit && (
          <Group justify="flex-start" mt="md">
            <Button
              radius="md"
              loading={saveExtras.isPending}
              disabled={!summary || !extrasChanged || palletError != null}
              onClick={() => saveExtras.mutate()}
            >
              ذخیره اطلاعات
            </Button>
          </Group>
        )}
      </Paper>
      <Paper shadow="xs" p="md">
        <Text fw={600} mb="sm">ردیف‌های کالا</Text>
        <Divider mb="sm" />
        {isLoading && <Center py="xl"><Loader /></Center>}
        {lines && lines.length === 0 && <Center py="xl"><Text c="dimmed">ردیفی ثبت نشده است.</Text></Center>}
        {lines && lines.length > 0 && (
          <Table striped withTableBorder>
            <Table.Thead><Table.Tr>
              <Table.Th>کد گروه کالا</Table.Th><Table.Th>Hscode</Table.Th>
              <Table.Th>شرح</Table.Th><Table.Th>نوع بسته</Table.Th>
              <Table.Th>تعداد</Table.Th><Table.Th>وزن اسناد</Table.Th><Table.Th>وزن باسکول</Table.Th>
              <Table.Th>طاق</Table.Th><Table.Th>عملیات</Table.Th>
            </Table.Tr></Table.Thead>
            <Table.Tbody>
              {lines.map((r) => (
                <Table.Tr key={r.id_ghabz_anbar_details}>
                  <Table.Td><bdi dir="ltr">{r.code_kala ?? '—'}</bdi></Table.Td>
                  <Table.Td><bdi dir="ltr">{r.hscode ?? '—'}</bdi></Table.Td>
                  <Table.Td>{r.description_kala ?? '—'}</Table.Td>
                  <Table.Td>{r.type_basteh ?? '—'}</Table.Td>
                  <Table.Td>{r.number_kala ?? '—'}</Table.Td>
                  <Table.Td>{r.weighte_asnad ?? '—'}</Table.Td>
                  <Table.Td>{r.weighte_baskol ?? '—'}</Table.Td>
                  <Table.Td>{r.tagh_name ?? '—'}</Table.Td>
                  <Table.Td>
                    <Group gap="xs">
                      <Button size="xs" variant="light" onClick={() => setSelectedLine(r)}>
                        مشاهده جزئیات
                      </Button>
                      {canEdit && (
                        <Button
                          size="xs"
                          variant="light"
                          color="red"
                          loading={deleteMutation.isPending && deleteMutation.variables === r.id_ghabz_anbar_details}
                          onClick={() => deleteMutation.mutate(r.id_ghabz_anbar_details)}
                        >
                          حذف
                        </Button>
                      )}
                    </Group>
                  </Table.Td>
                </Table.Tr>
              ))}
            </Table.Tbody>
          </Table>
        )}
      </Paper>
      <Modal opened={selectedLine != null} onClose={() => setSelectedLine(null)}
        title="مشاهده جزئیات ردیف" size="lg">
        {selectedLine && (
          <Grid>
            <Grid.Col span={6}><TextInput label="کد گروه کالا" readOnly value={selectedLine.code_kala ?? '—'} /></Grid.Col>
            <Grid.Col span={6}><TextInput label="HS Code" readOnly value={selectedLine.hscode ?? '—'} /></Grid.Col>
            <Grid.Col span={12}><TextInput label="شرح کالا" readOnly value={selectedLine.description_kala ?? '—'} /></Grid.Col>
            <Grid.Col span={6}><TextInput label="نوع بسته‌بندی" readOnly value={selectedLine.type_basteh ?? '—'} /></Grid.Col>
            <Grid.Col span={6}><TextInput label="تعداد" readOnly value={selectedLine.number_kala ?? '—'} /></Grid.Col>
            <Grid.Col span={6}><TextInput label="وزن اسناد" readOnly value={selectedLine.weighte_asnad ?? '—'} /></Grid.Col>
            <Grid.Col span={6}><TextInput label="وزن باسکول" readOnly value={selectedLine.weighte_baskol ?? '—'} /></Grid.Col>
            <Grid.Col span={6}><TextInput label="طاق" readOnly value={selectedLine.tagh_name ?? '—'} /></Grid.Col>
            <Grid.Col span={12}><Textarea label="شماره‌های حامل" readOnly autosize minRows={2} maxRows={8} value={(selectedLine.carriers ?? [selectedLine.number_hamel ?? '']).filter(Boolean).join('\n') || '—'} /></Grid.Col>
          </Grid>
        )}
      </Modal>
    </div>
  )
}
