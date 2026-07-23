// import { useQuery } from '@tanstack/react-query'
// import { useNavigate } from 'react-router-dom'
// import { Title, Button, Group, Table, Paper, Loader, Center, Text } from '@mantine/core'
// import { toJalaali } from 'jalaali-js'
// import { apiGet } from '../api/client'

// /**
//  * TallyListPage — the list of tallies (لیست تالی‌ها), the entry point to the
//  * tally module. Reads from /tally-list (the JOIN endpoint) so the border,
//  * country, company, and owner columns show names instead of raw ids.
//  *
//  * "افزودن تالی" opens the header form; clicking a row opens it for edit (edit
//  * wiring comes with the detail view next).
//  */

// // one row as returned by GET /tally-list (names already resolved by the JOIN)
// type TallyRow = {
//   id_tali: number
//   tali_number: number | null
//   radef_marze: number | null
//   date_enter_marze: string | null // ISO
//   date_unloading: string | null // ISO
//   is_bimeh: string | null
//   marze_name: string | null
//   country_name: string | null
//   company_name: string | null
//   owner_name: string | null
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

// export function TallyListPage() {
//   const navigate = useNavigate()

//   const { data, isLoading, isError } = useQuery({
//     queryKey: ['tally-list'],
//     queryFn: () => apiGet<TallyRow[]>('/tally/list'),
//   })

//   return (
//     <div dir="rtl">
//       <Group justify="space-between" mb="md">
//         <Title order={2}>لیست تالی‌ها</Title>
//         <Button onClick={() => navigate('/tally/new')}>افزودن تالی</Button>
//       </Group>

//       <Paper shadow="xs" p="md">
//         {isLoading && (
//           <Center py="xl"><Loader /></Center>
//         )}

//         {isError && (
//           <Center py="xl">
//             <Text c="red">خطا در بارگذاری لیست تالی‌ها.</Text>
//           </Center>
//         )}

//         {data && data.length === 0 && (
//           <Center py="xl">
//             <Text c="dimmed">هنوز تالی‌ای ثبت نشده است. برای شروع «افزودن تالی» را بزنید.</Text>
//           </Center>
//         )}

//         {data && data.length > 0 && (
//           <Table striped highlightOnHover withTableBorder>
//             <Table.Thead>
//               <Table.Tr>
//                 <Table.Th>شماره تالی</Table.Th>
//                 <Table.Th>نام مرز</Table.Th>
//                 <Table.Th>مبدا (کشور)</Table.Th>
//                 <Table.Th>نام شرکت حمل</Table.Th>
//                 <Table.Th>صاحب کالا</Table.Th>
//                 <Table.Th>تاریخ ورود به مرز</Table.Th>
//                 <Table.Th>تاریخ تخلیه</Table.Th>
//               </Table.Tr>
//             </Table.Thead>
//             <Table.Tbody>
//               {data.map((row) => (
//                 <Table.Tr
//                   key={row.id_tali}
//                   style={{ cursor: 'pointer' }}
//                   onClick={() => navigate(`/tally/${row.id_tali}`)}
//                 >
//                   <Table.Td>{row.tali_number ?? '—'}</Table.Td>
//                   <Table.Td>{row.marze_name ?? '—'}</Table.Td>
//                   <Table.Td>{row.country_name ?? '—'}</Table.Td>
//                   <Table.Td>{row.company_name?.trim() || '—'}</Table.Td>
//                   <Table.Td>{row.owner_name?.trim() || '—'}</Table.Td>
//                   <Table.Td>{isoToJalali(row.date_enter_marze)}</Table.Td>
//                   <Table.Td>{isoToJalali(row.date_unloading)}</Table.Td>
//                 </Table.Tr>
//               ))}
//             </Table.Tbody>
//           </Table>
//         )}
//       </Paper>
//     </div>
//   )
// }


//2
// import { useMemo, useState } from 'react'
// import { useQuery } from '@tanstack/react-query'
// import { useNavigate } from 'react-router-dom'
// import {
//   Title, Text, Button, Group, Table, Paper, Badge, Tooltip, ActionIcon,
//   TextInput, Select, SimpleGrid, ThemeIcon, Skeleton, Box, Stack, Center,
// } from '@mantine/core'
// import { useDebouncedValue } from '@mantine/hooks'
// import { toJalaali } from 'jalaali-js'
// import { apiGet } from '../api/client'

// /**
//  * TallyListPage — the list of tallies (لیست تالی‌ها), the entry point to the
//  * tally module. Reads from /tally-list (the JOIN endpoint) so the border,
//  * country, company, and owner columns show names instead of raw ids.
//  *
//  * "افزودن تالی" opens the header form; clicking a row opens it for edit.
//  *
//  * This is a presentational dashboard around that exact data flow — the query,
//  * API, routing, and navigation are unchanged. Search / filters / stats are all
//  * derived client-side from the already-fetched rows; nothing new is requested
//  * from the server.
//  */

// // one row as returned by GET /tally-list (names already resolved by the JOIN)
// type TallyRow = {
//   id_tali: number
//   tali_number: number | null
//   radef_marze: number | null
//   date_enter_marze: string | null // ISO
//   date_unloading: string | null // ISO
//   is_bimeh: string | null
//   marze_name: string | null
//   country_name: string | null
//   company_name: string | null
//   owner_name: string | null
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

// const pad = (n: number) => String(n).padStart(2, '0')
// const localISO = (d: Date) => `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}`
// const daysAgoISO = (n: number) => { const d = new Date(); d.setDate(d.getDate() - n); return localISO(d) }

// // Persian/Arabic-Indic digits -> Latin, so search matches either.
// const normalizeDigits = (s: string) =>
//   s.replace(/[\u06F0-\u06F9]/g, (d) => String(d.charCodeAt(0) - 0x06f0))
//    .replace(/[\u0660-\u0669]/g, (d) => String(d.charCodeAt(0) - 0x0660))

// // Optional header-level fields that /tally/list does not return today. Read
// // defensively so the dangerous stat + warehouse/dangerous filters activate
// // automatically if the endpoint ever includes them (no API change made here).
// const rowIsDangerous = (r: TallyRow) => {
//   const v = (r as Record<string, unknown>).is_dangerous
//   return v === true || v === 1 || v === 'yes' || v === '1'
// }
// const rowWarehouse = (r: TallyRow) => {
//   const v = (r as Record<string, unknown>).warehouse_name ?? (r as Record<string, unknown>).anbar_name
//   return typeof v === 'string' && v.trim() ? v.trim() : null
// }

// // ---- inline SVG icons (no icon dependency in this project) ----
// type IconProps = { size?: number; stroke?: number }
// const mk = (body: React.ReactNode) =>
//   function Icon({ size = 20, stroke = 1.8 }: IconProps) {
//     return (
//       <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor"
//         strokeWidth={stroke} strokeLinecap="round" strokeLinejoin="round" aria-hidden>
//         {body}
//       </svg>
//     )
//   }
// const IconBox = mk(<><path d="M12 3l8 4.5v9L12 21l-8-4.5v-9L12 3z" /><path d="M4 7.5l8 4.5 8-4.5" /><path d="M12 12v9" /></>)
// const IconToday = mk(<><rect x="3" y="4" width="18" height="17" rx="2" /><path d="M3 9h18M8 2v4M16 2v4" /><path d="M9 15l2 2 4-4" /></>)
// const IconAlert = mk(<><path d="M12 3l9 16H3z" /><path d="M12 10v4M12 17h.01" /></>)
// const IconClock = mk(<><circle cx="12" cy="12" r="9" /><path d="M12 7v5l3 2" /></>)
// const IconSearch = mk(<><circle cx="11" cy="11" r="7" /><path d="M21 21l-4-4" /></>)
// const IconWarehouse = mk(<><path d="M3 21V9l9-5 9 5v12" /><path d="M3 21h18" /><path d="M8 21v-6h8v6" /></>)
// const IconCalendar = mk(<><rect x="3" y="4" width="18" height="17" rx="2" /><path d="M3 9h18M8 2v4M16 2v4" /></>)
// const IconRefresh = mk(<><path d="M4 12a8 8 0 0 1 13.7-5.7L20 8" /><path d="M20 4v4h-4" /><path d="M20 12a8 8 0 0 1-13.7 5.7L4 16" /><path d="M4 20v-4h4" /></>)
// const IconPlus = mk(<path d="M12 5v14M5 12h14" />)
// const IconEye = mk(<><path d="M2 12s3.5-7 10-7 10 7 10 7-3.5 7-10 7-10-7-10-7z" /><circle cx="12" cy="12" r="3" /></>)
// const IconInbox = mk(<><path d="M3 13l3-8h12l3 8" /><path d="M3 13v6h18v-6" /><path d="M3 13h5l1.5 2h5L21 13" /></>)

// type StatColor = 'blue' | 'teal' | 'red' | 'orange'
// const TINT: Record<StatColor, string> = {
//   blue: 'var(--mantine-color-blue-0)',
//   teal: 'var(--mantine-color-teal-0)',
//   red: 'var(--mantine-color-red-0)',
//   orange: 'var(--mantine-color-orange-0)',
// }

// function StatCard({ icon, value, label, color }: {
//   icon: React.ReactNode; value: number; label: string; color: StatColor
// }) {
//   return (
//     <Paper radius="lg" p="lg" withBorder style={{ background: TINT[color] }}>
//       <Group wrap="nowrap" gap="md" align="center">
//         <ThemeIcon size={52} radius="md" variant="light" color={color}>{icon}</ThemeIcon>
//         <div style={{ minWidth: 0 }}>
//           <Text fw={700} lh={1.1} style={{ fontSize: '1.9rem' }}>
//             {value.toLocaleString('fa-IR')}
//           </Text>
//           <Text size="sm" c="dimmed" mt={2}>{label}</Text>
//         </div>
//       </Group>
//     </Paper>
//   )
// }

// const COLS = 9 // for skeleton width

// export function TallyListPage() {
//   const navigate = useNavigate()

//   // ---- data flow unchanged ----
//   const { data, isLoading, isError, refetch, isFetching } = useQuery({
//     queryKey: ['tally-list'],
//     queryFn: () => apiGet<TallyRow[]>('/tally/list'),
//   })

//   // ---- local UI state for presentational filtering only ----
//   const [search, setSearch] = useState('')
//   const [debounced] = useDebouncedValue(search, 200)
//   const [warehouse, setWarehouse] = useState<string | null>(null)
//   const [dateRange, setDateRange] = useState<string | null>(null)
//   const [danger, setDanger] = useState<string | null>(null)

//   const rows = useMemo(() => data ?? [], [data])

//   // overview stats (computed from the full dataset, not the filtered view)
//   const stats = useMemo(() => {
//     const today = localISO(new Date())
//     return {
//       total: rows.length,
//       today: rows.filter((r) => (r.date_enter_marze ?? '').slice(0, 10) === today).length,
//       dangerous: rows.filter(rowIsDangerous).length,
//       pending: rows.filter((r) => !r.date_unloading).length,
//     }
//   }, [rows])

//   const warehouseOptions = useMemo(() => {
//     const set = new Set<string>()
//     rows.forEach((r) => { const w = rowWarehouse(r); if (w) set.add(w) })
//     return [...set].sort().map((w) => ({ value: w, label: w }))
//   }, [rows])

//   const filtered = useMemo(() => {
//     const q = normalizeDigits(debounced.trim().toLowerCase())
//     const today = localISO(new Date())
//     return rows.filter((r) => {
//       if (q) {
//         const hay = normalizeDigits(
//           [r.tali_number, r.marze_name, r.country_name, r.company_name, r.owner_name]
//             .map((x) => (x ?? '')).join(' ').toLowerCase(),
//         )
//         if (!hay.includes(q)) return false
//       }
//       if (warehouse && rowWarehouse(r) !== warehouse) return false
//       if (danger === 'yes' && !rowIsDangerous(r)) return false
//       if (danger === 'no' && rowIsDangerous(r)) return false
//       if (dateRange) {
//         const d = (r.date_enter_marze ?? '').slice(0, 10)
//         if (!d) return false
//         if (dateRange === 'today' && d !== today) return false
//         if (dateRange === '7' && d < daysAgoISO(7)) return false
//         if (dateRange === '30' && d < daysAgoISO(30)) return false
//       }
//       return true
//     })
//   }, [rows, debounced, warehouse, danger, dateRange])

//   const hasFilters = Boolean(debounced || warehouse || dateRange || danger)
//   const clearFilters = () => { setSearch(''); setWarehouse(null); setDateRange(null); setDanger(null) }

//   return (
//     <Box dir="rtl" style={{ maxWidth: 1280, margin: '0 auto' }}>
//       <style>{`
//         .tlp-card { transition: box-shadow 150ms ease; }
//         .tlp-card:hover { box-shadow: var(--mantine-shadow-md); }
//         .tlp-row td { transition: background-color 120ms ease; }
//         @media (prefers-reduced-motion: reduce) {
//           .tlp-card, .tlp-row td { transition: none; }
//         }
//       `}</style>

//       {/* ---- dashboard header ---- */}
//       <Group justify="space-between" align="flex-end" mb="lg" wrap="wrap" gap="sm">
//         <div>
//           <Title order={2} fw={700}>مدیریت تالی‌ها</Title>
//           <Text c="dimmed" size="sm" mt={4}>نمای کلی و پیگیری تالی‌های انبار</Text>
//         </div>
//         <Group gap="sm">
//           <Button
//             variant="default" radius="md" leftSection={<IconRefresh size={18} />}
//             onClick={() => refetch()} loading={isFetching && !isLoading}
//           >
//             بروزرسانی
//           </Button>
//           <Button
//             radius="md" leftSection={<IconPlus size={18} />}
//             onClick={() => navigate('/tally/new')}
//           >
//             افزودن تالی
//           </Button>
//         </Group>
//       </Group>

//       {/* ---- summary stat cards ---- */}
//       <SimpleGrid cols={{ base: 1, xs: 2, md: 4 }} spacing="md" mb="lg">
//         {isLoading ? (
//           Array.from({ length: 4 }).map((_, i) => <Skeleton key={i} height={92} radius="lg" />)
//         ) : (
//           <>
//             <div className="tlp-card"><StatCard icon={<IconBox />} value={stats.total} label="کل تالی‌ها" color="blue" /></div>
//             {/* <div className="tlp-card"><StatCard icon={<IconToday />} value={stats.today} label="تالی‌های امروز" color="teal" /></div> */}
//             {/* <div className="tlp-card"><StatCard icon={<IconAlert />} value={stats.dangerous} label="کالای خطرناک" color="red" /></div> */}
//             <div className="tlp-card"><StatCard icon={<IconClock />} value={stats.pending} label="عملیات در انتظار" color="orange" /></div>
//           </>
//         )}
//       </SimpleGrid>

//       {/* ---- toolbar ---- */}
//       <Paper radius="md" p="sm" withBorder shadow="xs" mb="md">
//         <Group gap="sm" wrap="wrap" align="center">
//           <TextInput
//             radius="md" placeholder="جستجو در تالی‌ها…"
//             leftSection={<IconSearch size={16} />}
//             value={search} onChange={(e) => setSearch(e.currentTarget.value)}
//             style={{ flex: '1 1 240px', minWidth: 200 }}
//           />
//           <Select
//             radius="md" placeholder="انبار" clearable
//             leftSection={<IconWarehouse size={16} />}
//             data={warehouseOptions} value={warehouse} onChange={setWarehouse}
//             disabled={warehouseOptions.length === 0}
//             w={150}
//           />
//           <Select
//             radius="md" placeholder="بازه تاریخ" clearable
//             leftSection={<IconCalendar size={16} />}
//             data={[
//               { value: 'today', label: 'امروز' },
//               { value: '7', label: '۷ روز اخیر' },
//               { value: '30', label: '۳۰ روز اخیر' },
//             ]}
//             value={dateRange} onChange={setDateRange} w={150}
//           />
//           <Select
//             radius="md" placeholder="کالای خطرناک" clearable
//             leftSection={<IconAlert size={16} />}
//             data={[
//               { value: 'yes', label: 'دارد' },
//               { value: 'no', label: 'ندارد' },
//             ]}
//             value={danger} onChange={setDanger} w={150}
//           />
//         </Group>
//       </Paper>

//       {/* ---- table / states ---- */}
//       <Paper radius="md" withBorder shadow="sm" style={{ overflow: 'hidden' }}>
//         {isLoading && <TableSkeleton />}

//         {isError && (
//           <Center py={64}>
//             <Stack align="center" gap="xs">
//               <ThemeIcon size={48} radius="xl" variant="light" color="red"><IconAlert size={26} /></ThemeIcon>
//               <Text fw={600}>بارگذاری تالی‌ها ناموفق بود</Text>
//               <Text size="sm" c="dimmed">اتصال را بررسی کنید و دوباره تلاش کنید.</Text>
//               <Button mt="xs" variant="light" radius="md" leftSection={<IconRefresh size={16} />} onClick={() => refetch()}>
//                 تلاش دوباره
//               </Button>
//             </Stack>
//           </Center>
//         )}

//         {data && data.length === 0 && (
//           <Center py={72}>
//             <Stack align="center" gap="sm" maw={360} ta="center">
//               <ThemeIcon size={72} radius="xl" variant="light" color="blue"><IconInbox size={38} /></ThemeIcon>
//               <Text fw={600} size="lg">هنوز تالی‌ای ثبت نشده است</Text>
//               <Text size="sm" c="dimmed">اولین تالی انبار را بسازید تا اینجا نمایش داده شود.</Text>
//               <Button mt="xs" radius="md" leftSection={<IconPlus size={18} />} onClick={() => navigate('/tally/new')}>
//                 افزودن تالی
//               </Button>
//             </Stack>
//           </Center>
//         )}

//         {data && data.length > 0 && filtered.length === 0 && (
//           <Center py={64}>
//             <Stack align="center" gap="xs">
//               <ThemeIcon size={48} radius="xl" variant="light" color="gray"><IconSearch size={24} /></ThemeIcon>
//               <Text fw={600}>نتیجه‌ای یافت نشد</Text>
//               <Text size="sm" c="dimmed">هیچ تالی‌ای با این فیلترها مطابقت ندارد.</Text>
//               <Button mt="xs" variant="subtle" radius="md" onClick={clearFilters}>پاک کردن فیلترها</Button>
//             </Stack>
//           </Center>
//         )}

//         {data && data.length > 0 && filtered.length > 0 && (
//           <Table.ScrollContainer minWidth={860}>
//             <Table striped highlightOnHover stickyHeader verticalSpacing="sm" horizontalSpacing="md" withRowBorders>
//               <Table.Thead style={{ background: 'var(--mantine-color-gray-0)' }}>
//                 <Table.Tr>
//                   <Table.Th>شماره تالی</Table.Th>
//                   <Table.Th>نام مرز</Table.Th>
//                   <Table.Th>مبدا (کشور)</Table.Th>
//                   <Table.Th>نام شرکت حمل</Table.Th>
//                   <Table.Th>صاحب کالا</Table.Th>
//                   <Table.Th>تاریخ ورود به مرز</Table.Th>
//                   <Table.Th>تاریخ تخلیه</Table.Th>
//                   <Table.Th>وضعیت</Table.Th>
//                   <Table.Th style={{ textAlign: 'center' }}>عملیات</Table.Th>
//                 </Table.Tr>
//               </Table.Thead>
//               <Table.Tbody>
//                 {filtered.map((row) => {
//                   const unloaded = Boolean(row.date_unloading)
//                   const insured = (row.is_bimeh ?? '').trim() === 'yes'
//                   return (
//                     <Table.Tr
//                       key={row.id_tali} className="tlp-row"
//                       style={{ cursor: 'pointer' }}
//                       onClick={() => navigate(`/tally/${row.id_tali}`)}
//                     >
//                       <Table.Td><Text fw={600}>{row.tali_number ?? '—'}</Text></Table.Td>
//                       <Table.Td>{row.marze_name ?? '—'}</Table.Td>
//                       <Table.Td>{row.country_name ?? '—'}</Table.Td>
//                       <Table.Td>{row.company_name?.trim() || '—'}</Table.Td>
//                       <Table.Td>{row.owner_name?.trim() || '—'}</Table.Td>
//                       <Table.Td>{isoToJalali(row.date_enter_marze)}</Table.Td>
//                       <Table.Td>{isoToJalali(row.date_unloading)}</Table.Td>
//                       <Table.Td>
//                         <Group gap={6} wrap="nowrap">
//                           <Badge color={unloaded ? 'teal' : 'orange'} variant="light" radius="sm">
//                             {unloaded ? 'تخلیه شده' : 'در انتظار تخلیه'}
//                           </Badge>
//                           {insured && <Badge color="blue" variant="light" radius="sm">بیمه</Badge>}
//                         </Group>
//                       </Table.Td>
//                       <Table.Td style={{ textAlign: 'center' }}>
//                         <Tooltip label="مشاهده جزئیات" withArrow>
//                           <ActionIcon
//                             variant="subtle" color="blue" radius="md"
//                             onClick={(e) => { e.stopPropagation(); navigate(`/tally/${row.id_tali}`) }}
//                             aria-label="مشاهده جزئیات تالی"
//                           >
//                             <IconEye size={18} />
//                           </ActionIcon>
//                         </Tooltip>
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
//           نمایش {filtered.length.toLocaleString('fa-IR')} از {rows.length.toLocaleString('fa-IR')} تالی
//         </Text>
//       )}
//     </Box>
//   )
// }

// function TableSkeleton() {
//   return (
//     <Box p="md">
//       <Skeleton height={34} radius="sm" mb="sm" />
//       {Array.from({ length: 6 }).map((_, i) => (
//         <Group key={i} gap="md" mb="sm" wrap="nowrap">
//           {Array.from({ length: COLS }).map((__, j) => (
//             <Skeleton key={j} height={20} radius="sm" style={{ flex: j === 0 ? '0 0 70px' : 1 }} />
//           ))}
//         </Group>
//       ))}
//     </Box>
//   )
// }

// import { useMemo, useState } from 'react'
// import { useQuery } from '@tanstack/react-query'
// import { useNavigate } from 'react-router-dom'
// import {
//   Title, Text, Button, Group, Table, Paper, Badge, Tooltip, ActionIcon,
//   TextInput, Select, SimpleGrid, ThemeIcon, Skeleton, Box, Stack, Center,
// } from '@mantine/core'
// import { useDebouncedValue } from '@mantine/hooks'
// import { toJalaali } from 'jalaali-js'
// import { apiGet } from '../api/client'

// /**
//  * TallyListPage — the list of tallies (لیست تالی‌ها), the entry point to the
//  * tally module. Reads from /tally-list (the JOIN endpoint) so the border,
//  * country, company, and owner columns show names instead of raw ids.
//  *
//  * "افزودن تالی" opens the header form; clicking a row opens it for edit.
//  *
//  * This is a presentational dashboard around that exact data flow — the query,
//  * API, routing, and navigation are unchanged. Search / filters / stats are all
//  * derived client-side from the already-fetched rows; nothing new is requested
//  * from the server.
//  */

// // one row as returned by GET /tally-list (names already resolved by the JOIN)
// type TallyRow = {
//   id_tali: number
//   tali_number: number | null
//   radef_marze: number | null
//   date_enter_marze: string | null // ISO
//   date_unloading: string | null // ISO
//   is_bimeh: string | null
//   marze_name: string | null
//   country_name: string | null
//   company_name: string | null
//   owner_name: string | null
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

// const pad = (n: number) => String(n).padStart(2, '0')
// const localISO = (d: Date) => `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}`
// const daysAgoISO = (n: number) => { const d = new Date(); d.setDate(d.getDate() - n); return localISO(d) }

// // Persian/Arabic-Indic digits -> Latin, so search matches either.
// const normalizeDigits = (s: string) =>
//   s.replace(/[\u06F0-\u06F9]/g, (d) => String(d.charCodeAt(0) - 0x06f0))
//    .replace(/[\u0660-\u0669]/g, (d) => String(d.charCodeAt(0) - 0x0660))

// // Optional header-level fields that /tally/list does not return today. Read
// // defensively so the dangerous stat + warehouse/dangerous filters activate
// // automatically if the endpoint ever includes them (no API change made here).
// const rowIsDangerous = (r: TallyRow) => {
//   const v = (r as Record<string, unknown>).is_dangerous
//   return v === true || v === 1 || v === 'yes' || v === '1'
// }
// const rowWarehouse = (r: TallyRow) => {
//   const v = (r as Record<string, unknown>).warehouse_name ?? (r as Record<string, unknown>).anbar_name
//   return typeof v === 'string' && v.trim() ? v.trim() : null
// }

// // ---- inline SVG icons (no icon dependency in this project) ----
// type IconProps = { size?: number; stroke?: number }
// const mk = (body: React.ReactNode) =>
//   function Icon({ size = 20, stroke = 1.8 }: IconProps) {
//     return (
//       <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor"
//         strokeWidth={stroke} strokeLinecap="round" strokeLinejoin="round" aria-hidden>
//         {body}
//       </svg>
//     )
//   }
// const IconBox = mk(<><path d="M12 3l8 4.5v9L12 21l-8-4.5v-9L12 3z" /><path d="M4 7.5l8 4.5 8-4.5" /><path d="M12 12v9" /></>)
// const IconAlert = mk(<><path d="M12 3l9 16H3z" /><path d="M12 10v4M12 17h.01" /></>)
// const IconClock = mk(<><circle cx="12" cy="12" r="9" /><path d="M12 7v5l3 2" /></>)
// const IconSearch = mk(<><circle cx="11" cy="11" r="7" /><path d="M21 21l-4-4" /></>)
// const IconWarehouse = mk(<><path d="M3 21V9l9-5 9 5v12" /><path d="M3 21h18" /><path d="M8 21v-6h8v6" /></>)
// const IconCalendar = mk(<><rect x="3" y="4" width="18" height="17" rx="2" /><path d="M3 9h18M8 2v4M16 2v4" /></>)
// const IconRefresh = mk(<><path d="M4 12a8 8 0 0 1 13.7-5.7L20 8" /><path d="M20 4v4h-4" /><path d="M20 12a8 8 0 0 1-13.7 5.7L4 16" /><path d="M4 20v-4h4" /></>)
// const IconPlus = mk(<path d="M12 5v14M5 12h14" />)
// const IconEye = mk(<><path d="M2 12s3.5-7 10-7 10 7 10 7-3.5 7-10 7-10-7-10-7z" /><circle cx="12" cy="12" r="3" /></>)
// const IconInbox = mk(<><path d="M3 13l3-8h12l3 8" /><path d="M3 13v6h18v-6" /><path d="M3 13h5l1.5 2h5L21 13" /></>)

// type StatColor = 'blue' | 'teal' | 'red' | 'orange'
// const TINT: Record<StatColor, string> = {
//   blue: 'var(--mantine-color-blue-0)',
//   teal: 'var(--mantine-color-teal-0)',
//   red: 'var(--mantine-color-red-0)',
//   orange: 'var(--mantine-color-orange-0)',
// }

// function StatCard({ icon, value, label, color }: {
//   icon: React.ReactNode; value: number; label: string; color: StatColor
// }) {
//   return (
//     <Paper radius="lg" p="lg" withBorder style={{ background: TINT[color] }}>
//       <Group wrap="nowrap" gap="md" align="center">
//         <ThemeIcon size={52} radius="md" variant="light" color={color}>{icon}</ThemeIcon>
//         <div style={{ minWidth: 0 }}>
//           <Text fw={700} lh={1.1} style={{ fontSize: '1.9rem' }}>
//             {value.toLocaleString('fa-IR')}
//           </Text>
//           <Text size="sm" c="dimmed" mt={2}>{label}</Text>
//         </div>
//       </Group>
//     </Paper>
//   )
// }

// const COLS = 9 // for skeleton width

// export function TallyListPage() {
//   const navigate = useNavigate()

//   // ---- data flow unchanged ----
//   const { data, isLoading, isError, refetch, isFetching } = useQuery({
//     queryKey: ['tally-list'],
//     queryFn: () => apiGet<TallyRow[]>('/tally/list'),
//   })

//   // ---- local UI state for presentational filtering only ----
//   const [search, setSearch] = useState('')
//   const [debounced] = useDebouncedValue(search, 200)
//   const [warehouse, setWarehouse] = useState<string | null>(null)
//   const [dateRange, setDateRange] = useState<string | null>(null)
//   const [danger, setDanger] = useState<string | null>(null)

//   const rows = useMemo(() => data ?? [], [data])

//   // overview stats (computed from the full dataset, not the filtered view)
//   const stats = useMemo(() => {
//     const today = localISO(new Date())
//     return {
//       total: rows.length,
//       today: rows.filter((r) => (r.date_enter_marze ?? '').slice(0, 10) === today).length,
//       dangerous: rows.filter(rowIsDangerous).length,
//       pending: rows.filter((r) => !r.date_unloading).length,
//     }
//   }, [rows])

//   const warehouseOptions = useMemo(() => {
//     const set = new Set<string>()
//     rows.forEach((r) => { const w = rowWarehouse(r); if (w) set.add(w) })
//     return [...set].sort().map((w) => ({ value: w, label: w }))
//   }, [rows])

//   const filtered = useMemo(() => {
//     const q = normalizeDigits(debounced.trim().toLowerCase())
//     const today = localISO(new Date())
//     return rows.filter((r) => {
//       if (q) {
//         const hay = normalizeDigits(
//           [r.tali_number, r.marze_name, r.country_name, r.company_name, r.owner_name]
//             .map((x) => (x ?? '')).join(' ').toLowerCase(),
//         )
//         if (!hay.includes(q)) return false
//       }
//       if (warehouse && rowWarehouse(r) !== warehouse) return false
//       if (danger === 'yes' && !rowIsDangerous(r)) return false
//       if (danger === 'no' && rowIsDangerous(r)) return false
//       if (dateRange) {
//         const d = (r.date_enter_marze ?? '').slice(0, 10)
//         if (!d) return false
//         if (dateRange === 'today' && d !== today) return false
//         if (dateRange === '7' && d < daysAgoISO(7)) return false
//         if (dateRange === '30' && d < daysAgoISO(30)) return false
//       }
//       return true
//     })
//   }, [rows, debounced, warehouse, danger, dateRange])

//   const hasFilters = Boolean(debounced || warehouse || dateRange || danger)
//   const clearFilters = () => { setSearch(''); setWarehouse(null); setDateRange(null); setDanger(null) }

//   return (
//     <Box dir="rtl" style={{ maxWidth: 1280, margin: '0 auto' }}>
//       <style>{`
//         .tlp-card { transition: box-shadow 150ms ease; }
//         .tlp-card:hover { box-shadow: var(--mantine-shadow-md); }
//         .tlp-row td { transition: background-color 120ms ease; }
//         @media (prefers-reduced-motion: reduce) {
//           .tlp-card, .tlp-row td { transition: none; }
//         }
//       `}</style>

//       {/* ---- dashboard header ---- */}
//       <Group justify="space-between" align="flex-end" mb="lg" wrap="wrap" gap="sm">
//         <div>
//           <Title order={2} fw={700}>مدیریت تالی‌ها</Title>
//           <Text c="dimmed" size="sm" mt={4}>نمای کلی و پیگیری تالی‌های انبار</Text>
//         </div>
//         <Group gap="sm">
//           <Button
//             variant="default" radius="md" leftSection={<IconRefresh size={18} />}
//             onClick={() => refetch()} loading={isFetching && !isLoading}
//           >
//             بروزرسانی
//           </Button>
//           <Button
//             radius="md" leftSection={<IconPlus size={18} />}
//             onClick={() => navigate('/tally/new')}
//           >
//             افزودن تالی
//           </Button>
//         </Group>
//       </Group>

//       {/* ---- summary stat cards ---- */}
//       <SimpleGrid cols={{ base: 1, xs: 2 }} spacing="md" mb="lg">
//         {isLoading ? (
//           Array.from({ length: 2 }).map((_, i) => <Skeleton key={i} height={92} radius="lg" />)
//         ) : (
//           <>
//             <div className="tlp-card"><StatCard icon={<IconBox />} value={stats.total} label="کل تالی‌ها" color="blue" /></div>
//             <div className="tlp-card"><StatCard icon={<IconClock />} value={stats.pending} label="عملیات در انتظار" color="orange" /></div>
//           </>
//         )}
//       </SimpleGrid>

//       {/* ---- toolbar ---- */}
//       <Paper radius="md" p="sm" withBorder shadow="xs" mb="md">
//         <Group gap="sm" wrap="wrap" align="center">
//           <TextInput
//             radius="md" placeholder="جستجو در تالی‌ها…"
//             leftSection={<IconSearch size={16} />}
//             value={search} onChange={(e) => setSearch(e.currentTarget.value)}
//             style={{ flex: '1 1 240px', minWidth: 200 }}
//           />
//           <Select
//             radius="md" placeholder="انبار" clearable
//             leftSection={<IconWarehouse size={16} />}
//             data={warehouseOptions} value={warehouse} onChange={setWarehouse}
//             disabled={warehouseOptions.length === 0}
//             w={150}
//           />
//           <Select
//             radius="md" placeholder="بازه تاریخ" clearable
//             leftSection={<IconCalendar size={16} />}
//             data={[
//               { value: 'today', label: 'امروز' },
//               { value: '7', label: '۷ روز اخیر' },
//               { value: '30', label: '۳۰ روز اخیر' },
//             ]}
//             value={dateRange} onChange={setDateRange} w={150}
//           />
//           <Select
//             radius="md" placeholder="کالای خطرناک" clearable
//             leftSection={<IconAlert size={16} />}
//             data={[
//               { value: 'yes', label: 'دارد' },
//               { value: 'no', label: 'ندارد' },
//             ]}
//             value={danger} onChange={setDanger} w={150}
//           />
//         </Group>
//       </Paper>

//       {/* ---- table / states ---- */}
//       <Paper radius="md" withBorder shadow="sm" style={{ overflow: 'hidden' }}>
//         {isLoading && <TableSkeleton />}

//         {isError && (
//           <Center py={64}>
//             <Stack align="center" gap="xs">
//               <ThemeIcon size={48} radius="xl" variant="light" color="red"><IconAlert size={26} /></ThemeIcon>
//               <Text fw={600}>بارگذاری تالی‌ها ناموفق بود</Text>
//               <Text size="sm" c="dimmed">اتصال را بررسی کنید و دوباره تلاش کنید.</Text>
//               <Button mt="xs" variant="light" radius="md" leftSection={<IconRefresh size={16} />} onClick={() => refetch()}>
//                 تلاش دوباره
//               </Button>
//             </Stack>
//           </Center>
//         )}

//         {data && data.length === 0 && (
//           <Center py={72}>
//             <Stack align="center" gap="sm" maw={360} ta="center">
//               <ThemeIcon size={72} radius="xl" variant="light" color="blue"><IconInbox size={38} /></ThemeIcon>
//               <Text fw={600} size="lg">هنوز تالی‌ای ثبت نشده است</Text>
//               <Text size="sm" c="dimmed">اولین تالی انبار را بسازید تا اینجا نمایش داده شود.</Text>
//               <Button mt="xs" radius="md" leftSection={<IconPlus size={18} />} onClick={() => navigate('/tally/new')}>
//                 افزودن تالی
//               </Button>
//             </Stack>
//           </Center>
//         )}

//         {data && data.length > 0 && filtered.length === 0 && (
//           <Center py={64}>
//             <Stack align="center" gap="xs">
//               <ThemeIcon size={48} radius="xl" variant="light" color="gray"><IconSearch size={24} /></ThemeIcon>
//               <Text fw={600}>نتیجه‌ای یافت نشد</Text>
//               <Text size="sm" c="dimmed">هیچ تالی‌ای با این فیلترها مطابقت ندارد.</Text>
//               <Button mt="xs" variant="subtle" radius="md" onClick={clearFilters}>پاک کردن فیلترها</Button>
//             </Stack>
//           </Center>
//         )}

//         {data && data.length > 0 && filtered.length > 0 && (
//           <Table.ScrollContainer minWidth={860}>
//             <Table striped highlightOnHover stickyHeader verticalSpacing="sm" horizontalSpacing="md" withRowBorders>
//               <Table.Thead style={{ background: 'var(--mantine-color-gray-0)' }}>
//                 <Table.Tr>
//                   <Table.Th>شماره تالی</Table.Th>
//                   <Table.Th>نام مرز</Table.Th>
//                   <Table.Th>مبدا (کشور)</Table.Th>
//                   <Table.Th>نام شرکت حمل</Table.Th>
//                   <Table.Th>صاحب کالا</Table.Th>
//                   <Table.Th>تاریخ ورود به مرز</Table.Th>
//                   <Table.Th>تاریخ تخلیه</Table.Th>
//                   <Table.Th>وضعیت</Table.Th>
//                   <Table.Th style={{ textAlign: 'center' }}>عملیات</Table.Th>
//                 </Table.Tr>
//               </Table.Thead>
//               <Table.Tbody>
//                 {filtered.map((row) => {
//                   const unloaded = Boolean(row.date_unloading)
//                   const insured = (row.is_bimeh ?? '').trim() === 'yes'
//                   return (
//                     <Table.Tr
//                       key={row.id_tali} className="tlp-row"
//                       style={{ cursor: 'pointer' }}
//                       onClick={() => navigate(`/tally/${row.id_tali}`)}
//                     >
//                       <Table.Td><Text fw={600}>{row.tali_number ?? '—'}</Text></Table.Td>
//                       <Table.Td>{row.marze_name ?? '—'}</Table.Td>
//                       <Table.Td>{row.country_name ?? '—'}</Table.Td>
//                       <Table.Td>{row.company_name?.trim() || '—'}</Table.Td>
//                       <Table.Td>{row.owner_name?.trim() || '—'}</Table.Td>
//                       <Table.Td>{isoToJalali(row.date_enter_marze)}</Table.Td>
//                       <Table.Td>{isoToJalali(row.date_unloading)}</Table.Td>
//                       <Table.Td>
//                         <Group gap={6} wrap="nowrap">
//                           <Badge color={unloaded ? 'teal' : 'orange'} variant="light" radius="sm">
//                             {unloaded ? 'تخلیه شده' : 'در انتظار تخلیه'}
//                           </Badge>
//                           {insured && <Badge color="blue" variant="light" radius="sm">بیمه</Badge>}
//                         </Group>
//                       </Table.Td>
//                       <Table.Td style={{ textAlign: 'center' }}>
//                         <Tooltip label="مشاهده جزئیات" withArrow>
//                           <ActionIcon
//                             variant="subtle" color="blue" radius="md"
//                             onClick={(e) => { e.stopPropagation(); navigate(`/tally/${row.id_tali}`) }}
//                             aria-label="مشاهده جزئیات تالی"
//                           >
//                             <IconEye size={18} />
//                           </ActionIcon>
//                         </Tooltip>
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
//           نمایش {filtered.length.toLocaleString('fa-IR')} از {rows.length.toLocaleString('fa-IR')} تالی
//         </Text>
//       )}
//     </Box>
//   )
// }

// function TableSkeleton() {
//   return (
//     <Box p="md">
//       <Skeleton height={34} radius="sm" mb="sm" />
//       {Array.from({ length: 6 }).map((_, i) => (
//         <Group key={i} gap="md" mb="sm" wrap="nowrap">
//           {Array.from({ length: COLS }).map((__, j) => (
//             <Skeleton key={j} height={20} radius="sm" style={{ flex: j === 0 ? '0 0 70px' : 1 }} />
//           ))}
//         </Group>
//       ))}
//     </Box>
//   )
// }

import { useMemo, useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { useNavigate } from 'react-router-dom'
import {
  Title, Text, Button, Group, Table, Paper, Badge, Tooltip, ActionIcon,
  TextInput, Select, SimpleGrid, ThemeIcon, Skeleton, Box, Stack, Center,
} from '@mantine/core'
import { useDebouncedValue } from '@mantine/hooks'
import { toJalaali } from 'jalaali-js'
import { apiGet } from '../api/client'
import { TallyNumber } from '../components/TallyNumber'

/**
 * TallyListPage — the list of tallies (لیست تالی‌ها), the entry point to the
 * tally module. Reads from /tally-list (the JOIN endpoint) so the border,
 * country, company, and owner columns show names instead of raw ids.
 *
 * "افزودن تالی" opens the header form; clicking a row opens it for edit.
 *
 * This is a presentational dashboard around that exact data flow — the query,
 * API, routing, and navigation are unchanged. Search / filters / stats are all
 * derived client-side from the already-fetched rows; nothing new is requested
 * from the server.
 */

// one row as returned by GET /tally-list (names already resolved by the JOIN)
type TallyRow = {
  id_tali: number
  tali_number: string | null
  radef_marze: number | null
  date_enter_marze: string | null // ISO
  date_unloading: string | null // ISO
  is_bimeh: string | null
  marze_name: string | null
  country_name: string | null
  company_name: string | null
  owner_name: string | null
}

function tallyPath(row: TallyRow): string {
  const publicReference = row.tali_number ?? String(row.id_tali)
  return `/tally/${encodeURIComponent(publicReference)}`
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

const pad = (n: number) => String(n).padStart(2, '0')
const localISO = (d: Date) => `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}`
const daysAgoISO = (n: number) => { const d = new Date(); d.setDate(d.getDate() - n); return localISO(d) }

// Persian/Arabic-Indic digits -> Latin, so search matches either.
const normalizeDigits = (s: string) =>
  s.replace(/[\u06F0-\u06F9]/g, (d) => String(d.charCodeAt(0) - 0x06f0))
   .replace(/[\u0660-\u0669]/g, (d) => String(d.charCodeAt(0) - 0x0660))

// Optional header-level fields that /tally/list does not return today. Read
// defensively so the dangerous stat + warehouse/dangerous filters activate
// automatically if the endpoint ever includes them (no API change made here).
const rowIsDangerous = (r: TallyRow) => {
  const v = (r as Record<string, unknown>).is_dangerous
  return v === true || v === 1 || v === 'yes' || v === '1'
}
const rowWarehouse = (r: TallyRow) => {
  const v = (r as Record<string, unknown>).warehouse_name ?? (r as Record<string, unknown>).anbar_name
  return typeof v === 'string' && v.trim() ? v.trim() : null
}

// ---- inline SVG icons (no icon dependency in this project) ----
type IconProps = { size?: number; stroke?: number }
const mk = (body: React.ReactNode) =>
  function Icon({ size = 20, stroke = 1.8 }: IconProps) {
    return (
      <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor"
        strokeWidth={stroke} strokeLinecap="round" strokeLinejoin="round" aria-hidden>
        {body}
      </svg>
    )
  }
const IconBox = mk(<><path d="M12 3l8 4.5v9L12 21l-8-4.5v-9L12 3z" /><path d="M4 7.5l8 4.5 8-4.5" /><path d="M12 12v9" /></>)
const IconAlert = mk(<><path d="M12 3l9 16H3z" /><path d="M12 10v4M12 17h.01" /></>)
const IconClock = mk(<><circle cx="12" cy="12" r="9" /><path d="M12 7v5l3 2" /></>)
const IconSearch = mk(<><circle cx="11" cy="11" r="7" /><path d="M21 21l-4-4" /></>)
const IconWarehouse = mk(<><path d="M3 21V9l9-5 9 5v12" /><path d="M3 21h18" /><path d="M8 21v-6h8v6" /></>)
const IconCalendar = mk(<><rect x="3" y="4" width="18" height="17" rx="2" /><path d="M3 9h18M8 2v4M16 2v4" /></>)
const IconRefresh = mk(<><path d="M4 12a8 8 0 0 1 13.7-5.7L20 8" /><path d="M20 4v4h-4" /><path d="M20 12a8 8 0 0 1-13.7 5.7L4 16" /><path d="M4 20v-4h4" /></>)
const IconPlus = mk(<path d="M12 5v14M5 12h14" />)
const IconEye = mk(<><path d="M2 12s3.5-7 10-7 10 7 10 7-3.5 7-10 7-10-7-10-7z" /><circle cx="12" cy="12" r="3" /></>)
const IconInbox = mk(<><path d="M3 13l3-8h12l3 8" /><path d="M3 13v6h18v-6" /><path d="M3 13h5l1.5 2h5L21 13" /></>)

type StatColor = 'blue' | 'teal' | 'red' | 'orange'
const TINT: Record<StatColor, string> = {
  blue: 'var(--mantine-color-blue-light)',
  teal: 'var(--mantine-color-teal-light)',
  red: 'var(--mantine-color-red-light)',
  orange: 'var(--mantine-color-orange-light)',
}

function StatCard({ icon, value, label, color }: {
  icon: React.ReactNode; value: number; label: string; color: StatColor
}) {
  return (
    <Paper radius="lg" p="lg" shadow="sm" style={{ background: TINT[color] }}>
      <Group wrap="nowrap" gap="md" align="center">
        <ThemeIcon size={56} radius="md" variant="filled" color={color}>{icon}</ThemeIcon>
        <div style={{ minWidth: 0 }}>
          <Text fw={800} lh={1.05} style={{ fontSize: '2.15rem' }}>
            {value.toLocaleString('fa-IR')}
          </Text>
          <Text size="sm" c="dimmed" mt={4} fw={500}>{label}</Text>
        </div>
      </Group>
    </Paper>
  )
}

const COLS = 9 // for skeleton width

export function TallyListPage() {
  const navigate = useNavigate()

  // ---- data flow unchanged ----
  const { data, isLoading, isError, refetch, isFetching } = useQuery({
    queryKey: ['tally-list'],
    queryFn: () => apiGet<TallyRow[]>('/tally/list'),
  })

  // ---- local UI state for presentational filtering only ----
  const [search, setSearch] = useState('')
  const [debounced] = useDebouncedValue(search, 200)
  const [warehouse, setWarehouse] = useState<string | null>(null)
  const [dateRange, setDateRange] = useState<string | null>(null)
  const [danger, setDanger] = useState<string | null>(null)

  const rows = useMemo(() => data ?? [], [data])

  // overview stats (computed from the full dataset, not the filtered view)
  const stats = useMemo(() => {
    const today = localISO(new Date())
    return {
      total: rows.length,
      today: rows.filter((r) => (r.date_enter_marze ?? '').slice(0, 10) === today).length,
      dangerous: rows.filter(rowIsDangerous).length,
      pending: rows.filter((r) => !r.date_unloading).length,
    }
  }, [rows])

  const warehouseOptions = useMemo(() => {
    const set = new Set<string>()
    rows.forEach((r) => { const w = rowWarehouse(r); if (w) set.add(w) })
    return [...set].sort().map((w) => ({ value: w, label: w }))
  }, [rows])

  const filtered = useMemo(() => {
    const q = normalizeDigits(debounced.trim().toLowerCase())
    const today = localISO(new Date())
    return rows.filter((r) => {
      if (q) {
        const hay = normalizeDigits(
          [r.tali_number, r.marze_name, r.country_name, r.company_name, r.owner_name]
            .map((x) => (x ?? '')).join(' ').toLowerCase(),
        )
        if (!hay.includes(q)) return false
      }
      if (warehouse && rowWarehouse(r) !== warehouse) return false
      if (danger === 'yes' && !rowIsDangerous(r)) return false
      if (danger === 'no' && rowIsDangerous(r)) return false
      if (dateRange) {
        const d = (r.date_enter_marze ?? '').slice(0, 10)
        if (!d) return false
        if (dateRange === 'today' && d !== today) return false
        if (dateRange === '7' && d < daysAgoISO(7)) return false
        if (dateRange === '30' && d < daysAgoISO(30)) return false
      }
      return true
    })
  }, [rows, debounced, warehouse, danger, dateRange])

  const hasFilters = Boolean(debounced || warehouse || dateRange || danger)
  const clearFilters = () => { setSearch(''); setWarehouse(null); setDateRange(null); setDanger(null) }

  return (
    <Box dir="rtl" style={{ maxWidth: 1280, margin: '0 auto' }}>
      <style>{`
        .tlp-card { transition: box-shadow 150ms ease; }
        .tlp-card:hover { box-shadow: var(--mantine-shadow-md); }
        .tlp-row td { transition: background-color 120ms ease; }
        @media (prefers-reduced-motion: reduce) {
          .tlp-card, .tlp-row td { transition: none; }
        }
      `}</style>

      {/* ---- dashboard header ---- */}
      <Group justify="space-between" align="flex-end" mb="lg" wrap="wrap" gap="sm">
        <div>
          <Title order={2} fw={700}>مدیریت تالی‌ها</Title>
          <Text c="dimmed" size="sm" mt={4}>نمای کلی و پیگیری تالی‌های انبار</Text>
        </div>
        <Group gap="sm">
          <Button
            variant="default" radius="md" leftSection={<IconRefresh size={18} />}
            onClick={() => refetch()} loading={isFetching && !isLoading}
          >
            بروزرسانی
          </Button>
          <Button
            radius="md" leftSection={<IconPlus size={18} />}
            onClick={() => navigate('/tally/new')}
          >
            افزودن تالی
          </Button>
        </Group>
      </Group>

      {/* ---- summary stat cards ---- */}
      <SimpleGrid cols={{ base: 1, xs: 2 }} spacing="md" mb="lg">
        {isLoading ? (
          Array.from({ length: 2 }).map((_, i) => <Skeleton key={i} height={92} radius="lg" />)
        ) : (
          <>
            <div className="tlp-card"><StatCard icon={<IconBox />} value={stats.total} label="کل تالی‌ها" color="blue" /></div>
            <div className="tlp-card"><StatCard icon={<IconClock />} value={stats.pending} label="عملیات در انتظار" color="orange" /></div>
          </>
        )}
      </SimpleGrid>

      {/* ---- toolbar ---- */}
      <Paper radius="md" p="sm" withBorder shadow="xs" mb="md">
        <Group gap="sm" wrap="wrap" align="center">
          <TextInput
            radius="md" placeholder="جستجو در تالی‌ها…"
            leftSection={<IconSearch size={16} />}
            value={search} onChange={(e) => setSearch(e.currentTarget.value)}
            style={{ flex: '1 1 240px', minWidth: 200 }}
          />
          <Select
            radius="md" placeholder="انبار" clearable
            leftSection={<IconWarehouse size={16} />}
            data={warehouseOptions} value={warehouse} onChange={setWarehouse}
            disabled={warehouseOptions.length === 0}
            w={150}
          />
          <Select
            radius="md" placeholder="بازه تاریخ" clearable
            leftSection={<IconCalendar size={16} />}
            data={[
              { value: 'today', label: 'امروز' },
              { value: '7', label: '۷ روز اخیر' },
              { value: '30', label: '۳۰ روز اخیر' },
            ]}
            value={dateRange} onChange={setDateRange} w={150}
          />
          <Select
            radius="md" placeholder="کالای خطرناک" clearable
            leftSection={<IconAlert size={16} />}
            data={[
              { value: 'yes', label: 'دارد' },
              { value: 'no', label: 'ندارد' },
            ]}
            value={danger} onChange={setDanger} w={150}
          />
        </Group>
      </Paper>

      {/* ---- table / states ---- */}
      <Paper radius="md" withBorder shadow="sm" style={{ overflow: 'hidden' }}>
        {isLoading && <TableSkeleton />}

        {isError && (
          <Center py={64}>
            <Stack align="center" gap="xs">
              <ThemeIcon size={48} radius="xl" variant="light" color="red"><IconAlert size={26} /></ThemeIcon>
              <Text fw={600}>بارگذاری تالی‌ها ناموفق بود</Text>
              <Text size="sm" c="dimmed">اتصال را بررسی کنید و دوباره تلاش کنید.</Text>
              <Button mt="xs" variant="light" radius="md" leftSection={<IconRefresh size={16} />} onClick={() => refetch()}>
                تلاش دوباره
              </Button>
            </Stack>
          </Center>
        )}

        {data && data.length === 0 && (
          <Center py={72}>
            <Stack align="center" gap="sm" maw={360} ta="center">
              <ThemeIcon size={72} radius="xl" variant="light" color="blue"><IconInbox size={38} /></ThemeIcon>
              <Text fw={600} size="lg">هنوز تالی‌ای ثبت نشده است</Text>
              <Text size="sm" c="dimmed">اولین تالی انبار را بسازید تا اینجا نمایش داده شود.</Text>
              <Button mt="xs" radius="md" leftSection={<IconPlus size={18} />} onClick={() => navigate('/tally/new')}>
                افزودن تالی
              </Button>
            </Stack>
          </Center>
        )}

        {data && data.length > 0 && filtered.length === 0 && (
          <Center py={64}>
            <Stack align="center" gap="xs">
              <ThemeIcon size={48} radius="xl" variant="light" color="gray"><IconSearch size={24} /></ThemeIcon>
              <Text fw={600}>نتیجه‌ای یافت نشد</Text>
              <Text size="sm" c="dimmed">هیچ تالی‌ای با این فیلترها مطابقت ندارد.</Text>
              <Button mt="xs" variant="subtle" radius="md" onClick={clearFilters}>پاک کردن فیلترها</Button>
            </Stack>
          </Center>
        )}

        {data && data.length > 0 && filtered.length > 0 && (
          <Table.ScrollContainer minWidth={860}>
            <Table striped highlightOnHover stickyHeader verticalSpacing="sm" horizontalSpacing="md" withRowBorders>
              <Table.Thead style={{ background: 'var(--mantine-color-gray-light)' }}>
                <Table.Tr>
                  <Table.Th>شماره تالی</Table.Th>
                  <Table.Th>نام مرز</Table.Th>
                  <Table.Th>مبدا (کشور)</Table.Th>
                  <Table.Th>نام شرکت حمل</Table.Th>
                  <Table.Th>صاحب کالا</Table.Th>
                  <Table.Th>تاریخ ورود به مرز</Table.Th>
                  <Table.Th>تاریخ تخلیه</Table.Th>
                  <Table.Th>وضعیت</Table.Th>
                  <Table.Th style={{ textAlign: 'center' }}>عملیات</Table.Th>
                </Table.Tr>
              </Table.Thead>
              <Table.Tbody>
                {filtered.map((row) => {
                  const unloaded = Boolean(row.date_unloading)
                  const insured = (row.is_bimeh ?? '').trim() === 'yes'
                  return (
                    <Table.Tr
                      key={row.id_tali} className="tlp-row"
                      style={{ cursor: 'pointer' }}
                      onClick={() => navigate(tallyPath(row))}
                    >
                      <Table.Td><Text fw={600}><TallyNumber value={row.tali_number} /></Text></Table.Td>
                      <Table.Td>{row.marze_name ?? '—'}</Table.Td>
                      <Table.Td>{row.country_name ?? '—'}</Table.Td>
                      <Table.Td>{row.company_name?.trim() || '—'}</Table.Td>
                      <Table.Td>{row.owner_name?.trim() || '—'}</Table.Td>
                      <Table.Td>{isoToJalali(row.date_enter_marze)}</Table.Td>
                      <Table.Td>{isoToJalali(row.date_unloading)}</Table.Td>
                      <Table.Td>
                        <Group gap={6} wrap="nowrap">
                          <Badge color={unloaded ? 'teal' : 'orange'} variant="light" radius="sm">
                            {unloaded ? 'تخلیه شده' : 'در انتظار تخلیه'}
                          </Badge>
                          {insured && <Badge color="blue" variant="light" radius="sm">بیمه</Badge>}
                        </Group>
                      </Table.Td>
                      <Table.Td style={{ textAlign: 'center' }}>
                        <Tooltip label="مشاهده جزئیات" withArrow>
                          <ActionIcon
                            variant="subtle" color="blue" radius="md"
                            onClick={(e) => { e.stopPropagation(); navigate(tallyPath(row)) }}
                            aria-label="مشاهده جزئیات تالی"
                          >
                            <IconEye size={18} />
                          </ActionIcon>
                        </Tooltip>
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
          نمایش {filtered.length.toLocaleString('fa-IR')} از {rows.length.toLocaleString('fa-IR')} تالی
        </Text>
      )}
    </Box>
  )
}

function TableSkeleton() {
  return (
    <Box p="md">
      <Skeleton height={34} radius="sm" mb="sm" />
      {Array.from({ length: 6 }).map((_, i) => (
        <Group key={i} gap="md" mb="sm" wrap="nowrap">
          {Array.from({ length: COLS }).map((__, j) => (
            <Skeleton key={j} height={20} radius="sm" style={{ flex: j === 0 ? '0 0 70px' : 1 }} />
          ))}
        </Group>
      ))}
    </Box>
  )
}
