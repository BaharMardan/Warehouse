// import { useState } from 'react'
// import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
// import { Container, Title, Button, Group } from '@mantine/core'
// import { DataTable, type Column } from './DataTable'
// import { CrudFormModal, type FieldDef } from './CrudFormModal'
// import { makeCrudApi } from '../api/crud'

// export interface CrudConfig<T> {
//   route: string           // browser URL, e.g. '/kala'
//   path: string            // API path, e.g. '/items'
//   queryKey: string        // cache key, e.g. 'kala'
//   title: string           // page heading, e.g. 'کالاها'
//   entity: string          // singular noun for buttons/messages, e.g. 'کالا'
//   pkField: keyof T        // primary key field, e.g. 'id_kala'
//   columns: Column<T>[]    // display columns (actions added automatically)
//   fields: FieldDef[]      // form fields
// }

// export function CrudResource<T extends Record<string, any>>({ config }: { config: CrudConfig<T> }) {
//   const api = makeCrudApi<T>(config.path)
//   const qc = useQueryClient()
//   const { data, isLoading, error } = useQuery({ queryKey: [config.queryKey], queryFn: api.list })

//   const [open, setOpen] = useState(false)
//   const [editing, setEditing] = useState<T | null>(null)

//   const refresh = () => qc.invalidateQueries({ queryKey: [config.queryKey] })

//   const save = useMutation({
//     mutationFn: (values: Record<string, unknown>) =>
//       editing ? api.update(Number(editing[config.pkField]), values) : api.create(values),
//     onSuccess: () => { refresh(); setOpen(false) },
//   })
//   const remove = useMutation({ mutationFn: (id: number) => api.remove(id), onSuccess: refresh })

//   const columns: Column<T>[] = [
//     ...config.columns,
//     {
//       key: '__actions',
//       label: 'عملیات',
//       render: (row) => (
//         <Group gap="xs">
//           <Button size="xs" variant="light" onClick={() => { setEditing(row); setOpen(true) }}>
//             ویرایش
//           </Button>
//           <Button
//             size="xs"
//             variant="light"
//             color="red"
//             onClick={() => confirm(`حذف این ${config.entity}؟`) && remove.mutate(Number(row[config.pkField]))}
//           >
//             حذف
//           </Button>
//         </Group>
//       ),
//     },
//   ]

//   return (
//     <Container my="lg">
//       <Group justify="space-between" mb="md">
//         <Title order={2}>{config.title}</Title>
//         <Button onClick={() => { setEditing(null); setOpen(true) }}>{`افزودن ${config.entity}`}</Button>
//       </Group>
//       <DataTable
//         columns={columns}
//         data={data}
//         isLoading={isLoading}
//         error={error}
//         getRowKey={(row) => Number(row[config.pkField])}
//       />
//       <CrudFormModal
//         opened={open}
//         onClose={() => setOpen(false)}
//         onSubmit={(values) => save.mutate(values)}
//         fields={config.fields}
//         initial={editing}
//         loading={save.isPending}
//         title={editing ? `ویرایش ${config.entity}` : `افزودن ${config.entity}`}
//       />
//     </Container>
//   )
// }

import { useMemo, useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import {
  Box, Title, Text, Button, Group, Paper, TextInput, Tooltip, ActionIcon,
  ThemeIcon, Stack, Center,
} from '@mantine/core'
import { useDebouncedValue } from '@mantine/hooks'
import { DataTable, type Column } from './DataTable'
import { CrudFormModal, type FieldDef } from './CrudFormModal'
import { makeCrudApi } from '../api/crud'
import { IconSearch, IconRefresh, IconPlus, IconEdit, IconTrash, IconInbox } from './icons'

export interface CrudConfig<T> {
  route: string           // browser URL, e.g. '/kala'
  path: string            // API path, e.g. '/items'
  queryKey: string        // cache key, e.g. 'kala'
  title: string           // page heading, e.g. 'کالاها'
  entity: string          // singular noun for buttons/messages, e.g. 'کالا'
  pkField: keyof T        // primary key field, e.g. 'id_kala'
  columns: Column<T>[]    // display columns (actions added automatically)
  fields: FieldDef[]      // form fields
  listFilter?: Partial<Record<keyof T, unknown>> // fixed lookup scope, e.g. one term category
  fixedValues?: Record<string, unknown>          // values always included in create/update payloads
}

// Persian/Arabic-Indic digits -> Latin so search matches either script.
const normalizeDigits = (s: string) =>
  s.replace(/[\u06F0-\u06F9]/g, (d) => String(d.charCodeAt(0) - 0x06f0))
   .replace(/[\u0660-\u0669]/g, (d) => String(d.charCodeAt(0) - 0x0660))

export function CrudResource<T extends Record<string, any>>({ config }: { config: CrudConfig<T> }) {
  const api = makeCrudApi<T>(config.path)
  const qc = useQueryClient()
  const { data, isLoading, error, isFetching } = useQuery({ queryKey: [config.queryKey], queryFn: api.list })

  const [open, setOpen] = useState(false)
  const [editing, setEditing] = useState<T | null>(null)
  const [search, setSearch] = useState('')
  const [debounced] = useDebouncedValue(search, 200)

  const refresh = () => {
    qc.invalidateQueries({ queryKey: [config.queryKey] })
    if (config.path === '/terms') {
      qc.invalidateQueries({ queryKey: ['refselect', '/terms'] })
      qc.invalidateQueries({ queryKey: ['term-values'] })
    }
  }

  const save = useMutation({
    mutationFn: (values: Record<string, unknown>) => {
      const payload = { ...values, ...(config.fixedValues ?? {}) }
      return editing ? api.update(Number(editing[config.pkField]), payload) : api.create(payload)
    },
    onSuccess: () => { refresh(); setOpen(false) },
  })
  const remove = useMutation({ mutationFn: (id: number) => api.remove(id), onSuccess: refresh })

  const openAdd = () => {
    save.reset()
    setEditing(null)
    setOpen(true)
  }
  const closeForm = () => {
    save.reset()
    setOpen(false)
  }

  const records = useMemo(() => {
    const rows = data ?? []
    const filters = Object.entries(config.listFilter ?? {})
    if (filters.length === 0) return rows
    return rows.filter((row) =>
      filters.every(([key, expected]) => String(row[key] ?? '') === String(expected ?? '')),
    )
  }, [data, config.listFilter])
  const searchable = useMemo(
    () => config.columns.filter((c) => c.field).map((c) => c.field as keyof T),
    [config.columns],
  )
  const filtered = useMemo(() => {
    const q = normalizeDigits(debounced.trim().toLowerCase())
    if (!q) return records
    return records.filter((row) =>
      normalizeDigits(searchable.map((f) => String(row[f] ?? '')).join(' ').toLowerCase()).includes(q),
    )
  }, [records, debounced, searchable])

  const columns: Column<T>[] = [
    ...config.columns,
    {
      key: '__actions',
      label: 'عملیات',
      render: (row) => (
        <Group gap={4} justify="center" wrap="nowrap">
          <Tooltip label="ویرایش" withArrow>
            <ActionIcon variant="subtle" color="blue" radius="md" aria-label="ویرایش"
              onClick={() => { save.reset(); setEditing(row); setOpen(true) }}>
              <IconEdit size={18} />
            </ActionIcon>
          </Tooltip>
          <Tooltip label="حذف" withArrow>
            <ActionIcon variant="subtle" color="red" radius="md" aria-label="حذف"
              onClick={() => confirm(`حذف این ${config.entity}؟`) && remove.mutate(Number(row[config.pkField]))}>
              <IconTrash size={18} />
            </ActionIcon>
          </Tooltip>
        </Group>
      ),
    },
  ]

  const emptyContent =
    records.length === 0 ? (
      <Center py={64}>
        <Stack align="center" gap="sm" ta="center" maw={360}>
          <ThemeIcon size={64} radius="xl" variant="light" color="blue"><IconInbox size={34} /></ThemeIcon>
          <Text fw={600} size="lg">{`هنوز ${config.entity}‌ای ثبت نشده است`}</Text>
          <Text size="sm" c="dimmed">{`اولین ${config.entity} را اضافه کنید تا اینجا نمایش داده شود.`}</Text>
          <Button mt="xs" radius="md" leftSection={<IconPlus size={18} />} onClick={openAdd}>
            {`افزودن ${config.entity}`}
          </Button>
        </Stack>
      </Center>
    ) : (
      <Center py={64}>
        <Stack align="center" gap="xs">
          <ThemeIcon size={44} radius="xl" variant="light" color="gray"><IconSearch size={24} /></ThemeIcon>
          <Text fw={600}>نتیجه‌ای یافت نشد</Text>
          <Text size="sm" c="dimmed">موردی با این جستجو مطابقت ندارد.</Text>
          <Button mt="xs" variant="subtle" radius="md" onClick={() => setSearch('')}>پاک کردن جستجو</Button>
        </Stack>
      </Center>
    )

  return (
    <Box dir="rtl" style={{ maxWidth: 1280, margin: '0 auto' }}>
      {/* header */}
      <Group justify="space-between" align="flex-end" mb="lg" wrap="wrap" gap="sm">
        <div>
          <Title order={2} fw={700}>{config.title}</Title>
          <Text c="dimmed" size="sm" mt={4}>{`مدیریت ${config.title}`}</Text>
        </div>
        <Button radius="md" leftSection={<IconPlus size={18} />} onClick={openAdd}>
          {`افزودن ${config.entity}`}
        </Button>
      </Group>

      {/* toolbar */}
      <Paper radius="md" p="sm" withBorder shadow="xs" mb="md">
        <Group gap="sm" wrap="wrap" align="center">
          <TextInput
            radius="md" placeholder={`جستجو در ${config.title}…`}
            leftSection={<IconSearch size={16} />}
            value={search} onChange={(e) => setSearch(e.currentTarget.value)}
            style={{ flex: '1 1 260px', minWidth: 200 }}
          />
          <Button
            variant="default" radius="md" leftSection={<IconRefresh size={16} />}
            onClick={refresh} loading={isFetching && !isLoading}
          >
            بروزرسانی
          </Button>
        </Group>
      </Paper>

      <DataTable
        columns={columns}
        data={isLoading ? undefined : filtered}
        isLoading={isLoading}
        error={error}
        getRowKey={(row) => Number(row[config.pkField])}
        emptyContent={emptyContent}
      />

      {records.length > 0 && (
        <Text size="xs" c="dimmed" mt="sm" ta="center">
          نمایش {filtered.length.toLocaleString('fa-IR')} از {records.length.toLocaleString('fa-IR')} مورد
        </Text>
      )}

      <CrudFormModal
        opened={open}
        onClose={closeForm}
        onSubmit={(values) => save.mutate(values)}
        fields={config.fields}
        initial={editing}
        loading={save.isPending}
        error={save.isError ? 'ذخیره انجام نشد. لطفاً دوباره تلاش کنید.' : null}
        title={editing ? `ویرایش ${config.entity}` : `افزودن ${config.entity}`}
      />
    </Box>
  )
}
