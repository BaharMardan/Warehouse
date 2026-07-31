// import { useState } from 'react'
// import { useParams, useNavigate } from 'react-router-dom'
// import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
// import {
//   Title, Button, Group, Table, Paper, Loader, Center, Text, Divider,
//   Modal, TextInput, Grid, Stack,
// } from '@mantine/core'
// import { apiGet, apiSend } from '../api/client'
// import { RefSelect } from '../components/RefSelect'
// import { CommodityPicker, type Commodity } from '../components/CommodityPicker'

// type DetailRow = {
//   id_ghabz_anbar_details: number
//   id_ghabz_anbar_headar: number
//   code_kala: number
//   code_kala_kantiner: number | null
//   description_kala: string | null
//   type_basteh: string | null
//   number_kala: number
//   number_kantiner: number | null
//   weighte_asnad: number
//   weighte_baskol: number
//   number_hamel: string | null
//   id_tagh_anbar: number | null
//   tagh_name: string | null
// }

// type LineForm = {
//   code_kala: string
//   description_kala: string
//   type_basteh: string
//   number_kala: string
//   weighte_asnad: string
//   weighte_baskol: string
//   number_hamel: string
//   id_tagh_anbar: number | null
// }

// const EMPTY: LineForm = {
//   code_kala: '', description_kala: '', type_basteh: '', number_kala: '',
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

//   const { data: lines, isLoading } = useQuery({
//     queryKey: ['ghabz-details', headerId],
//     queryFn: () => apiGet<DetailRow[]>(`/ghabz/${headerId}/details`),
//   })

//   function toPayload(f: LineForm) {
//     const numOrNull = (v: string) => (v.trim() === '' ? null : Number(normalizeDigits(v)))
//     const strOrNull = (v: string) => (v.trim() === '' ? null : v)
//     return {
//       id_ghabz_anbar_headar: headerId,
//       code_kala: Number(normalizeDigits(f.code_kala)),
//       description_kala: strOrNull(f.description_kala),
//       type_basteh: strOrNull(f.type_basteh),
//       number_kala: Number(normalizeDigits(f.number_kala)),
//       weighte_asnad: Number(normalizeDigits(f.weighte_asnad)),
//       weighte_baskol: Number(normalizeDigits(f.weighte_baskol)),
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

//   // snapshot the description from the picked catalog commodity (ghabz lines carry no
//   // hscode/unit/duty columns); code_kala (= storage group) is set by CommodityPicker.
//   function onPickCommodity(c: Commodity | null) {
//     setPicked(c)
//     if (!c) return
//     setLine((l) => ({ ...l, description_kala: c.description_fa ?? '' }))
//   }

//   function openAdd() { setEditingId(null); setLine(EMPTY); setPicked(null); setModalOpen(true) }
//   function openEdit(r: DetailRow) {
//     setEditingId(r.id_ghabz_anbar_details)
//     setPicked(null)
//     setLine({
//       code_kala: String(r.code_kala ?? ''), description_kala: r.description_kala ?? '',
//       type_basteh: r.type_basteh ?? '', number_kala: String(r.number_kala ?? ''),
//       weighte_asnad: String(r.weighte_asnad ?? ''), weighte_baskol: String(r.weighte_baskol ?? ''),
//       number_hamel: r.number_hamel ?? '', id_tagh_anbar: r.id_tagh_anbar,
//     })
//     setModalOpen(true)
//   }
//   const canSave = line.code_kala.trim() && line.number_kala.trim() &&
//                   line.weighte_asnad.trim() && line.weighte_baskol.trim()

//   return (
//     <div dir="rtl">
//       <Group justify="space-between" mb="md">
//         <Title order={2}>جزئیات قبض انبار #{headerId}</Title>
//         <Group>
//           <Button variant="light" onClick={() => navigate(`/ghabz/${headerId}/edit`)}>ویرایش سربرگ</Button>
//           <Button variant="subtle" onClick={() => navigate('/ghabz')}>بازگشت</Button>
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
//               <Table.Th>کد کالا</Table.Th><Table.Th>شرح</Table.Th><Table.Th>نوع بسته</Table.Th>
//               <Table.Th>تعداد</Table.Th><Table.Th>وزن اسناد</Table.Th><Table.Th>وزن باسکول</Table.Th>
//               <Table.Th>طاق</Table.Th><Table.Th>عملیات</Table.Th>
//             </Table.Tr></Table.Thead>
//             <Table.Tbody>
//               {lines.map((r) => (
//                 <Table.Tr key={r.id_ghabz_anbar_details}>
//                   <Table.Td>{r.code_kala}</Table.Td>
//                   <Table.Td>{r.description_kala ?? '—'}</Table.Td>
//                   <Table.Td>{r.type_basteh ?? '—'}</Table.Td>
//                   <Table.Td>{r.number_kala}</Table.Td>
//                   <Table.Td>{r.weighte_asnad}</Table.Td>
//                   <Table.Td>{r.weighte_baskol}</Table.Td>
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
//             <Grid.Col span={6}><TextInput label="نوع بسته‌بندی"
//               value={line.type_basteh} onChange={(e) => set('type_basteh', e.currentTarget.value)} /></Grid.Col>
//             <Grid.Col span={6}><TextInput label="تعداد" required inputMode="numeric"
//               value={line.number_kala} onChange={(e) => set('number_kala', e.currentTarget.value)} /></Grid.Col>
//             <Grid.Col span={6}><TextInput label="وزن اسناد" required inputMode="numeric"
//               value={line.weighte_asnad} onChange={(e) => set('weighte_asnad', e.currentTarget.value)} /></Grid.Col>
//             <Grid.Col span={6}><TextInput label="وزن باسکول" required inputMode="numeric"
//               value={line.weighte_baskol} onChange={(e) => set('weighte_baskol', e.currentTarget.value)} /></Grid.Col>
//             <Grid.Col span={6}><RefSelect label="طاق" path="/tagh" valueKey="id_tagh" labelKey="name_tagh"
//               value={line.id_tagh_anbar} onChange={(v) => set('id_tagh_anbar', v)} /></Grid.Col>
//             <Grid.Col span={6}><TextInput label="شماره حامل"
//               value={line.number_hamel} onChange={(e) => set('number_hamel', e.currentTarget.value)} /></Grid.Col>
//           </Grid>
//           <Group justify="flex-start" mt="md">
//             <Button onClick={() => saveMutation.mutate(line)} loading={saveMutation.isPending} disabled={!canSave}>ذخیره</Button>
//             <Button variant="subtle" onClick={() => setModalOpen(false)}>لغو</Button>
//           </Group>
//         </Stack>
//       </Modal>
//     </div>
//   )
// }

import { useState } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { BackButton } from '../components/BackButton'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import {
  Title, Button, Group, Table, Paper, Loader, Center, Text, Divider,
  Modal, TextInput, Grid, Stack,
} from '@mantine/core'
import { apiGet, apiSend } from '../api/client'
import { RefSelect } from '../components/RefSelect'
import { TermValueSelect } from '../components/TermValueSelect'
import { CommodityPicker, type Commodity } from '../components/CommodityPicker'

type DetailRow = {
  id_ghabz_anbar_details: number
  id_ghabz_anbar_headar: number
  code_kala: number
  code_kala_kantiner: number | null
  description_kala: string | null
  type_basteh: string | null
  number_kala: number
  number_kantiner: number | null
  weighte_asnad: number
  weighte_baskol: number
  number_hamel: string | null
  id_tagh_anbar: number | null
  tagh_name: string | null
}

type LineForm = {
  code_kala: string
  description_kala: string
  type_basteh: string
  number_kala: string
  weighte_asnad: string
  weighte_baskol: string
  number_hamel: string
  id_tagh_anbar: number | null
}

const EMPTY: LineForm = {
  code_kala: '', description_kala: '', type_basteh: '', number_kala: '',
  weighte_asnad: '', weighte_baskol: '', number_hamel: '', id_tagh_anbar: null,
}

function normalizeDigits(s: string): string {
  return s.replace(/[\u06F0-\u06F9]/g, (d) => String(d.charCodeAt(0) - 0x06f0))
          .replace(/[\u0660-\u0669]/g, (d) => String(d.charCodeAt(0) - 0x0660))
}

export function GhabzDetailPage() {
  const { id } = useParams<{ id: string }>()
  const headerId = Number(id)
  const navigate = useNavigate()
  const qc = useQueryClient()
  const [modalOpen, setModalOpen] = useState(false)
  const [editingId, setEditingId] = useState<number | null>(null)
  const [line, setLine] = useState<LineForm>(EMPTY)
  const [picked, setPicked] = useState<Commodity | null>(null)

  const { data: lines, isLoading } = useQuery({
    queryKey: ['ghabz-details', headerId],
    queryFn: () => apiGet<DetailRow[]>(`/ghabz/${headerId}/details`),
  })

  function toPayload(f: LineForm) {
    const numOrNull = (v: string) => (v.trim() === '' ? null : Number(normalizeDigits(v)))
    const strOrNull = (v: string) => (v.trim() === '' ? null : v)
    return {
      id_ghabz_anbar_headar: headerId,
      code_kala: Number(normalizeDigits(f.code_kala)),
      description_kala: strOrNull(f.description_kala),
      type_basteh: strOrNull(f.type_basteh),
      number_kala: Number(normalizeDigits(f.number_kala)),
      weighte_asnad: Number(normalizeDigits(f.weighte_asnad)),
      weighte_baskol: Number(normalizeDigits(f.weighte_baskol)),
      number_hamel: strOrNull(f.number_hamel),
      id_tagh_anbar: f.id_tagh_anbar,
    }
  }

  const saveMutation = useMutation({
    mutationFn: (f: LineForm) =>
      editingId == null
        ? apiSend('/ghabz-details', 'POST', toPayload(f))
        : apiSend(`/ghabz-details/${editingId}`, 'PUT', toPayload(f)),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ['ghabz-details', headerId] }); setModalOpen(false) },
  })
  const deleteMutation = useMutation({
    mutationFn: (lid: number) => apiSend(`/ghabz-details/${lid}`, 'DELETE'),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['ghabz-details', headerId] }),
  })

  const set = <K extends keyof LineForm>(k: K, v: LineForm[K]) => setLine((l) => ({ ...l, [k]: v }))

  // snapshot the description from the picked catalog commodity (ghabz lines carry no
  // hscode/unit/duty columns); code_kala (= storage group) is set by CommodityPicker.
  function onPickCommodity(c: Commodity | null) {
    setPicked(c)
    if (!c) return
    setLine((l) => ({ ...l, description_kala: c.description_fa ?? '' }))
  }

  function openAdd() { setEditingId(null); setLine(EMPTY); setPicked(null); setModalOpen(true) }
  function openEdit(r: DetailRow) {
    setEditingId(r.id_ghabz_anbar_details)
    setPicked(null)
    setLine({
      code_kala: String(r.code_kala ?? ''), description_kala: r.description_kala ?? '',
      type_basteh: r.type_basteh ?? '', number_kala: String(r.number_kala ?? ''),
      weighte_asnad: String(r.weighte_asnad ?? ''), weighte_baskol: String(r.weighte_baskol ?? ''),
      number_hamel: r.number_hamel ?? '', id_tagh_anbar: r.id_tagh_anbar,
    })
    setModalOpen(true)
  }
  const canSave = line.code_kala.trim() && line.number_kala.trim() &&
                  line.weighte_asnad.trim() && line.weighte_baskol.trim()

  return (
    <div dir="rtl">
      <Group justify="space-between" mb="md">
        <Title order={2}>جزئیات قبض انبار #{headerId}</Title>
        <Group>
          <Button variant="light" onClick={() => navigate(`/ghabz/${headerId}/edit`)}>ویرایش سربرگ</Button>
          <BackButton to="/ghabz" />
        </Group>
      </Group>
      <Paper shadow="xs" p="md">
        <Group justify="space-between" mb="sm">
          <Text fw={600}>ردیف‌های کالا</Text>
          <Button onClick={openAdd}>افزودن ردیف</Button>
        </Group>
        <Divider mb="sm" />
        {isLoading && <Center py="xl"><Loader /></Center>}
        {lines && lines.length === 0 && <Center py="xl"><Text c="dimmed">ردیفی ثبت نشده است.</Text></Center>}
        {lines && lines.length > 0 && (
          <Table striped withTableBorder>
            <Table.Thead><Table.Tr>
              <Table.Th>کد کالا</Table.Th><Table.Th>شرح</Table.Th><Table.Th>نوع بسته</Table.Th>
              <Table.Th>تعداد</Table.Th><Table.Th>وزن اسناد</Table.Th><Table.Th>وزن باسکول</Table.Th>
              <Table.Th>طاق</Table.Th><Table.Th>عملیات</Table.Th>
            </Table.Tr></Table.Thead>
            <Table.Tbody>
              {lines.map((r) => (
                <Table.Tr key={r.id_ghabz_anbar_details}>
                  <Table.Td>{r.code_kala}</Table.Td>
                  <Table.Td>{r.description_kala ?? '—'}</Table.Td>
                  <Table.Td>{r.type_basteh ?? '—'}</Table.Td>
                  <Table.Td>{r.number_kala}</Table.Td>
                  <Table.Td>{r.weighte_asnad}</Table.Td>
                  <Table.Td>{r.weighte_baskol}</Table.Td>
                  <Table.Td>{r.tagh_name ?? '—'}</Table.Td>
                  <Table.Td>
                    <Group gap="xs">
                      <Button size="xs" variant="light" onClick={() => openEdit(r)}>ویرایش</Button>
                      <Button size="xs" variant="light" color="red"
                        onClick={() => deleteMutation.mutate(r.id_ghabz_anbar_details)}>حذف</Button>
                    </Group>
                  </Table.Td>
                </Table.Tr>
              ))}
            </Table.Tbody>
          </Table>
        )}
      </Paper>
      <Modal opened={modalOpen} onClose={() => setModalOpen(false)}
        title={editingId == null ? 'افزودن ردیف' : 'ویرایش ردیف'} size="lg">
        <Stack>
          <CommodityPicker
            picked={picked}
            onPick={onPickCommodity}
            groupValue={line.code_kala.trim() === '' ? null : Number(line.code_kala)}
            onGroupChange={(v) => set('code_kala', v == null ? '' : String(v))}
          />
          <Divider />
          <Grid>
            <Grid.Col span={6}><TextInput label="شرح کالا"
              value={line.description_kala} onChange={(e) => set('description_kala', e.currentTarget.value)} /></Grid.Col>
            <Grid.Col span={6}><TermValueSelect label="نوع بسته‌بندی" categoryId={3}
              value={line.type_basteh || null} onChange={(value) => set('type_basteh', value ?? '')} /></Grid.Col>
            <Grid.Col span={6}><TextInput label="تعداد" required inputMode="numeric"
              value={line.number_kala} onChange={(e) => set('number_kala', e.currentTarget.value)} /></Grid.Col>
            <Grid.Col span={6}><TextInput label="وزن اسناد" required inputMode="numeric"
              value={line.weighte_asnad} onChange={(e) => set('weighte_asnad', e.currentTarget.value)} /></Grid.Col>
            <Grid.Col span={6}><TextInput label="وزن باسکول" required inputMode="numeric"
              value={line.weighte_baskol} onChange={(e) => set('weighte_baskol', e.currentTarget.value)} /></Grid.Col>
            <Grid.Col span={6}><RefSelect label="طاق" path="/tagh" valueKey="id_tagh" labelKey="name_tagh"
              value={line.id_tagh_anbar} onChange={(v) => set('id_tagh_anbar', v)} /></Grid.Col>
            <Grid.Col span={6}><TextInput label="شماره حامل"
              value={line.number_hamel} onChange={(e) => set('number_hamel', e.currentTarget.value)} /></Grid.Col>
          </Grid>
          <Group justify="flex-start" mt="md">
            <Button onClick={() => saveMutation.mutate(line)} loading={saveMutation.isPending} disabled={!canSave}>ذخیره</Button>
            <Button variant="subtle" onClick={() => setModalOpen(false)}>لغو</Button>
          </Group>
        </Stack>
      </Modal>
    </div>
  )
}
