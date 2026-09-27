// import type { CSSProperties } from 'react'
// import { useQuery } from '@tanstack/react-query'
// import { useNavigate } from 'react-router-dom'
// import {
//   ActionIcon, Badge, Button, Center, Group, Loader, Menu, Paper, Table, Text,
// } from '@mantine/core'
// import { toJalaali } from 'jalaali-js'
// import { apiGet } from '../api/client'
// import { PageHeader } from '../components/PageHeader'
// import { BackButton } from '../components/BackButton'
// import { TallyNumber } from '../components/TallyNumber'
// import { modules } from '../modules'
// import {
//   IconClipboardList, IconDots, IconInvoice, IconReceipt, IconRefresh,
// } from '../components/icons'

// /**
//  * KartablPage — the cross-module worklist (کارتابل). One row per active tally,
//  * the whole row tinted by the same workflow status the tally list computes
//  * (open = tally only, pending = has a receipt, closed = invoiced), with a
//  * per-row عملیات menu that jumps to that tally's own تالی / قبض انبار /
//  * صورتحساب.
//  */

// // one row as returned by GET /kartabl/list
// type KartablRow = {
//   id_tali: number
//   tali_number: string | null
//   kala_description: string | null
//   owner_name: string | null
//   company_name: string | null
//   representative_name: string | null
//   date_unloading: string | null // ISO
//   workflow_status: 'open' | 'pending' | 'closed'
//   receipts: string | null // LISTAGG payload: "id|number,id|number"
//   invoice_id: number | null
// }

// // const STATUS = {
// //   open: { color: 'blue', accent: '#1971c2', label: 'تالی' },
// //   pending: { color: 'green', accent: '#10af7f', label: 'قبض انبار' },
// //   closed: { color: 'red', accent: '#e03131', label: 'صورتحساب' },
// // } as const
// const STATUS = {
//   open: { color: 'blue', accent: '#1971c2', label: 'تالی' },
//   pending: { color: 'green', accent: '#10af7f', label: 'قبض انبار' },
//   closed: { color: 'red', accent: '#e03131', label: 'صورتحساب' },
// } as const

// type Receipt = { id: number; number: string }

// // "12|1405_3_1,15|1405_3_2" -> [{ id: 12, number: '1405_3_1' }, ...]. Both
// // parts are digits/underscores only, so the two separators are unambiguous.
// function parseReceipts(raw: string | null): Receipt[] {
//   if (!raw) return []
//   return raw.split(',').flatMap((pair) => {
//     const [id, number] = pair.split('|')
//     const parsed = Number(id)
//     return Number.isFinite(parsed) ? [{ id: parsed, number: number || String(parsed) }] : []
//   })
// }

// // Same routing rule as the tally list: prefer the business number, fall back
// // to the surrogate id for legacy rows that were never numbered.
// function tallyPath(row: KartablRow): string {
//   if (row.tali_number) {
//     return `/tally/${encodeURIComponent(row.tali_number)}`
//   }
//   return `/tally/id/${row.id_tali}`
// }

// // ISO "2026-06-26" -> Jalali display "1405/04/05". Blank if empty.
// function isoToJalali(iso: string | null): string {
//   if (!iso) return '—'
//   const [gy, gm, gd] = iso.slice(0, 10).split('-').map(Number)
//   if (!gy || !gm || !gd) return '—'
//   const { jy, jm, jd } = toJalaali(gy, gm, gd)
//   const pad = (n: number) => String(n).padStart(2, '0')
//   return `${jy}/${pad(jm)}/${pad(jd)}`
// }

// function RowActions({ row }: { row: KartablRow }) {
//   const navigate = useNavigate()
//   const receipts = parseReceipts(row.receipts)
//   const status = STATUS[row.workflow_status] ?? STATUS.open

//   // The invoice frontend is not built yet: the menu item follows the module's
//   // enabled flag in modules.tsx, so flipping that flag activates it here too.
//   // The target is the future preview→save flow for this tally.
//   const invoiceEnabled = modules.find((m) => m.key === 'invoice')?.enabled !== false

//   return (
//     <Menu shadow="md" width={230} position="bottom-end" withinPortal>
//       <Menu.Target>
//         <ActionIcon
//           variant="subtle" color={status.color} radius="md"
//           onClick={(e) => e.stopPropagation()}
//           aria-label="عملیات"
//         >
//           <IconDots size={18} stroke={2.6} />
//         </ActionIcon>
//       </Menu.Target>
//       <Menu.Dropdown>
//         <Menu.Item
//           leftSection={<IconClipboardList size={16} />}
//           onClick={() => navigate(tallyPath(row))}
//         >
//           تالی
//         </Menu.Item>

//         {receipts.length === 0 && (
//           <Menu.Item leftSection={<IconReceipt size={16} />} disabled>
//             قبض انبار (صادر نشده)
//           </Menu.Item>
//         )}
//         {receipts.length === 1 && (
//           <Menu.Item
//             leftSection={<IconReceipt size={16} />}
//             onClick={() => navigate(`/ghabz/${receipts[0].id}`)}
//           >
//             قبض انبار
//           </Menu.Item>
//         )}
//         {receipts.length > 1 && (
//           <>
//             <Menu.Label>قبض انبار</Menu.Label>
//             {receipts.map((r) => (
//               <Menu.Item
//                 key={r.id}
//                 leftSection={<IconReceipt size={16} />}
//                 onClick={() => navigate(`/ghabz/${r.id}`)}
//               >
//                 <bdi dir="ltr">{r.number}</bdi>
//               </Menu.Item>
//             ))}
//           </>
//         )}

//         <Menu.Item
//           leftSection={<IconInvoice size={16} />}
//           disabled={!invoiceEnabled}
//           rightSection={!invoiceEnabled
//             ? <Badge size="xs" variant="light" color="gray">به‌زودی</Badge>
//             : undefined}
//           onClick={() => navigate(`/invoice/from-tally/${row.id_tali}`)}
//         >
//           صورتحساب
//         </Menu.Item>
//       </Menu.Dropdown>
//     </Menu>
//   )
// }

// export function KartablPage() {
//   const navigate = useNavigate()

//   const { data, isLoading, isError, refetch, isFetching } = useQuery({
//     queryKey: ['kartabl-list'],
//     queryFn: () => apiGet<KartablRow[]>('/kartabl/list'),
//   })

//   return (
//     <div dir="rtl">
//       <style>{`
//         .kt-row {
//           background: linear-gradient(90deg, var(--kt-bg-strong), var(--kt-bg));
//           cursor: pointer;
//           transition: background 150ms ease;
//         }

//         .kt-row:hover {
//           background: linear-gradient(
//             90deg,
//             var(--kt-bg-hover-strong),
//             var(--kt-bg-hover)
//           );
//         }

//         .kt-row td {
//           border-top: 1.5px solid var(--kt-accent);
//           border-bottom: 1.5px solid var(--kt-accent);
//         }

//         .kt-row td:first-child {
//           border-inline-start: 7px solid var(--kt-accent);
//         }

//         .kt-row td:last-child {
//           border-inline-end: 2px solid var(--kt-accent);
//         }

//         .kt-table-header th {
//           background: #1E3A5F;
//           color: #FFFFFF;
//           border-color: #315579;
//           font-weight: 800;
//         }
//       `}</style>

//       <PageHeader
//         title="کارتابل"
//         subtitle="پیگیری پرونده‌ها از تالی تا صورتحساب"
//         actions={
//           <>
//             <Button
//               variant="default" radius="md" leftSection={<IconRefresh size={18} />}
//               onClick={() => refetch()} loading={isFetching && !isLoading}
//             >
//               بروزرسانی
//             </Button>
//             <BackButton to="/" />
//           </>
//         }
//       />

//       {/* colour legend: what each row tint means, mirroring the tally badges */}
//       <Group gap="lg" mb="md" px="xs">
//         {(Object.keys(STATUS) as (keyof typeof STATUS)[]).map((key) => (
//           <Group key={key} gap={6} wrap="nowrap">
//             <span
//               aria-hidden
//               style={{
//                 width: 12, height: 12, borderRadius: 4,
//                 background: STATUS[key].accent,
//                 boxShadow: `0 0 0 1px ${STATUS[key].accent}`,
//               }}
//             />
//             <Text size="sm" c="dimmed">{STATUS[key].label}</Text>
//           </Group>
//         ))}
//       </Group>

//       <Paper shadow="xs" p="md">
//         {isLoading && <Center py="xl"><Loader /></Center>}
//         {isError && <Center py="xl"><Text c="red">خطا در بارگذاری کارتابل.</Text></Center>}
//         {data && data.length === 0 && (
//           <Center py="xl"><Text c="dimmed">هنوز پرونده‌ای ثبت نشده است.</Text></Center>
//         )}
//         {data && data.length > 0 && (
//           <Table.ScrollContainer minWidth={860}>
//             <Table highlightOnHover={false} withTableBorder verticalSpacing="sm">
//               <Table.Thead className="kt-table-header">
//                 <Table.Tr>
//                   <Table.Th>شماره تالی</Table.Th>
//                   <Table.Th>شرح کالا</Table.Th>
//                   <Table.Th>صاحب کالا</Table.Th>
//                   <Table.Th>شرکت حمل</Table.Th>
//                   <Table.Th>نماینده شرکت حمل</Table.Th>
//                   <Table.Th>تاریخ تخلیه</Table.Th>
//                   <Table.Th style={{ textAlign: 'center' }}>عملیات</Table.Th>
//                 </Table.Tr>
//               </Table.Thead>
//               <Table.Tbody>
//                 {data.map((row) => {
//                   const status = STATUS[row.workflow_status] ?? STATUS.open
//                   const c = status.color
//                   return (
//                     <Table.Tr
//                       key={row.id_tali}
//                       className="kt-row"
//                       style={{
//                         '--kt-accent': status.accent,
//                         '--kt-bg': `color-mix(in srgb, ${status.accent} 19%, white)`,
//                         '--kt-bg-strong': `color-mix(in srgb, ${status.accent} 25%, white)`,
//                         '--kt-bg-hover': `color-mix(in srgb, ${status.accent} 28%, white)`,
//                         '--kt-bg-hover-strong': `color-mix(in srgb, ${status.accent} 36%, white)`,
//                       } as CSSProperties}
//                       onClick={() => navigate(tallyPath(row))}
//                     >
//                       <Table.Td>
//                         <Text fw={700} c={`${c}.8`}>
//                           <TallyNumber value={row.tali_number} />
//                         </Text>
//                       </Table.Td>
//                       <Table.Td>
//                         <Text size="sm" lineClamp={2}>{row.kala_description?.trim() || '—'}</Text>
//                       </Table.Td>
//                       <Table.Td>{row.owner_name?.trim() || '—'}</Table.Td>
//                       <Table.Td>{row.company_name?.trim() || '—'}</Table.Td>
//                       <Table.Td>{row.representative_name?.trim() || '—'}</Table.Td>
//                       <Table.Td>{isoToJalali(row.date_unloading)}</Table.Td>
//                       <Table.Td style={{ textAlign: 'center' }} onClick={(e) => e.stopPropagation()}>
//                         <RowActions row={row} />
//                       </Table.Td>
//                     </Table.Tr>
//                   )
//                 })}
//               </Table.Tbody>
//             </Table>
//           </Table.ScrollContainer>
//         )}
//       </Paper>

//       {data && data.length > 0 && (
//         <Text size="xs" c="dimmed" mt="sm" ta="center">
//           {data.length.toLocaleString('fa-IR')} پرونده
//         </Text>
//       )}
//     </div>
//   )
// }


import type { CSSProperties } from 'react'
import { useQuery } from '@tanstack/react-query'
import { useNavigate, useSearchParams } from 'react-router-dom'
import {
  ActionIcon, Badge, Button, Center, Group, Loader, Menu, Paper, Table, Text,
} from '@mantine/core'
import { toJalaali } from 'jalaali-js'
import { apiGet } from '../api/client'
import { PageHeader } from '../components/PageHeader'
import { BackButton } from '../components/BackButton'
import { TallyNumber } from '../components/TallyNumber'
import { modules } from '../modules'
import { usePermissions } from '../auth/usePermissions'
import { ReceiptKeeperQueue } from '../components/ReceiptWorkflow'
import {
  IconClipboardList, IconDots, IconInvoice, IconReceipt, IconRefresh,
} from '../components/icons'

/**
 * KartablPage — the cross-module worklist (کارتابل). One row per active tally,
 * the whole row tinted by the same workflow status the tally list computes
 * (open = tally only, pending = has a receipt, closed = invoiced), with a
 * per-row عملیات menu that jumps to that tally's own تالی / قبض انبار /
 * صورتحساب.
 */

// one row as returned by GET /kartabl/list
type KartablRow = {
  id_tali: number
  tali_number: string | null
  kala_description: string | null
  owner_name: string | null
  company_name: string | null
  representative_name: string | null
  date_unloading: string | null // ISO
  workflow_status: 'open' | 'pending' | 'closed'
  handoff_step: 'operator' | 'keeper' | 'returned'
  receipts: string | null // LISTAGG payload: "id|number,id|number"
  invoice_id: number | null
}

// const STATUS = {
//   open: { color: 'blue', accent: '#1971c2', label: 'تالی' },
//   pending: { color: 'green', accent: '#10af7f', label: 'قبض انبار' },
//   closed: { color: 'red', accent: '#e03131', label: 'صورتحساب' },
// } as const
const STATUS = {
  open: { color: 'blue', accent: '#1971c2', label: 'تالی' },
  pending: { color: 'green', accent: '#10af7f', label: 'قبض انبار' },
  closed: { color: 'red', accent: '#e03131', label: 'صورتحساب' },
} as const

type Receipt = { id: number; number: string }

// "12|1405_3_1,15|1405_3_2" -> [{ id: 12, number: '1405_3_1' }, ...]. Both
// parts are digits/underscores only, so the two separators are unambiguous.
function parseReceipts(raw: string | null): Receipt[] {
  if (!raw) return []
  return raw.split(',').flatMap((pair) => {
    const [id, number] = pair.split('|')
    const parsed = Number(id)
    return Number.isFinite(parsed) ? [{ id: parsed, number: number || String(parsed) }] : []
  })
}

// Same routing rule as the tally list: prefer the business number, fall back
// to the surrogate id for legacy rows that were never numbered.
function tallyPath(row: KartablRow): string {
  if (row.tali_number) {
    return `/tally/${encodeURIComponent(row.tali_number)}`
  }
  return `/tally/id/${row.id_tali}`
}

// ISO "2026-06-26" -> Jalali display "1405/04/05". Blank if empty.
function isoToJalali(iso: string | null): string {
  if (!iso) return '—'
  const [gy, gm, gd] = iso.slice(0, 10).split('-').map(Number)
  if (!gy || !gm || !gd) return '—'
  const { jy, jm, jd } = toJalaali(gy, gm, gd)
  const pad = (n: number) => String(n).padStart(2, '0')
  return `${jy}/${pad(jm)}/${pad(jd)}`
}

function RowActions({ row }: { row: KartablRow }) {
  const navigate = useNavigate()
  const { can } = usePermissions()
  const receipts = parseReceipts(row.receipts)
  const status = STATUS[row.workflow_status] ?? STATUS.open

  // Saved invoices can be opened; generating a new invoice is not yet available.
  const invoiceEnabled = modules.find((m) => m.key === 'invoice')?.enabled !== false && row.invoice_id != null
  const canTally = can('tally.view')
  const canGhabz = can('ghabz.view')
  const canInvoice = can('invoice.view')
  if (!canTally && !canGhabz && !canInvoice) return null

  return (
    <Menu shadow="md" width={230} position="bottom-end" withinPortal>
      <Menu.Target>
        <ActionIcon
          variant="subtle" color={status.color} radius="md"
          onClick={(e) => e.stopPropagation()}
          aria-label="عملیات"
        >
          <IconDots size={18} stroke={2.6} />
        </ActionIcon>
      </Menu.Target>
      <Menu.Dropdown>
        {canTally && (
          <Menu.Item
            leftSection={<IconClipboardList size={16} />}
            onClick={() => navigate(tallyPath(row))}
          >
            تالی
          </Menu.Item>
        )}

        {canGhabz && receipts.length === 0 && (
          <Menu.Item leftSection={<IconReceipt size={16} />} disabled>
            قبض انبار (صادر نشده)
          </Menu.Item>
        )}
        {canGhabz && receipts.length === 1 && (
          <Menu.Item
            leftSection={<IconReceipt size={16} />}
            onClick={() => navigate(`/ghabz/${receipts[0].id}`)}
          >
            قبض انبار
          </Menu.Item>
        )}
        {canGhabz && receipts.length > 1 && (
          <>
            <Menu.Label>قبض انبار</Menu.Label>
            {receipts.map((r) => (
              <Menu.Item
                key={r.id}
                leftSection={<IconReceipt size={16} />}
                onClick={() => navigate(`/ghabz/${r.id}`)}
              >
                <bdi dir="ltr">{r.number}</bdi>
              </Menu.Item>
            ))}
          </>
        )}

        {canInvoice && (
          <Menu.Item
            leftSection={<IconInvoice size={16} />}
            disabled={!invoiceEnabled}
            rightSection={!invoiceEnabled
              ? <Badge size="xs" variant="light" color="gray">به‌زودی</Badge>
              : undefined}
            onClick={() => navigate(`/invoice/${row.invoice_id}`)}
          >
            صورتحساب
          </Menu.Item>
        )}
      </Menu.Dropdown>
    </Menu>
  )
}

export function KartablPage() {
  const navigate = useNavigate()
  const canTally = usePermissions().can('tally.view')
  const [params, setParams] = useSearchParams()
  const onlyWaiting = params.get('waiting') === '1'

  const { data, isLoading, isError, refetch, isFetching } = useQuery({
    queryKey: ['kartabl-list'],
    queryFn: () => apiGet<KartablRow[]>('/kartabl/list'),
    refetchInterval: 20000,
  })

  // The bell links here with ?waiting=1, so a keeper lands on their own queue.
  const waiting = (data ?? []).filter((row) => row.handoff_step === 'keeper')
  const rows = onlyWaiting ? waiting : data

  return (
    <div dir="rtl">
      <style>{`
        .kt-row {
          background: linear-gradient(90deg, var(--kt-bg-strong), var(--kt-bg));
          cursor: pointer;
          transition: background 150ms ease;
        }

        .kt-row:hover {
          background: linear-gradient(
            90deg,
            var(--kt-bg-hover-strong),
            var(--kt-bg-hover)
          );
        }

        .kt-row td {
          border-top: 1.5px solid var(--kt-accent);
          border-bottom: 1.5px solid var(--kt-accent);
        }

        .kt-row td:first-child {
          border-inline-start: 7px solid var(--kt-accent);
        }

        .kt-row td:last-child {
          border-inline-end: 2px solid var(--kt-accent);
        }

        .kt-table-header th {
          background: #1E3A5F;
          color: #FFFFFF;
          border-color: #315579;
          font-weight: 800;
        }
      `}</style>

      <ReceiptKeeperQueue />
      <PageHeader
        title="کارتابل"
        subtitle="پیگیری پرونده‌ها از تالی تا صورتحساب"
        actions={
          <>
            {waiting.length > 0 && (
              <Button
                variant="filled" color="orange" radius="md" fw={800}
                style={{ boxShadow: '0 3px 8px rgba(229, 115, 0, 0.28)' }}
                onClick={() => setParams(onlyWaiting ? {} : { waiting: '1' }, { replace: true })}
              >
                {onlyWaiting
                  ? 'نمایش همه'
                  : `فقط در انتظار انباردار (${waiting.length.toLocaleString('fa-IR')})`}
              </Button>
            )}
            <Button
              variant="default" radius="md" leftSection={<IconRefresh size={18} />}
              onClick={() => refetch()} loading={isFetching && !isLoading}
            >
              بروزرسانی
            </Button>
            <BackButton to="/" />
          </>
        }
      />

      {/* colour legend: what each row tint means, mirroring the tally badges */}
      <Group gap="lg" mb="md" px="xs">
        {(Object.keys(STATUS) as (keyof typeof STATUS)[]).map((key) => (
          <Group key={key} gap={6} wrap="nowrap">
            <span
              aria-hidden
              style={{
                width: 12, height: 12, borderRadius: 4,
                background: STATUS[key].accent,
                boxShadow: `0 0 0 1px ${STATUS[key].accent}`,
              }}
            />
            <Text size="sm" c="dimmed">{STATUS[key].label}</Text>
          </Group>
        ))}
      </Group>

      <Paper shadow="xs" p="md">
        {isLoading && <Center py="xl"><Loader /></Center>}
        {isError && <Center py="xl"><Text c="red">خطا در بارگذاری کارتابل.</Text></Center>}
        {rows && rows.length === 0 && (
          <Center py="xl">
            <Text c="dimmed">
              {onlyWaiting ? 'تالی در انتظار انباردار نیست.' : 'هنوز پرونده‌ای ثبت نشده است.'}
            </Text>
          </Center>
        )}
        {rows && rows.length > 0 && (
          <Table.ScrollContainer minWidth={860}>
            <Table highlightOnHover={false} withTableBorder verticalSpacing="sm">
              <Table.Thead className="kt-table-header">
                <Table.Tr>
                  <Table.Th>شماره تالی</Table.Th>
                  <Table.Th>شرح کالا</Table.Th>
                  <Table.Th>صاحب کالا</Table.Th>
                  <Table.Th>شرکت حمل</Table.Th>
                  <Table.Th>نماینده شرکت حمل</Table.Th>
                  <Table.Th>تاریخ تخلیه</Table.Th>
                  <Table.Th style={{ textAlign: 'center' }}>عملیات</Table.Th>
                </Table.Tr>
              </Table.Thead>
              <Table.Tbody>
                {rows.map((row) => {
                  const status = STATUS[row.workflow_status] ?? STATUS.open
                  const c = status.color
                  return (
                    <Table.Tr
                      key={row.id_tali}
                      className="kt-row"
                      style={{
                        '--kt-accent': status.accent,
                        '--kt-bg': `color-mix(in srgb, ${status.accent} 19%, white)`,
                        '--kt-bg-strong': `color-mix(in srgb, ${status.accent} 25%, white)`,
                        '--kt-bg-hover': `color-mix(in srgb, ${status.accent} 28%, white)`,
                        '--kt-bg-hover-strong': `color-mix(in srgb, ${status.accent} 36%, white)`,
                      } as CSSProperties}
                      onClick={canTally ? () => navigate(tallyPath(row)) : undefined}
                    >
                      <Table.Td>
                        <Text fw={700} c={`${c}.8`}>
                          <TallyNumber value={row.tali_number} />
                        </Text>
                        {row.handoff_step === 'keeper' && (
                          <Badge color="orange" variant="light" radius="sm" size="xs" mt={4}>
                            در انتظار انباردار
                          </Badge>
                        )}
                      </Table.Td>
                      <Table.Td>
                        <Text size="sm" lineClamp={2}>{row.kala_description?.trim() || '—'}</Text>
                      </Table.Td>
                      <Table.Td>{row.owner_name?.trim() || '—'}</Table.Td>
                      <Table.Td>{row.company_name?.trim() || '—'}</Table.Td>
                      <Table.Td>{row.representative_name?.trim() || '—'}</Table.Td>
                      <Table.Td>{isoToJalali(row.date_unloading)}</Table.Td>
                      <Table.Td style={{ textAlign: 'center' }} onClick={(e) => e.stopPropagation()}>
                        <RowActions row={row} />
                      </Table.Td>
                    </Table.Tr>
                  )
                })}
              </Table.Tbody>
            </Table>
          </Table.ScrollContainer>
        )}
      </Paper>

      {data && data.length > 0 && (
        <Text size="xs" c="dimmed" mt="sm" ta="center">
          {data.length.toLocaleString('fa-IR')} پرونده
        </Text>
      )}
    </div>
  )
}
