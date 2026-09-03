// import { useEffect, useState } from 'react'
// import { useParams, useNavigate } from 'react-router-dom'
// import { BackButton } from '../components/BackButton'
// import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
// import {
//   Title, Button, Group, Table, Paper, Loader, Center, Text, Divider,
//   Modal, TextInput, Grid, Stack,
// } from '@mantine/core'
// import { apiGet, apiSend } from '../api/client'
// import { TermValueSelect } from '../components/TermValueSelect'
// import { CommodityPicker, type Commodity } from '../components/CommodityPicker'

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
//   source_anbar_names: string | null
//   source_tagh_names: string | null
// }

// type GhabzSummary = {
//   id_ghabz: number
//   ghabz_number: string | null
//   number_ghabz: number | null
//   number_tali: string | null
//   tali_id: number | null
//   created_by_username: string | null
//   created_by_full_name: string | null
// }

// type LineForm = {
//   code_kala: string
//   description_kala: string
//   hscode: string
//   type_basteh: string
//   number_kala: string
//   weighte_asnad: string
//   weighte_baskol: string
//   number_hamel: string
//   id_tagh_anbar: number | null
// }

// const EMPTY: LineForm = {
//   code_kala: '', description_kala: '', hscode: '', type_basteh: '', number_kala: '',
//   weighte_asnad: '', weighte_baskol: '', number_hamel: '', id_tagh_anbar: null,
// }

// function normalizeDigits(s: string): string {
//   return s.replace(/[\u06F0-\u06F9]/g, (d) => String(d.charCodeAt(0) - 0x06f0))
//           .replace(/[\u0660-\u0669]/g, (d) => String(d.charCodeAt(0) - 0x0660))
// }

// export function GhabzDetailPage() {
//   const { id } = useParams<{ id: string }>()
//   const headerId = Number(id)
//   const navigate = useNavigate()
//   const qc = useQueryClient()
//   const [modalOpen, setModalOpen] = useState(false)
//   const [editingId, setEditingId] = useState<number | null>(null)
//   const [line, setLine] = useState<LineForm>(EMPTY)
//   const [picked, setPicked] = useState<Commodity | null>(null)
//   // HS code of the row being edited, used to restore the catalog selection below.
//   const [hydrateHs, setHydrateHs] = useState<string | null>(null)
//   const [sourceLocations, setSourceLocations] = useState({ anbar: '', tagh: '' })

//   const { data: summary } = useQuery({
//     queryKey: ['ghabz-summary', headerId],
//     queryFn: () => apiGet<GhabzSummary>(`/ghabz/${headerId}/summary`),
//     enabled: Number.isFinite(headerId),
//   })

//   const { data: lines, isLoading } = useQuery({
//     queryKey: ['ghabz-details', headerId],
//     queryFn: () => apiGet<DetailRow[]>(`/ghabz/${headerId}/details`),
//   })

//   /**
//    * Restore the catalog selection when editing an existing line.
//    *
//    * Neither FA_ghabz_anbar_DETAILES nor FA_TALI_DETAILES stores the catalog row
//    * id — both only snapshot description / HS / storage group. So the commodity
//    * is re-resolved from the stored HS code, which is exact: FA_COMMODITY_CATALOG
//    * carries UQ_COMMODITY_HS, so one HS code means one catalog row. A line with no
//    * HS code simply leaves the picker empty, which is the honest result.
//    */
//   const { data: hsLookup } = useQuery({
//     queryKey: ['commodity-by-hs', hydrateHs],
//     queryFn: () =>
//       apiGet<{ items: Commodity[] }>(
//         `/commodity?q=${encodeURIComponent(hydrateHs ?? '')}&limit=5`,
//       ),
//     enabled: hydrateHs != null && hydrateHs.trim() !== '',
//     staleTime: 60 * 1000,
//   })

//   useEffect(() => {
//     if (hydrateHs == null || !hsLookup) return
//     const exact = hsLookup.items.find((c) => c.hs_code === hydrateHs.trim())
//     if (exact) setPicked(exact)
//   }, [hydrateHs, hsLookup])

//   function toPayload(f: LineForm) {
//     const numOrNull = (v: string) => (v.trim() === '' ? null : Number(normalizeDigits(v)))
//     const strOrNull = (v: string) => (v.trim() === '' ? null : v)
//     return {
//       id_ghabz_anbar_headar: headerId,
//       code_kala: numOrNull(f.code_kala),
//       description_kala: strOrNull(f.description_kala),
//       hscode: strOrNull(f.hscode),
//       type_basteh: strOrNull(f.type_basteh),
//       number_kala: numOrNull(f.number_kala),
//       weighte_asnad: numOrNull(f.weighte_asnad),
//       weighte_baskol: numOrNull(f.weighte_baskol),
//       number_hamel: strOrNull(f.number_hamel),
//       id_tagh_anbar: f.id_tagh_anbar,
//     }
//   }

//   const saveMutation = useMutation({
//     mutationFn: (f: LineForm) =>
//       editingId == null
//         ? apiSend('/ghabz-details', 'POST', toPayload(f))
//         : apiSend(`/ghabz-details/${editingId}`, 'PUT', toPayload(f)),
//     onSuccess: () => { qc.invalidateQueries({ queryKey: ['ghabz-details', headerId] }); setModalOpen(false) },
//   })
//   const deleteMutation = useMutation({
//     mutationFn: (lid: number) => apiSend(`/ghabz-details/${lid}`, 'DELETE'),
//     onSuccess: () => qc.invalidateQueries({ queryKey: ['ghabz-details', headerId] }),
//   })

//   const set = <K extends keyof LineForm>(k: K, v: LineForm[K]) => setLine((l) => ({ ...l, [k]: v }))

//   // snapshot description + HS from the picked catalog commodity; code_kala (= storage
//   // group) is set by CommodityPicker. HS is what lets the picker rehydrate on reopen.
//   function onPickCommodity(c: Commodity | null) {
//     setPicked(c)
//     if (!c) return
//     setHydrateHs(c.hs_code ?? null)
//     setLine((l) => ({
//       ...l,
//       description_kala: c.description_fa ?? '',
//       hscode: c.hs_code ?? '',
//     }))
//   }

//   function openAdd() {
//     setEditingId(null); setLine(EMPTY); setPicked(null); setHydrateHs(null)
//     setSourceLocations({ anbar: '', tagh: '' }); setModalOpen(true)
//   }
//   function openEdit(r: DetailRow) {
//     setEditingId(r.id_ghabz_anbar_details)
//     setPicked(null)
//     setHydrateHs(r.hscode)
//     setLine({
//       code_kala: String(r.code_kala ?? ''), description_kala: r.description_kala ?? '',
//       hscode: r.hscode ?? '',
//       type_basteh: r.type_basteh ?? '', number_kala: String(r.number_kala ?? ''),
//       weighte_asnad: String(r.weighte_asnad ?? ''), weighte_baskol: String(r.weighte_baskol ?? ''),
//       number_hamel: r.number_hamel ?? '', id_tagh_anbar: r.id_tagh_anbar,
//     })
//     setSourceLocations({
//       anbar: r.source_anbar_names ?? '',
//       tagh: r.source_tagh_names ?? r.tagh_name ?? '',
//     })
//     setModalOpen(true)
//   }

//   // The printed receipt number, not the table's primary key.
//   const receiptNumber = summary?.ghabz_number ?? summary?.number_ghabz ?? null
//   const createdBy = summary?.created_by_full_name?.trim() || summary?.created_by_username?.trim()

//   return (
//     <div dir="rtl">
//       <Group justify="space-between" mb="md">
//         <Group gap="sm" align="baseline">
//           <Title order={2}>
//             قبض انبار <bdi dir="ltr">{receiptNumber ?? '—'}</bdi>
//           </Title>
//           {summary?.number_tali && (
//             <Text c="dimmed" size="sm">تالی <bdi dir="ltr">{summary.number_tali}</bdi></Text>
//           )}
//           {createdBy && <Text c="dimmed" size="sm">ثبت‌کننده: {createdBy}</Text>}
//         </Group>
//         <Group>
//           <Button variant="light" onClick={() => navigate(`/ghabz/${headerId}/edit`)}>ویرایش سربرگ</Button>
//           <BackButton to="/ghabz" />
//         </Group>
//       </Group>
//       <Paper shadow="xs" p="md">
//         <Group justify="space-between" mb="sm">
//           <Text fw={600}>ردیف‌های کالا</Text>
//           <Button onClick={openAdd}>افزودن ردیف</Button>
//         </Group>
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
//                       <Button size="xs" variant="light" onClick={() => openEdit(r)}>ویرایش</Button>
//                       <Button size="xs" variant="light" color="red"
//                         onClick={() => deleteMutation.mutate(r.id_ghabz_anbar_details)}>حذف</Button>
//                     </Group>
//                   </Table.Td>
//                 </Table.Tr>
//               ))}
//             </Table.Tbody>
//           </Table>
//         )}
//       </Paper>
//       <Modal opened={modalOpen} onClose={() => setModalOpen(false)}
//         title={editingId == null ? 'افزودن ردیف' : 'ویرایش ردیف'} size="lg">
//         <Stack>
//           <CommodityPicker
//             picked={picked}
//             onPick={onPickCommodity}
//             groupValue={line.code_kala.trim() === '' ? null : Number(line.code_kala)}
//             onGroupChange={(v) => set('code_kala', v == null ? '' : String(v))}
//           />
//           <Divider />
//           <Grid>
//             <Grid.Col span={6}><TextInput label="شرح کالا"
//               value={line.description_kala} onChange={(e) => set('description_kala', e.currentTarget.value)} /></Grid.Col>
//             <Grid.Col span={6}><TextInput label="Hscode" inputMode="numeric"
//               value={line.hscode} onChange={(e) => set('hscode', e.currentTarget.value)} /></Grid.Col>
//             <Grid.Col span={6}><TermValueSelect label="نوع بسته‌بندی" categoryId={3}
//               value={line.type_basteh || null} onChange={(value) => set('type_basteh', value ?? '')} /></Grid.Col>
//             <Grid.Col span={6}><TextInput label="تعداد" inputMode="numeric"
//               value={line.number_kala} onChange={(e) => set('number_kala', e.currentTarget.value)} /></Grid.Col>
//             <Grid.Col span={6}><TextInput label="وزن اسناد" inputMode="numeric"
//               value={line.weighte_asnad} onChange={(e) => set('weighte_asnad', e.currentTarget.value)} /></Grid.Col>
//             <Grid.Col span={6}><TextInput label="وزن باسکول" inputMode="numeric"
//               value={line.weighte_baskol} onChange={(e) => set('weighte_baskol', e.currentTarget.value)} /></Grid.Col>
//             <Grid.Col span={6}><TextInput label="شماره حامل"
//               value={line.number_hamel} onChange={(e) => set('number_hamel', e.currentTarget.value)} /></Grid.Col>
//             {sourceLocations.anbar && (
//               <Grid.Col span={6}><TextInput label="انبارهای ردیف‌های تالی" readOnly
//                 value={sourceLocations.anbar} /></Grid.Col>
//             )}
//             {sourceLocations.tagh && (
//               <Grid.Col span={6}><TextInput label="طاق‌های ردیف‌های تالی" readOnly
//                 value={sourceLocations.tagh} /></Grid.Col>
//             )}
//           </Grid>
//           <Group justify="flex-start" mt="md">
//             <Button onClick={() => saveMutation.mutate(line)} loading={saveMutation.isPending}>ذخیره</Button>
//             <Button variant="subtle" onClick={() => setModalOpen(false)}>لغو</Button>
//           </Group>
//         </Stack>
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
import { apiGet, apiSend } from '../api/client'
import { IconPrint } from '../components/icons'

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
}

function normalizeDigits(s: string): string {
  return s.replace(/[\u06F0-\u06F9]/g, (d) => String(d.charCodeAt(0) - 0x06f0))
          .replace(/[\u0660-\u0669]/g, (d) => String(d.charCodeAt(0) - 0x0660))
}

export function GhabzDetailPage() {
  const { id } = useParams<{ id: string }>()
  const headerId = Number(id)
  const qc = useQueryClient()
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

  // Operator enters these two directly on this page; PUT only sends these
  // fields, and the factory updates only the provided columns.
  const [uniqeId, setUniqeId] = useState('')
  const [description, setDescription] = useState('')
  useEffect(() => {
    setUniqeId(summary?.number_ghabz_uniqe == null ? '' : String(summary.number_ghabz_uniqe))
    setDescription(summary?.description ?? '')
  }, [summary?.number_ghabz_uniqe, summary?.description])

  const saveExtras = useMutation({
    mutationFn: () => apiSend(`/ghabz-header/${headerId}`, 'PUT', {
      number_ghabz_uniqe: uniqeId.trim() === '' ? null : Number(normalizeDigits(uniqeId)),
      description: description.trim() === '' ? null : description,
    }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['ghabz-summary', headerId] }),
  })

  // The printed receipt number, not the table's primary key.
  const receiptNumber = summary?.ghabz_number ?? summary?.number_ghabz ?? null
  const createdBy = summary?.created_by_full_name?.trim() || summary?.created_by_username?.trim()

  return (
    <div dir="rtl">
      <Group justify="space-between" mb="md">
        <Group gap="sm" align="baseline">
          <Title order={2}>
            قبض انبار <bdi dir="ltr">{receiptNumber ?? '—'}</bdi>
            {summary?.is_master === 'yes' && (
              <Badge ml="xs" color="indigo" variant="light">مادر</Badge>
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
          <BackButton to="/ghabz" />
        </Group>
      </Group>
      <Paper shadow="xs" p="md" mb="md">
        <Grid align="flex-end">
          <Grid.Col span={{ base: 12, md: 4 }}>
            <TextInput label="شناسه یکتا" inputMode="numeric" value={uniqeId}
              onChange={(e) => { setUniqeId(e.currentTarget.value); saveExtras.reset() }} />
          </Grid.Col>
          <Grid.Col span={{ base: 12, md: 8 }}>
            <Textarea label="توضیحات" autosize minRows={2} value={description}
              onChange={(e) => { setDescription(e.currentTarget.value); saveExtras.reset() }} />
          </Grid.Col>
        </Grid>
        <Group mt="sm" gap="sm">
          <Button size="xs" loading={saveExtras.isPending} onClick={() => saveExtras.mutate()}>ذخیره</Button>
          {saveExtras.isSuccess && <Text size="xs" c="teal">ذخیره شد</Text>}
          {saveExtras.isError && <Text size="xs" c="red">خطا در ذخیره</Text>}
        </Group>
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
                      <Button
                        size="xs"
                        variant="light"
                        color="red"
                        loading={deleteMutation.isPending && deleteMutation.variables === r.id_ghabz_anbar_details}
                        onClick={() => deleteMutation.mutate(r.id_ghabz_anbar_details)}
                      >
                        حذف
                      </Button>
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
            <Grid.Col span={6}><TextInput label="شماره حامل" readOnly value={selectedLine.number_hamel ?? '—'} /></Grid.Col>
          </Grid>
        )}
      </Modal>
    </div>
  )
}
