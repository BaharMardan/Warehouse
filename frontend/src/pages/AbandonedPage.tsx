import { useEffect } from 'react'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import { Alert, Badge, Button, Center, Group, Loader, Paper, SimpleGrid, Stack, Table, Text, Title, UnstyledButton } from '@mantine/core'
import { Link, useSearchParams } from 'react-router-dom'
import { apiSend } from '../api/client'
import { useAbandoned, type AgingItem } from '../api/abandoned'
import { BackButton } from '../components/BackButton'
import { PageHeader } from '../components/PageHeader'
import { jalali } from './invoiceTypes'

export function AbandonedPage() {
  const { data, isLoading, isError } = useAbandoned()
  const qc = useQueryClient()
  const [params, setParams] = useSearchParams()
  const requested = params.get('section')
  const selected = requested === 'abandoned' || requested === 'warning' ? requested : null
  const seen = useMutation({
    mutationFn: (tokens: string[]) => apiSend<void>('/abandoned/seen', 'POST', { tokens }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['abandoned'] }),
  })
  const tokens = data?.items.filter(row => row.unseen).map(row => row.token) ?? []
  const tokenKey = tokens.join(',')
  useEffect(() => {
    if (tokenKey && !seen.isPending && !seen.isError) seen.mutate(tokenKey.split(','))
  }, [tokenKey, seen.isPending, seen.isError, seen.mutate])

  const section = (title: string, rows: AgingItem[], warning: boolean) =>
    <Paper withBorder p="md" radius="md">
      <Group mb="md"><Title order={3}>{title}</Title><Badge color="yellow">{rows.length.toLocaleString('fa-IR')}</Badge></Group>
      {!rows.length ? <Text c="dimmed">موردی وجود ندارد.</Text> :
        <Table.ScrollContainer minWidth={650}><Table striped highlightOnHover>
          <Table.Thead><Table.Tr><Table.Th>شماره تالی</Table.Th><Table.Th>صاحب کالا</Table.Th>
            <Table.Th>تاریخ تخلیه</Table.Th><Table.Th>روزهای سپری‌شده</Table.Th>
            {warning && <Table.Th>روز تا متروکه‌شدن</Table.Th>}
          </Table.Tr></Table.Thead>
          <Table.Tbody>{rows.map(row => <Table.Tr key={row.id}>
            <Table.Td><Button component={Link} to={`/tally/id/${row.id}`} variant="subtle" color="yellow">
              <bdi>{row.tally_number || row.id}</bdi>
            </Button></Table.Td>
            <Table.Td>{row.owner_name || '—'}</Table.Td><Table.Td>{jalali(row.unloaded_at)}</Table.Td>
            <Table.Td>{row.age_days.toLocaleString('fa-IR')}</Table.Td>
            {warning && <Table.Td>{row.days_remaining.toLocaleString('fa-IR')}</Table.Td>}
          </Table.Tr>)}</Table.Tbody>
        </Table></Table.ScrollContainer>}
    </Paper>

  return <div dir="rtl">
    <PageHeader title="متروکه" subtitle="تالی‌های بدون صورتحساب فعال که خروج بار آن‌ها ثبت نشده یا تاریخ خروج هنوز نرسیده است"
      actions={<BackButton to="/" />} />
    {isLoading && <Center py="xl"><Loader color="yellow" /></Center>}
    {isError && <Alert color="red">دریافت فهرست متروکه ناموفق بود.</Alert>}
    {seen.isError && <Alert color="orange" mb="md">ثبت مشاهده اعلان‌ها انجام نشد.
      <Button variant="subtle" onClick={() => seen.mutate(tokens)}>تلاش مجدد</Button>
    </Alert>}
    {data && (selected == null ?
      <SimpleGrid cols={{ base: 1, sm: 2 }} spacing="lg">
        {([
          { key: 'abandoned', title: 'کالاهای متروکه', description: '۹۰ روز و بیشتر از تاریخ تخلیه', count: data.abandoned_count },
          { key: 'warning', title: 'هشدار متروکه', description: '۸۰ تا ۸۹ روز از تاریخ تخلیه؛ نزدیک به متروکه‌شدن', count: data.warning_count },
        ] as const).map(item =>
          <Paper key={item.key} withBorder radius="lg" style={{ overflow: 'hidden', borderColor: 'var(--mantine-color-yellow-5)' }}>
            <UnstyledButton onClick={() => setParams({ section: item.key })}
              aria-label={`بازکردن ${item.title}`}
              style={{ width: '100%', padding: 32, textAlign: 'right', background: 'var(--mantine-color-yellow-light)' }}>
              <Stack gap="sm">
                <Group justify="space-between"><Title order={3}>{item.title}</Title>
                  <Badge color="yellow" size="lg">{item.count.toLocaleString('fa-IR')}</Badge>
                </Group>
                <Text size="sm" c="dimmed">{item.description}</Text>
                <Text size="sm" fw={700} c="yellow.8">مشاهده فهرست</Text>
              </Stack>
            </UnstyledButton>
          </Paper>
        )}
      </SimpleGrid> :
      <Stack>
        <Group><Button variant="light" color="yellow" onClick={() => setParams({})}>بازگشت به بخش‌های متروکه</Button></Group>
        {section(selected === 'abandoned' ? 'متروکه — ۹۰ روز و بیشتر' : 'هشدار متروکه — ۸۰ تا ۸۹ روز',
          data.items.filter(row => row.stage === selected), selected === 'warning')}
      </Stack>
    )}
  </div>
}
