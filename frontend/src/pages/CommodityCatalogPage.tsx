// import { useRef, useState } from 'react'
// import { useQuery, useMutation, useQueryClient, keepPreviousData } from '@tanstack/react-query'
// import {
//   Title, Group, Button, TextInput, Table, Paper, Loader, Center, Text,
//   Pagination, Badge, Modal, Stack, FileButton,
// } from '@mantine/core'
// import { useDebouncedValue } from '@mantine/hooks'
// import { apiGet, apiSend, apiUpload } from '../api/client'
// import { StorageGroupSelect } from '../components/StorageGroupSelect'
// import type { Commodity } from '../components/CommoditySelect'

// /**
//  * CommodityCatalogPage — the «کالاها» page, now backed by FA_COMMODITY_CATALOG.
//  * Server-side search (HS prefix OR partial Persian description) + pagination, so the
//  * ~9k rows are never all loaded into the browser. Admins can import the yearly Excel and
//  * assign each commodity's storage-price group (STORAGE_GROUP_ID). The storage-price-group
//  * screen itself is untouched and lives separately.
//  */

// const PAGE_SIZE = 20

// type SearchResponse = { items: Commodity[]; total: number }

// export function CommodityCatalogPage() {
//   const qc = useQueryClient()
//   const [search, setSearch] = useState('')
//   const [debounced] = useDebouncedValue(search, 300)
//   const [page, setPage] = useState(1)
//   const [editing, setEditing] = useState<Commodity | null>(null)
//   const [groupId, setGroupId] = useState<number | null>(null)
//   const [importMsg, setImportMsg] = useState<string | null>(null)
//   const resetRef = useRef<() => void>(null)

//   // reset to page 1 whenever the search term changes
//   const offset = (page - 1) * PAGE_SIZE
//   const { data, isLoading, isError, isFetching } = useQuery({
//     queryKey: ['commodity', debounced, page],
//     queryFn: () =>
//       apiGet<SearchResponse>(
//         `/commodity?q=${encodeURIComponent(debounced)}&limit=${PAGE_SIZE}&offset=${offset}`,
//       ),
//     placeholderData: keepPreviousData,
//   })

//   const totalPages = data ? Math.max(1, Math.ceil(data.total / PAGE_SIZE)) : 1

//   const importMutation = useMutation({
//     mutationFn: (file: File) =>
//       apiUpload<{ processed: number; inserted: number; updated: number }>(
//         '/commodity/import',
//         file,
//       ),
//     onSuccess: (r) => {
//       setImportMsg(`ایمپورت شد: ${r.processed} ردیف (${r.inserted} جدید، ${r.updated} بروزرسانی)`)
//       qc.invalidateQueries({ queryKey: ['commodity'] })
//     },
//     onError: (e) => setImportMsg(`خطا: ${(e as Error).message}`),
//   })

//   const saveGroupMutation = useMutation({
//     mutationFn: (payload: { id: number; storage_group_id: number | null }) =>
//       apiSend(`/commodity/${payload.id}`, 'PUT', { storage_group_id: payload.storage_group_id }),
//     onSuccess: () => {
//       qc.invalidateQueries({ queryKey: ['commodity'] })
//       setEditing(null)
//     },
//   })

//   function openEdit(c: Commodity) {
//     setEditing(c)
//     setGroupId(c.storage_group_id)
//   }

//   function onSearchChange(v: string) {
//     setSearch(v)
//     setPage(1)
//   }

//   return (
//     <div dir="rtl">
//       <Group justify="space-between" mb="md">
//         <Title order={2}>کاتالوگ کالاها</Title>
//         <Group>
//           <FileButton
//             resetRef={resetRef}
//             accept=".xlsx,.xlsm"
//             onChange={(f) => {
//               if (f) importMutation.mutate(f)
//               resetRef.current?.()
//             }}
//           >
//             {(props) => (
//               <Button {...props} variant="light" loading={importMutation.isPending}>
//                 ایمپورت اکسل
//               </Button>
//             )}
//           </FileButton>
//         </Group>
//       </Group>

//       {importMsg && (
//         <Text mb="sm" c={importMsg.startsWith('خطا') ? 'red' : 'teal'}>{importMsg}</Text>
//       )}

//       <TextInput
//         mb="md"
//         placeholder="جستجو بر اساس HS Code یا بخشی از شرح فارسی…"
//         value={search}
//         onChange={(e) => onSearchChange(e.currentTarget.value)}
//       />

//       <Paper shadow="xs" p="md">
//         {isLoading && <Center py="xl"><Loader /></Center>}
//         {isError && <Center py="xl"><Text c="red">خطا در بارگذاری کاتالوگ.</Text></Center>}

//         {data && data.items.length === 0 && (
//           <Center py="xl"><Text c="dimmed">موردی یافت نشد.</Text></Center>
//         )}

//         {data && data.items.length > 0 && (
//           <>
//             <Table striped highlightOnHover withTableBorder>
//               <Table.Thead>
//                 <Table.Tr>
//                   <Table.Th>HS Code</Table.Th>
//                   <Table.Th>شرح</Table.Th>
//                   <Table.Th>واحد</Table.Th>
//                   <Table.Th>حقوق گمرکی</Table.Th>
//                   <Table.Th>سود بازرگانی</Table.Th>
//                   <Table.Th>گروه قیمت انبار</Table.Th>
//                   <Table.Th>عملیات</Table.Th>
//                 </Table.Tr>
//               </Table.Thead>
//               <Table.Tbody>
//                 {data.items.map((c) => (
//                   <Table.Tr key={c.id}>
//                     <Table.Td>{c.hs_code}</Table.Td>
//                     <Table.Td>{c.description_fa ?? '—'}</Table.Td>
//                     <Table.Td>{c.unit ?? '—'}</Table.Td>
//                     <Table.Td>{c.customs_duty ?? '—'}</Table.Td>
//                     <Table.Td>{c.commercial_profit ?? '—'}</Table.Td>
//                     <Table.Td>
//                       {c.storage_group_code
//                         ? <Badge variant="light">{c.storage_group_code}</Badge>
//                         : <Text c="dimmed" size="sm">تعیین نشده</Text>}
//                     </Table.Td>
//                     <Table.Td>
//                       <Button size="xs" variant="light" onClick={() => openEdit(c)}>
//                         گروه قیمت
//                       </Button>
//                     </Table.Td>
//                   </Table.Tr>
//                 ))}
//               </Table.Tbody>
//             </Table>

//             <Group justify="space-between" mt="md">
//               <Text size="sm" c="dimmed">
//                 {data.total.toLocaleString('fa-IR')} کالا{isFetching ? ' …' : ''}
//               </Text>
//               <Pagination value={page} onChange={setPage} total={totalPages} />
//             </Group>
//           </>
//         )}
//       </Paper>

//       <Modal
//         opened={editing != null}
//         onClose={() => setEditing(null)}
//         title={editing ? `گروه قیمت انبار — ${editing.hs_code}` : ''}
//       >
//         <Stack>
//           <StorageGroupSelect
//             label="گروه قیمت انبار"
//             value={groupId}
//             onChange={setGroupId}
//           />
//           <Group>
//             <Button
//               loading={saveGroupMutation.isPending}
//               onClick={() => editing && saveGroupMutation.mutate({ id: editing.id, storage_group_id: groupId })}
//             >
//               ذخیره
//             </Button>
//             <Button variant="subtle" onClick={() => setEditing(null)}>لغو</Button>
//           </Group>
//         </Stack>
//       </Modal>
//     </div>
//   )
// }

import { useRef, useState, type CSSProperties } from 'react'
import { useQuery, useMutation, useQueryClient, keepPreviousData } from '@tanstack/react-query'
import {
  Box, Text, Group, Button, TextInput, Table, Paper, Center, Stack,
  Pagination, Badge, Modal, FileButton, ThemeIcon, Skeleton, Tooltip, ActionIcon, Alert,
} from '@mantine/core'
import { useDebouncedValue } from '@mantine/hooks'
import { apiGet, apiSend, apiUpload } from '../api/client'
import { StorageGroupSelect } from '../components/StorageGroupSelect'
import { PageHeader } from '../components/PageHeader'
import { BackButton } from '../components/BackButton'
import type { Commodity } from '../components/CommoditySelect'
import { IconSearch, IconUpload, IconEdit, IconInbox, IconAlert } from '../components/icons'

/**
 * CommodityCatalogPage — the «کالاها» page, backed by FA_COMMODITY_CATALOG.
 * Server-side search (HS prefix OR partial Persian description) + pagination, so the
 * ~9k rows are never all loaded into the browser. Admins can import the yearly Excel and
 * assign each commodity's storage-price group (STORAGE_GROUP_ID). The storage-price-group
 * screen itself is untouched and lives separately.
 *
 * Presentational refresh only — the query, pagination, import, and save-group logic below
 * are unchanged.
 */

const PAGE_SIZE = 20

type SearchResponse = { items: Commodity[]; total: number }

export function CommodityCatalogPage() {
  const qc = useQueryClient()
  const [search, setSearch] = useState('')
  const [debounced] = useDebouncedValue(search, 300)
  const [page, setPage] = useState(1)
  const [editing, setEditing] = useState<Commodity | null>(null)
  const [groupId, setGroupId] = useState<number | null>(null)
  const [importMsg, setImportMsg] = useState<string | null>(null)
  const resetRef = useRef<() => void>(null)

  const offset = (page - 1) * PAGE_SIZE
  const { data, isLoading, isError, isFetching } = useQuery({
    queryKey: ['commodity', debounced, page],
    queryFn: () =>
      apiGet<SearchResponse>(
        `/commodity?q=${encodeURIComponent(debounced)}&limit=${PAGE_SIZE}&offset=${offset}`,
      ),
    placeholderData: keepPreviousData,
  })

  const totalPages = data ? Math.max(1, Math.ceil(data.total / PAGE_SIZE)) : 1

  const importMutation = useMutation({
    mutationFn: (file: File) =>
      apiUpload<{ processed: number; inserted: number; updated: number }>('/commodity/import', file),
    onSuccess: (r) => {
      setImportMsg(`ایمپورت شد: ${r.processed} ردیف (${r.inserted} جدید، ${r.updated} بروزرسانی)`)
      qc.invalidateQueries({ queryKey: ['commodity'] })
    },
    onError: (e) => setImportMsg(`خطا: ${(e as Error).message}`),
  })

  const saveGroupMutation = useMutation({
    mutationFn: (payload: { id: number; storage_group_id: number | null }) =>
      apiSend(`/commodity/${payload.id}`, 'PUT', { storage_group_id: payload.storage_group_id }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['commodity'] })
      setEditing(null)
    },
  })

  function openEdit(c: Commodity) {
    setEditing(c)
    setGroupId(c.storage_group_id)
  }

  function onSearchChange(v: string) {
    setSearch(v)
    setPage(1)
  }

  const items = data?.items ?? []

  return (
    <Box dir="rtl" style={{ maxWidth: 1280, margin: '0 auto' }}>
      {/* header */}
      <PageHeader
        title="کاتالوگ کالاها"
        subtitle="جستجو، ایمپورت و تعیین گروه قیمت کالاها"
        actions={
          <>
            <FileButton
              resetRef={resetRef}
              accept=".xlsx,.xlsm"
              onChange={(f) => { if (f) importMutation.mutate(f); resetRef.current?.() }}
            >
              {(props) => (
                <Button {...props} radius="md" variant="white" leftSection={<IconUpload size={18} />}
                  loading={importMutation.isPending}>
                  ایمپورت اکسل
                </Button>
              )}
            </FileButton>
            <BackButton to="/base-data" />
          </>
        }
      />

      {importMsg && (
        <Alert
          mb="md" radius="md" variant="light"
          color={importMsg.startsWith('خطا') ? 'red' : 'teal'}
          withCloseButton onClose={() => setImportMsg(null)}
        >
          {importMsg}
        </Alert>
      )}

      {/* toolbar */}
      <Paper radius="md" p="sm" withBorder shadow="xs" mb="md"
        bg="var(--app-accent-light, var(--mantine-color-gray-0))"
        style={{ borderColor: 'var(--app-accent-light-hover, var(--mantine-color-gray-3))' }}>
        <TextInput
          radius="md"
          placeholder="جستجو بر اساس HS Code یا بخشی از شرح فارسی…"
          leftSection={<IconSearch size={16} />}
          value={search}
          onChange={(e) => onSearchChange(e.currentTarget.value)}
        />
      </Paper>

      {/* table */}
      <Paper radius="md" withBorder shadow="sm" style={{ overflow: 'hidden' }}>
        {isLoading ? (
          <Box p="md">
            <Skeleton height={34} radius="sm" mb="sm" />
            {Array.from({ length: 8 }).map((_, i) => (
              <Group key={i} gap="md" mb="sm" wrap="nowrap">
                {Array.from({ length: 7 }).map((__, j) => (
                  <Skeleton key={j} height={20} radius="sm" style={{ flex: j === 0 ? '0 0 90px' : 1 }} />
                ))}
              </Group>
            ))}
          </Box>
        ) : isError ? (
          <Center py={56}>
            <Stack align="center" gap="xs">
              <ThemeIcon size={44} radius="xl" variant="light" color="red"><IconAlert size={24} /></ThemeIcon>
              <Text fw={600}>بارگذاری کاتالوگ ناموفق بود</Text>
              <Text size="sm" c="dimmed">اتصال را بررسی کنید و دوباره تلاش کنید.</Text>
            </Stack>
          </Center>
        ) : items.length === 0 ? (
          <Center py={56}>
            <Stack align="center" gap="xs">
              <ThemeIcon size={44} radius="xl" variant="light" color="gray"><IconInbox size={24} /></ThemeIcon>
              <Text fw={600}>موردی یافت نشد</Text>
              <Text size="sm" c="dimmed">عبارت جستجو را تغییر دهید.</Text>
            </Stack>
          </Center>
        ) : (
          <Table.ScrollContainer minWidth={900}>
            <Table
              striped highlightOnHover stickyHeader verticalSpacing="sm" horizontalSpacing="md" withRowBorders
              style={{
                '--table-striped-color': 'var(--app-accent-light, var(--mantine-color-gray-0))',
                '--table-highlight-on-hover-color':
                  'var(--app-accent-light-hover, var(--mantine-color-gray-1))',
              } as CSSProperties}
            >
              <Table.Thead style={{ background: 'var(--app-accent-filled, var(--mantine-color-gray-light))', color: 'var(--mantine-color-white)' }}>
                <Table.Tr>
                  <Table.Th>HS Code</Table.Th>
                  <Table.Th>شرح</Table.Th>
                  <Table.Th>واحد</Table.Th>
                  <Table.Th>حقوق گمرکی</Table.Th>
                  <Table.Th>سود بازرگانی</Table.Th>
                  <Table.Th>گروه قیمت انبار</Table.Th>
                  <Table.Th style={{ textAlign: 'center' }}>عملیات</Table.Th>
                </Table.Tr>
              </Table.Thead>
              <Table.Tbody>
                {items.map((c) => (
                  <Table.Tr key={c.id}>
                    <Table.Td>{c.hs_code}</Table.Td>
                    <Table.Td>{c.description_fa ?? '—'}</Table.Td>
                    <Table.Td>{c.unit ?? '—'}</Table.Td>
                    <Table.Td>{c.customs_duty ?? '—'}</Table.Td>
                    <Table.Td>{c.commercial_profit ?? '—'}</Table.Td>
                    <Table.Td>
                      {c.storage_group_code
                        ? <Badge variant="light" radius="sm">{c.storage_group_code}</Badge>
                        : <Text c="dimmed" size="sm">تعیین نشده</Text>}
                    </Table.Td>
                    <Table.Td style={{ textAlign: 'center' }}>
                      <Tooltip label="تعیین گروه قیمت انبار" withArrow>
                        <ActionIcon variant="subtle" color="blue" radius="md" aria-label="تعیین گروه قیمت"
                          onClick={() => openEdit(c)}>
                          <IconEdit size={18} />
                        </ActionIcon>
                      </Tooltip>
                    </Table.Td>
                  </Table.Tr>
                ))}
              </Table.Tbody>
            </Table>
          </Table.ScrollContainer>
        )}
      </Paper>

      {items.length > 0 && (
        <Group justify="space-between" mt="sm" wrap="wrap" gap="sm">
          <Text size="sm" c="dimmed">
            {data!.total.toLocaleString('fa-IR')} کالا{isFetching ? ' …' : ''}
          </Text>
          <Pagination value={page} onChange={setPage} total={totalPages} radius="md" />
        </Group>
      )}

      <Modal
        opened={editing != null}
        onClose={() => setEditing(null)}
        title={editing ? `گروه قیمت انبار — ${editing.hs_code}` : ''}
        radius="md" centered overlayProps={{ backgroundOpacity: 0.55, blur: 2 }}
        styles={{ title: { fontWeight: 700 } }}
      >
        <Stack gap="sm">
          <StorageGroupSelect label="گروه قیمت انبار" value={groupId} onChange={setGroupId} />
          <Group mt="md" gap="sm">
            <Button
              radius="md"
              loading={saveGroupMutation.isPending}
              onClick={() => editing && saveGroupMutation.mutate({ id: editing.id, storage_group_id: groupId })}
            >
              ذخیره
            </Button>
            <Button variant="default" radius="md" onClick={() => setEditing(null)}>لغو</Button>
          </Group>
        </Stack>
      </Modal>
    </Box>
  )
}