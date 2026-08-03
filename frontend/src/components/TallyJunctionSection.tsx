// import { useState } from 'react'
// import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
// import {
//   Paper, Group, Text, Button, Divider, Table, Center, Loader, Modal, Stack, TextInput, Select,
// } from '@mantine/core'
// import { apiGet, apiSend } from '../api/client'
// import { RefSelect } from './RefSelect'

// /**
//  * TallyJunctionSection — one reusable rate-junction section, config-driven.
//  * Every rate junction (diamound, price, strip, ...) is the same shape, so this
//  * one component renders any of them from a config. See junctions.ts.
//  */

// export type JunctionConfig = {
//   key: string
//   title: string
//   apiPath: string
//   readPath: string
//   linkKey: string
//   catalogPath: string
//   catalogValueKey: string
//   catalogLabel: (r: Record<string, any>) => string
//   extraField?: { key: string; label: string }
//   // Optional per-row dropdown (e.g. strip's «نوع قیمت»). Generic: any junction can
//   // declare one. `defaultValue` is pre-selected on add so the stored value is explicit.
//   selectField?: {
//     key: string
//     label: string
//     options: { value: string; label: string }[]
//     defaultValue?: string
//   }
// }

// type JunctionRow = {
//   id: number
//   tali_id: number
//   rate_id: number | null
//   code: string | null
//   description: string | null
//   rate_code: string | null
//   rate_title: string | null
//   number_service?: number | null
//   pricing_type?: string | null
// }

// function normalizeDigits(s: string): string {
//   return s
//     .replace(/[\u06F0-\u06F9]/g, (d) => String(d.charCodeAt(0) - 0x06f0))
//     .replace(/[\u0660-\u0669]/g, (d) => String(d.charCodeAt(0) - 0x0660))
// }

// export function TallyJunctionSection({ config, tallyId }: { config: JunctionConfig; tallyId: number }) {
//   const qc = useQueryClient()
//   const [modalOpen, setModalOpen] = useState(false)
//   const [rateId, setRateId] = useState<number | null>(null)
//   const [snapCode, setSnapCode] = useState<string | null>(null)
//   const [description, setDescription] = useState('')
//   const [extraVal, setExtraVal] = useState('')
//   const [selectVal, setSelectVal] = useState<string | null>(config.selectField?.defaultValue ?? null)

//   const queryKey = ['tally-junction', config.key, tallyId]

//   const { data, isLoading, isError } = useQuery({
//     queryKey,
//     queryFn: () => apiGet<JunctionRow[]>(`/tally/${tallyId}/${config.readPath}`),
//   })

//   const createMutation = useMutation({
//     mutationFn: () => {
//       const payload: Record<string, unknown> = {
//         tali_id: tallyId,
//         [config.linkKey]: rateId,
//         code: snapCode,
//         description: description.trim() === '' ? null : description,
//       }
//       if (config.extraField) {
//         payload[config.extraField.key] =
//           extraVal.trim() === '' ? null : Number(normalizeDigits(extraVal))
//       }
//       if (config.selectField) {
//         payload[config.selectField.key] = selectVal
//       }
//       return apiSend(config.apiPath, 'POST', payload)
//     },
//     onSuccess: () => {
//       qc.invalidateQueries({ queryKey })
//       setModalOpen(false)
//       setRateId(null); setSnapCode(null); setDescription(''); setExtraVal('')
//       setSelectVal(config.selectField?.defaultValue ?? null)
//     },
//   })

//   const deleteMutation = useMutation({
//     mutationFn: (id: number) => apiSend(`${config.apiPath}/${id}`, 'DELETE'),
//     onSuccess: () => qc.invalidateQueries({ queryKey }),
//   })

//   return (
//     <Paper shadow="xs" p="md" mt="md">
//       <Group justify="space-between" mb="sm">
//         <Text fw={600}>{config.title}</Text>
//         <Button size="sm" onClick={() => setModalOpen(true)}>افزودن</Button>
//       </Group>
//       <Divider mb="sm" />

//       {isLoading && <Center py="md"><Loader size="sm" /></Center>}
//       {isError && <Center py="md"><Text c="red">خطا در بارگذاری.</Text></Center>}

//       {data && data.length === 0 && (
//         <Center py="md"><Text c="dimmed" size="sm">ردیفی ثبت نشده است.</Text></Center>
//       )}

//       {data && data.length > 0 && (
//         <Table striped withTableBorder>
//           <Table.Thead>
//             <Table.Tr>
//               <Table.Th>کد</Table.Th>
//               <Table.Th>عنوان</Table.Th>
//               {config.extraField && <Table.Th>{config.extraField.label}</Table.Th>}
//               {config.selectField && <Table.Th>{config.selectField.label}</Table.Th>}
//               <Table.Th>توضیحات</Table.Th>
//               <Table.Th>عملیات</Table.Th>
//             </Table.Tr>
//           </Table.Thead>
//           <Table.Tbody>
//             {data.map((row) => (
//               <Table.Tr key={row.id}>
//                 <Table.Td>{row.code ?? row.rate_code ?? '—'}</Table.Td>
//                 <Table.Td>{row.rate_title ?? '—'}</Table.Td>
//                 {config.extraField && <Table.Td>{row.number_service ?? '—'}</Table.Td>}
//                 {config.selectField && (
//                   <Table.Td>
//                     {config.selectField.options.find(
//                       (o) => o.value === (row as Record<string, any>)[config.selectField!.key],
//                     )?.label ?? '—'}
//                   </Table.Td>
//                 )}
//                 <Table.Td>{row.description ?? '—'}</Table.Td>
//                 <Table.Td>
//                   <Button size="xs" variant="light" color="red"
//                     onClick={() => deleteMutation.mutate(row.id)}>
//                     حذف
//                   </Button>
//                 </Table.Td>
//               </Table.Tr>
//             ))}
//           </Table.Tbody>
//         </Table>
//       )}

//       <Modal opened={modalOpen} onClose={() => setModalOpen(false)} title={`افزودن ${config.title}`}>
//         <Stack>
//           <RefSelect
//             label="انتخاب"
//             path={config.catalogPath}
//             valueKey={config.catalogValueKey}
//             labelKey={config.catalogLabel}
//             value={rateId}
//             onChange={setRateId}
//             onPick={(row) => setSnapCode(row?.code ?? null)}
//           />
//           {config.extraField && (
//             <TextInput
//               label={config.extraField.label}
//               inputMode="numeric"
//               value={extraVal}
//               onChange={(e) => setExtraVal(e.currentTarget.value)}
//             />
//           )}
//           {config.selectField && (
//             <Select
//               label={config.selectField.label}
//               data={config.selectField.options}
//               value={selectVal}
//               onChange={setSelectVal}
//               allowDeselect={false}
//             />
//           )}
//           <TextInput
//             label="توضیحات"
//             value={description}
//             onChange={(e) => setDescription(e.currentTarget.value)}
//           />
//           <Group justify="flex-start" mt="sm">
//             <Button onClick={() => createMutation.mutate()}
//               loading={createMutation.isPending} disabled={rateId == null}>
//               ذخیره
//             </Button>
//             <Button variant="subtle" onClick={() => setModalOpen(false)}>لغو</Button>
//           </Group>
//         </Stack>
//       </Modal>
//     </Paper>
//   )
// }

// import { useState } from 'react'
// import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
// import {
//   Paper, Group, Text, Button, Divider, Table, Center, Loader, Modal, Stack, TextInput,
// } from '@mantine/core'
// import { apiGet, apiSend } from '../api/client'
// import { RefSelect } from './RefSelect'

// /**
//  * TallyJunctionSection — one reusable rate-junction section, config-driven.
//  * Every rate junction (diamound, price, strip, ...) is the same shape, so this
//  * one component renders any of them from a config. See junctions.ts.
//  */

// export type JunctionConfig = {
//   key: string
//   title: string
//   apiPath: string
//   readPath: string
//   linkKey: string
//   catalogPath: string
//   catalogValueKey: string
//   catalogLabel: (r: Record<string, any>) => string
//   extraField?: { key: string; label: string }
// }

// type JunctionRow = {
//   id: number
//   tali_id: number
//   rate_id: number | null
//   code: string | null
//   description: string | null
//   rate_code: string | null
//   rate_title: string | null
//   number_service?: number | null
// }

// function normalizeDigits(s: string): string {
//   return s
//     .replace(/[\u06F0-\u06F9]/g, (d) => String(d.charCodeAt(0) - 0x06f0))
//     .replace(/[\u0660-\u0669]/g, (d) => String(d.charCodeAt(0) - 0x0660))
// }

// export function TallyJunctionSection({ config, tallyId }: { config: JunctionConfig; tallyId: number }) {
//   const qc = useQueryClient()
//   const [modalOpen, setModalOpen] = useState(false)
//   const [rateId, setRateId] = useState<number | null>(null)
//   const [snapCode, setSnapCode] = useState<string | null>(null)
//   const [description, setDescription] = useState('')
//   const [extraVal, setExtraVal] = useState('')

//   const queryKey = ['tally-junction', config.key, tallyId]

//   const { data, isLoading, isError } = useQuery({
//     queryKey,
//     queryFn: () => apiGet<JunctionRow[]>(`/tally/${tallyId}/${config.readPath}`),
//   })

//   const createMutation = useMutation({
//     mutationFn: () => {
//       const payload: Record<string, unknown> = {
//         tali_id: tallyId,
//         [config.linkKey]: rateId,
//         code: snapCode,
//         description: description.trim() === '' ? null : description,
//       }
//       if (config.extraField) {
//         payload[config.extraField.key] =
//           extraVal.trim() === '' ? null : Number(normalizeDigits(extraVal))
//       }
//       return apiSend(config.apiPath, 'POST', payload)
//     },
//     onSuccess: () => {
//       qc.invalidateQueries({ queryKey })
//       setModalOpen(false)
//       setRateId(null); setSnapCode(null); setDescription(''); setExtraVal('')
//     },
//   })

//   const deleteMutation = useMutation({
//     mutationFn: (id: number) => apiSend(`${config.apiPath}/${id}`, 'DELETE'),
//     onSuccess: () => qc.invalidateQueries({ queryKey }),
//   })

//   return (
//     <Paper shadow="xs" p="md" mt="md">
//       <Group justify="space-between" mb="sm">
//         <Text fw={600}>{config.title}</Text>
//         <Button size="sm" onClick={() => setModalOpen(true)}>افزودن</Button>
//       </Group>
//       <Divider mb="sm" />

//       {isLoading && <Center py="md"><Loader size="sm" /></Center>}
//       {isError && <Center py="md"><Text c="red">خطا در بارگذاری.</Text></Center>}

//       {data && data.length === 0 && (
//         <Center py="md"><Text c="dimmed" size="sm">ردیفی ثبت نشده است.</Text></Center>
//       )}

//       {data && data.length > 0 && (
//         <Table striped withTableBorder>
//           <Table.Thead>
//             <Table.Tr>
//               <Table.Th>کد</Table.Th>
//               <Table.Th>عنوان</Table.Th>
//               {config.extraField && <Table.Th>{config.extraField.label}</Table.Th>}
//               <Table.Th>توضیحات</Table.Th>
//               <Table.Th>عملیات</Table.Th>
//             </Table.Tr>
//           </Table.Thead>
//           <Table.Tbody>
//             {data.map((row) => (
//               <Table.Tr key={row.id}>
//                 <Table.Td>{row.code ?? row.rate_code ?? '—'}</Table.Td>
//                 <Table.Td>{row.rate_title ?? '—'}</Table.Td>
//                 {config.extraField && <Table.Td>{row.number_service ?? '—'}</Table.Td>}
//                 <Table.Td>{row.description ?? '—'}</Table.Td>
//                 <Table.Td>
//                   <Button size="xs" variant="light" color="red"
//                     onClick={() => deleteMutation.mutate(row.id)}>
//                     حذف
//                   </Button>
//                 </Table.Td>
//               </Table.Tr>
//             ))}
//           </Table.Tbody>
//         </Table>
//       )}

//       <Modal opened={modalOpen} onClose={() => setModalOpen(false)} title={`افزودن ${config.title}`}>
//         <Stack>
//           <RefSelect
//             label="انتخاب"
//             path={config.catalogPath}
//             valueKey={config.catalogValueKey}
//             labelKey={config.catalogLabel}
//             value={rateId}
//             onChange={setRateId}
//             onPick={(row) => setSnapCode(row?.code ?? null)}
//           />
//           {config.extraField && (
//             <TextInput
//               label={config.extraField.label}
//               inputMode="numeric"
//               value={extraVal}
//               onChange={(e) => setExtraVal(e.currentTarget.value)}
//             />
//           )}
//           <TextInput
//             label="توضیحات"
//             value={description}
//             onChange={(e) => setDescription(e.currentTarget.value)}
//           />
//           <Group justify="flex-start" mt="sm">
//             <Button onClick={() => createMutation.mutate()}
//               loading={createMutation.isPending} disabled={rateId == null}>
//               ذخیره
//             </Button>
//             <Button variant="subtle" onClick={() => setModalOpen(false)}>لغو</Button>
//           </Group>
//         </Stack>
//       </Modal>
//     </Paper>
//   )
// }

import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import {
  Paper, Group, Text, Button, Table, Center, Loader, Modal, Stack, TextInput, Select, Title,
  ActionIcon, Tooltip,
} from '@mantine/core'
import {
  Boxes,
  Clock3,
  Layers3,
  PackageSearch,
  Plus,
  ShieldAlert,
  Truck,
} from 'lucide-react'
import { apiGet, apiSend } from '../api/client'
import { RefSelect } from './RefSelect'
import { IconEdit, IconTrash } from './icons'

/**
 * TallyJunctionSection — one reusable service-junction section, config-driven.
 * Every service junction (diamound, price, strip, ...) is the same shape, so this
 * one component renders any of them from a config. See junctions.ts.
 *
 * Rows can be added, edited, and removed. A junction row is a service association
 * (which catalog item + optional description / quantity / pricing-type), so "edit" reopens
 * the same form pre-filled and updates those fields in place.
 */

export type JunctionConfig = {
  key: string
  title: string
  apiPath: string
  readPath: string
  linkKey: string
  catalogPath: string
  catalogValueKey: string
  catalogLabel: (r: Record<string, any>) => string
  extraField?: { key: string; label: string }
  // Optional per-row dropdown (e.g. strip's «نوع قیمت»). Generic: any junction can
  // declare one. `defaultValue` is pre-selected on add so the stored value is explicit.
  selectField?: {
    key: string
    label: string
    options: { value: string; label: string; catalogField?: string }[]
    defaultValue?: string
    inlineWithCatalog?: boolean
  }
}

type JunctionRow = {
  id: number
  tali_id: number
  rate_id: number | null
  code: string | null
  description: string | null
  rate_code: string | null
  rate_title: string | null
  number_service?: number | null
  pricing_type?: string | null
  selected_price?: string | number | null
}

function normalizeDigits(s: string): string {
  return s
    .replace(/[\u06F0-\u06F9]/g, (d) => String(d.charCodeAt(0) - 0x06f0))
    .replace(/[\u0660-\u0669]/g, (d) => String(d.charCodeAt(0) - 0x0660))
}

export function TallyJunctionSection({ config, tallyId }: { config: JunctionConfig; tallyId: number }) {
  const qc = useQueryClient()
  const [modalOpen, setModalOpen] = useState(false)
  const [editingId, setEditingId] = useState<number | null>(null)
  const [rateId, setRateId] = useState<number | null>(null)
  const [snapCode, setSnapCode] = useState<string | null>(null)
  const [description, setDescription] = useState('')
  const [extraVal, setExtraVal] = useState('')
  const [selectVal, setSelectVal] = useState<string | null>(config.selectField?.defaultValue ?? null)

  const queryKey = ['tally-junction', config.key, tallyId]

  const { data, isLoading, isError } = useQuery({
    queryKey,
    queryFn: () => apiGet<JunctionRow[]>(`/tally/${tallyId}/${config.readPath}`),
  })

  function resetForm() {
    setEditingId(null)
    setRateId(null); setSnapCode(null); setDescription(''); setExtraVal('')
    setSelectVal(config.selectField?.defaultValue ?? null)
  }

  function openAdd() {
    resetForm()
    setModalOpen(true)
  }

  function openEdit(row: JunctionRow) {
    setEditingId(row.id)
    setRateId(row.rate_id)
    setSnapCode(row.code)
    setDescription(row.description ?? '')
    setExtraVal(row.number_service != null ? String(row.number_service) : '')
    setSelectVal(
      config.selectField
        ? ((row as Record<string, any>)[config.selectField.key] ?? config.selectField.defaultValue ?? null)
        : null,
    )
    setModalOpen(true)
  }

  const saveMutation = useMutation({
    mutationFn: () => {
      const payload: Record<string, unknown> = {
        tali_id: tallyId,
        [config.linkKey]: rateId,
        code: snapCode,
        description: description.trim() === '' ? null : description,
      }
      if (config.extraField) {
        payload[config.extraField.key] =
          extraVal.trim() === '' ? null : Number(normalizeDigits(extraVal))
      }
      if (config.selectField) {
        payload[config.selectField.key] = selectVal
      }
      return editingId == null
        ? apiSend(config.apiPath, 'POST', payload)
        : apiSend(`${config.apiPath}/${editingId}`, 'PUT', payload)
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey })
      setModalOpen(false)
      resetForm()
    },
    onError: (e) => alert(`ذخیره ناموفق بود: ${(e as Error).message}`),
  })

  const deleteMutation = useMutation({
    mutationFn: (id: number) => apiSend(`${config.apiPath}/${id}`, 'DELETE'),
    onSuccess: () => qc.invalidateQueries({ queryKey }),
    onError: (e) => alert(`حذف ناموفق بود: ${(e as Error).message}`),
  })

  const SectionIcon = {
    diamound: Clock3,
    strip: Boxes,
    'other-service': PackageSearch,
    'time-stop': Clock3,
    'vehicle-enter': Truck,
    dangerous: ShieldAlert,
  }[config.key] ?? Layers3

  return (
    <Paper className="tally-detail-section tally-detail-junction-section" radius="xl">
      <div className="tally-detail-section-header">
        <div className="tally-detail-section-heading">
          <span className="tally-detail-section-icon" aria-hidden>
            <SectionIcon size={22} strokeWidth={1.8} />
          </span>
          <div>
            <Title order={3}>{config.title}</Title>
            <Text>ثبت و مدیریت خدمات مرتبط با این تالی</Text>
          </div>
        </div>
        <Button
          className="tally-detail-add-button"
          size="sm"
          leftSection={<Plus size={17} />}
          onClick={openAdd}
        >
          افزودن
        </Button>
      </div>
      <div className="tally-detail-section-rule" />

      {isLoading && (
        <Center className="tally-detail-state">
          <Loader size="sm" />
          <Text>در حال بارگذاری...</Text>
        </Center>
      )}
      {isError && (
        <Center className="tally-detail-state tally-detail-state-error">
          <Text>خطا در بارگذاری.</Text>
        </Center>
      )}

      {data && data.length === 0 && (
        <Center className="tally-detail-empty-state tally-detail-empty-state-compact">
          <SectionIcon size={25} strokeWidth={1.6} aria-hidden />
          <Text fw={700}>هنوز ردیفی ثبت نشده است.</Text>
          <Text size="sm">برای این بخش می‌توانید مورد جدید اضافه کنید.</Text>
        </Center>
      )}

      {data && data.length > 0 && (
        <div className="tally-detail-table-shell">
          <Table.ScrollContainer minWidth={620}>
            <Table
              className="tally-detail-table"
              highlightOnHover
              verticalSpacing="md"
              horizontalSpacing="md"
              withRowBorders
            >
              <Table.Thead>
                <Table.Tr>
                  <Table.Th>کد</Table.Th>
                  <Table.Th>عنوان</Table.Th>
                  {config.extraField && <Table.Th>{config.extraField.label}</Table.Th>}
                  {config.selectField && <Table.Th>{config.selectField.label}</Table.Th>}
                  {config.selectField?.inlineWithCatalog && <Table.Th>مبلغ</Table.Th>}
                  <Table.Th>توضیحات</Table.Th>
                  <Table.Th className="tally-detail-actions-cell">عملیات</Table.Th>
                </Table.Tr>
              </Table.Thead>
              <Table.Tbody>
                {data.map((row) => (
                  <Table.Tr key={row.id}>
                    <Table.Td>{row.code ?? row.rate_code ?? '—'}</Table.Td>
                    <Table.Td className="tally-detail-primary-cell">{row.rate_title ?? '—'}</Table.Td>
                    {config.extraField && <Table.Td>{row.number_service ?? '—'}</Table.Td>}
                    {config.selectField && (
                      <Table.Td>
                        {config.selectField.options.find(
                          (o) => o.value === (row as Record<string, any>)[config.selectField!.key],
                        )?.label ?? '—'}
                      </Table.Td>
                    )}
                    {config.selectField?.inlineWithCatalog && (
                      <Table.Td>
                        {row.selected_price == null
                          ? '—'
                          : `${Number(row.selected_price).toLocaleString('fa-IR')} ریال`}
                      </Table.Td>
                    )}
                    <Table.Td>{row.description ?? '—'}</Table.Td>
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
                            onClick={() => confirm('حذف این ردیف؟') && deleteMutation.mutate(row.id)}
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

      <Modal opened={modalOpen} onClose={() => setModalOpen(false)}
        title={`${editingId == null ? 'افزودن' : 'ویرایش'} ${config.title}`}
        radius="lg" centered overlayProps={{ backgroundOpacity: 0.55, blur: 2 }}
        classNames={{
          content: 'tally-detail-modal',
          header: 'tally-detail-modal-header',
          title: 'tally-detail-modal-title',
        }}>
        <Stack>
          <RefSelect
            label={`انتخاب ${config.title}`}
            path={config.catalogPath}
            valueKey={config.catalogValueKey}
            labelKey={config.catalogLabel}
            value={rateId}
            onChange={setRateId}
            onPick={(row) => setSnapCode(row?.code ?? null)}
            variantOptions={
              config.selectField?.inlineWithCatalog
                ? config.selectField.options.map((option) => ({
                    value: option.value,
                    label: option.label,
                    field: option.catalogField,
                  }))
                : undefined
            }
            variantValue={config.selectField?.inlineWithCatalog ? selectVal : undefined}
            onVariantChange={config.selectField?.inlineWithCatalog ? setSelectVal : undefined}
          />
          {config.extraField && (
            <TextInput
              label={config.extraField.label}
              inputMode="numeric"
              value={extraVal}
              onChange={(e) => setExtraVal(e.currentTarget.value)}
            />
          )}
          {config.selectField && !config.selectField.inlineWithCatalog && (
            <Select
              label={config.selectField.label}
              data={config.selectField.options}
              value={selectVal}
              onChange={setSelectVal}
              allowDeselect={false}
            />
          )}
          <TextInput
            label="توضیحات"
            value={description}
            onChange={(e) => setDescription(e.currentTarget.value)}
          />
          <Group justify="flex-start" mt="sm">
            <Button className="tally-detail-save-button" onClick={() => saveMutation.mutate()}
              loading={saveMutation.isPending}>
              ذخیره
            </Button>
            <Button variant="default" onClick={() => setModalOpen(false)}>لغو</Button>
          </Group>
        </Stack>
      </Modal>
    </Paper>
  )
}
