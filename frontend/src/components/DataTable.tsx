// import type { ReactNode } from 'react'
// import { Table, Loader, Text } from '@mantine/core'

// export interface Column<T> {
//   key: string                       // unique column id (React key)
//   label: string
//   field?: keyof T                   // which data field to show by default
//   render?: (row: T) => ReactNode    // OR a custom cell (actions, badges, dates…)
// }

// interface DataTableProps<T> {
//   columns: Column<T>[]
//   data: T[] | undefined
//   isLoading?: boolean
//   error?: unknown
//   getRowKey: (row: T) => string | number
// }

// export function DataTable<T>({ columns, data, isLoading, error, getRowKey }: DataTableProps<T>) {
//   if (isLoading) return <Loader />
//   if (error) return <Text c="red">خطا در بارگذاری اطلاعات</Text>

//   return (
//     <Table striped withTableBorder highlightOnHover>
//       <Table.Thead>
//         <Table.Tr>
//           {columns.map((col) => (
//             <Table.Th key={col.key}>{col.label}</Table.Th>
//           ))}
//         </Table.Tr>
//       </Table.Thead>
//       <Table.Tbody>
//         {data?.map((row) => (
//           <Table.Tr key={getRowKey(row)}>
//             {columns.map((col) => (
//               <Table.Td key={col.key}>
//                 {col.render ? col.render(row) : String(col.field ? row[col.field] ?? '' : '')}
//               </Table.Td>
//             ))}
//           </Table.Tr>
//         ))}
//       </Table.Tbody>
//     </Table>
//   )
// }

import type { ReactNode } from 'react'
import { Table, Text, Paper, Skeleton, Center, Stack, ThemeIcon, Box, Group } from '@mantine/core'
import { IconInbox, IconAlert } from './icons'

export interface Column<T> {
  key: string                       // unique column id (React key)
  label: string
  field?: keyof T                   // which data field to show by default
  render?: (row: T) => ReactNode    // OR a custom cell (actions, badges, dates…)
}

interface DataTableProps<T> {
  columns: Column<T>[]
  data: T[] | undefined
  isLoading?: boolean
  error?: unknown
  getRowKey: (row: T) => string | number
  onRowClick?: (row: T) => void
  emptyContent?: ReactNode          // shown when there are no rows (custom empty state)
  minWidth?: number
}

export function DataTable<T>({
  columns, data, isLoading, error, getRowKey, onRowClick, emptyContent, minWidth = 720,
}: DataTableProps<T>) {
  const shell = (child: ReactNode) => (
    <Paper radius="md" withBorder shadow="sm" style={{ overflow: 'hidden' }}>{child}</Paper>
  )

  if (isLoading) {
    return shell(
      <Box p="md">
        <Skeleton height={34} radius="sm" mb="sm" />
        {Array.from({ length: 6 }).map((_, i) => (
          <Group key={i} gap="md" mb="sm" wrap="nowrap">
            {columns.map((c, j) => (
              <Skeleton key={c.key} height={20} radius="sm" style={{ flex: j === 0 ? '0 0 80px' : 1 }} />
            ))}
          </Group>
        ))}
      </Box>,
    )
  }

  if (error) {
    return shell(
      <Center py={56}>
        <Stack align="center" gap="xs">
          <ThemeIcon size={44} radius="xl" variant="light" color="red"><IconAlert size={24} /></ThemeIcon>
          <Text fw={600}>بارگذاری اطلاعات ناموفق بود</Text>
          <Text size="sm" c="dimmed">اتصال را بررسی کنید و دوباره تلاش کنید.</Text>
        </Stack>
      </Center>,
    )
  }

  if (!data || data.length === 0) {
    return shell(
      emptyContent ?? (
        <Center py={56}>
          <Stack align="center" gap="xs">
            <ThemeIcon size={44} radius="xl" variant="light" color="gray"><IconInbox size={24} /></ThemeIcon>
            <Text fw={600}>موردی برای نمایش نیست</Text>
          </Stack>
        </Center>
      ),
    )
  }

  return shell(
    <Table.ScrollContainer minWidth={minWidth}>
      <Table striped highlightOnHover stickyHeader verticalSpacing="sm" horizontalSpacing="md" withRowBorders>
        <Table.Thead style={{ background: 'var(--mantine-color-gray-light)' }}>
          <Table.Tr>
            {columns.map((col) => (
              <Table.Th key={col.key} style={col.key === '__actions' ? { textAlign: 'center' } : undefined}>
                {col.label}
              </Table.Th>
            ))}
          </Table.Tr>
        </Table.Thead>
        <Table.Tbody>
          {data.map((row) => (
            <Table.Tr
              key={getRowKey(row)}
              onClick={onRowClick ? () => onRowClick(row) : undefined}
              style={onRowClick ? { cursor: 'pointer' } : undefined}
            >
              {columns.map((col) => (
                <Table.Td key={col.key} style={col.key === '__actions' ? { textAlign: 'center' } : undefined}>
                  {col.render ? col.render(row) : String(col.field ? row[col.field] ?? '' : '')}
                </Table.Td>
              ))}
            </Table.Tr>
          ))}
        </Table.Tbody>
      </Table>
    </Table.ScrollContainer>,
  )
}