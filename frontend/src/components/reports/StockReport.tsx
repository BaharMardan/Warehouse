import { useState } from 'react'
import { useDebouncedValue } from '@mantine/hooks'
import {
  Alert, Button, Center, Group, Loader, Paper, SegmentedControl, Select, SimpleGrid, Stack, Switch,
  Table, Text, TextInput, Title, Tooltip,
} from '@mantine/core'
import { Link, useNavigate } from 'react-router-dom'
import { PrintButton } from './PrintDialog'
import {
  useStockReport, type StockBlock, type StockData, type StockGroup, type StockGroupBy, type StockRow,
} from '../../api/reports'
import { amount, downloadCsv, jalali, money } from './reportFormat'

const GROUPS: { value: StockGroupBy; label: string }[] = [
  { value: 'hscode', label: 'HS Code' },
  { value: 'owner', label: 'صاحب کالا' },
  { value: 'anbar', label: 'انبار' },
  { value: 'location', label: 'نوع محل' },
  { value: 'tally', label: 'تالی' },
  { value: 'none', label: 'تک‌تک ردیف‌ها' },
]
const CARGO: Record<string, string> = { weight: 'وزنی', volumetric: 'حجمی', container: 'کانتینری', yes: 'حجمی', no: 'وزنی' }

const list = (values: string[]) => values.join('، ') || '—'

function Figure({ label, value, hint }: { label: string; value: string; hint?: string }) {
  return (
    <Paper withBorder p="md" radius="md">
      <Text size="sm" c="dimmed">{label}</Text>
      <Text fw={700} size="lg"><bdi dir="ltr">{value}</bdi></Text>
      {hint && <Text size="xs" c="dimmed">{hint}</Text>}
    </Paper>
  )
}

function Insured({ value, unknown = 'نامشخص' }: { value: number | null; unknown?: string }) {
  if (value != null) return <bdi dir="ltr">{money(value)}</bdi>
  return <Tooltip label="تالی بیمه‌دار است ولی ارزش کالای بیمه‌شده (سقف بیمه‌نامه) در هیچ تالی ثبت نشده است" multiline w={260}>
    <Text span c="orange" size="sm">{unknown}</Text>
  </Tooltip>
}

function RowsTable({ rows }: { rows: StockRow[] }) {
  return (
    <Table.ScrollContainer minWidth={1700}>
      <Table striped highlightOnHover verticalSpacing={6}>
        <Table.Thead><Table.Tr>
          <Table.Th>تالی</Table.Th><Table.Th>تاریخ تخلیه</Table.Th><Table.Th>صاحب کالا</Table.Th>
          <Table.Th>HS Code</Table.Th><Table.Th>شرح کالا</Table.Th><Table.Th>نوع بسته‌بندی</Table.Th>
          <Table.Th>انبار</Table.Th><Table.Th>طاق</Table.Th><Table.Th>نوع محل</Table.Th>
          <Table.Th>نوع بار</Table.Th><Table.Th>حامل / کانتینر</Table.Th><Table.Th>تعداد</Table.Th>
          <Table.Th>وزن اظهار (kg)</Table.Th><Table.Th>وزن باسکول (kg)</Table.Th><Table.Th>پالت</Table.Th>
          <Table.Th ta="left">ارزش کالا (گمرکی)</Table.Th>
          <Table.Th ta="left">ارزش بیمه‌نامهٔ تالی</Table.Th>
        </Table.Tr></Table.Thead>
        <Table.Tbody>
          {rows.map((row) => (
            <Table.Tr key={row.detail_id}>
              <Table.Td><Button component={Link} to={`/tally/id/${row.tally_id}`} variant="subtle"
                color="forest" size="compact-sm">{row.tally_number ?? row.tally_id}</Button></Table.Td>
              <Table.Td>{jalali(row.unloaded_at)}</Table.Td>
              <Table.Td>{row.owner_name}</Table.Td>
              <Table.Td><bdi dir="ltr">{row.hscode ?? '—'}</bdi></Table.Td>
              <Table.Td maw={260}><Text size="sm" lineClamp={2} title={row.description ?? undefined}>{row.description ?? '—'}</Text></Table.Td>
              <Table.Td>{row.package_type ?? '—'}</Table.Td>
              <Table.Td>{row.anbar_name}</Table.Td>
              <Table.Td>{row.tagh_name ?? '—'}</Table.Td>
              <Table.Td>{row.location_label}</Table.Td>
              <Table.Td>{(row.cargo_type && CARGO[row.cargo_type]) || '—'}</Table.Td>
              <Table.Td><bdi dir="ltr">{[row.container_type, row.container_number, row.carrier].filter(Boolean).join(' / ') || '—'}</bdi></Table.Td>
              <Table.Td><bdi dir="ltr">{amount(row.quantity)}</bdi></Table.Td>
              <Table.Td><bdi dir="ltr">{amount(row.weight)}</bdi></Table.Td>
              <Table.Td><bdi dir="ltr">{amount(row.baskol)}</bdi></Table.Td>
              <Table.Td><bdi dir="ltr">{amount(row.pallets)}</bdi></Table.Td>
              <Table.Td ta="left"><bdi dir="ltr">{money(row.customs_value)}</bdi></Table.Td>
              <Table.Td ta="left"><Insured value={row.insured_value} /></Table.Td>
            </Table.Tr>
          ))}
        </Table.Tbody>
      </Table>
    </Table.ScrollContainer>
  )
}

function GroupsTable({ data, groupLabel }: { data: StockData; groupLabel: string }) {
  const [open, setOpen] = useState<Set<string | number>>(new Set())
  const toggle = (key: string | number) => setOpen((current) => {
    const next = new Set(current)
    if (!next.delete(key)) next.add(key)
    return next
  })
  const total = data.totals
  const block = (group: StockBlock) => (<>
    <Table.Td><bdi dir="ltr">{group.rows.toLocaleString('fa-IR')}</bdi></Table.Td>
    <Table.Td><bdi dir="ltr">{amount(group.weight)}</bdi></Table.Td>
    <Table.Td><bdi dir="ltr">{amount(group.pallets)}</bdi></Table.Td>
    <Table.Td><bdi dir="ltr">{amount(group.containers, 0)}</bdi></Table.Td>
    <Table.Td ta="left"><bdi dir="ltr">{money(group.customs_value)}</bdi></Table.Td>
    <Table.Td ta="left">
      <bdi dir="ltr">{money(group.insured_value)}</bdi>
      {group.insurance_unknown > 0 && <Text size="xs" c="orange">{group.insurance_unknown.toLocaleString('fa-IR')} تالی بدون مبلغ بیمه‌نامه</Text>}
    </Table.Td>
  </>)
  return (
    <Table.ScrollContainer minWidth={1500}>
      <Table highlightOnHover verticalSpacing={6}>
        <Table.Thead><Table.Tr>
          <Table.Th>{groupLabel}</Table.Th><Table.Th>شرح کالا</Table.Th><Table.Th>نوع بسته‌بندی</Table.Th>
          <Table.Th>صاحب کالا</Table.Th><Table.Th>انبار / نوع محل</Table.Th><Table.Th>ردیف</Table.Th>
          <Table.Th>وزن اظهار (kg)</Table.Th><Table.Th>پالت</Table.Th><Table.Th>کانتینر</Table.Th>
          <Table.Th ta="left">ارزش کالا (گمرکی)</Table.Th>
          <Table.Th ta="left">ارزش بیمه‌شده (هر تالی یک‌بار)</Table.Th>
        </Table.Tr></Table.Thead>
        <Table.Tbody>
          {data.groups.map((group: StockGroup) => {
            const isOpen = open.has(group.key)
            return [
              <Table.Tr key={group.key} style={{ cursor: 'pointer' }} onClick={() => toggle(group.key)}
                bg={isOpen ? 'var(--app-accent-light)' : undefined}>
                <Table.Td fw={700}>{isOpen ? '▾' : '◂'} <bdi dir="ltr">{group.label}</bdi></Table.Td>
                <Table.Td maw={260}><Text size="sm" lineClamp={2} title={list(group.descriptions)}>{list(group.descriptions)}</Text></Table.Td>
                <Table.Td>{list(group.package_types)}</Table.Td>
                <Table.Td maw={180}><Text size="sm" lineClamp={2} title={list(group.owners)}>{list(group.owners)}</Text></Table.Td>
                <Table.Td maw={160}><Text size="sm" lineClamp={2}>{list(group.anbars)} / {list(group.locations)}</Text></Table.Td>
                {block(group)}
              </Table.Tr>,
              isOpen && <Table.Tr key={`${group.key}-rows`}>
                <Table.Td colSpan={11} p={0}>
                  <RowsTable rows={data.rows.filter((row) => row.group_key === group.key)} />
                </Table.Td>
              </Table.Tr>,
            ]
          })}
          <Table.Tr fw={700} bg="var(--mantine-color-default-hover)">
            <Table.Td>جمع کل</Table.Td><Table.Td /><Table.Td /><Table.Td /><Table.Td />
            {block(total)}
          </Table.Tr>
        </Table.Tbody>
      </Table>
    </Table.ScrollContainer>
  )
}

/** The goods in the warehouse right now, with value, insurance, weight and location. */
export function StockReport({ from, to, enabled }: { from: string; to: string; enabled: boolean }) {
  const [groupBy, setGroupBy] = useState<StockGroupBy>('hscode')
  const [hscode, setHscode] = useState('')
  const [debouncedHs] = useDebouncedValue(hscode, 400)
  const [ownerId, setOwnerId] = useState<string | null>(null)
  const [anbarId, setAnbarId] = useState<string | null>(null)
  const [location, setLocation] = useState<string | null>(null)
  const [byUnloadDate, setByUnloadDate] = useState(false)
  const navigate = useNavigate()

  const stock = useStockReport({
    groupBy, hscode: debouncedHs, ownerId, anbarId, location,
    unloadedFrom: byUnloadDate ? from : null, unloadedTo: byUnloadDate ? to : null,
  }, enabled)
  const data = stock.data

  if (stock.isError) return <Alert color="red">دریافت گزارش موجودی انبار ناموفق بود.</Alert>
  if (!data) return <Center py="xl"><Loader color="forest" /></Center>

  const t = data.totals
  const groupLabel = GROUPS.find((g) => g.value === groupBy)?.label ?? ''
  const asOf = new Date(data.as_of).toLocaleString('fa-IR')

  const print = (sections: string[]) => navigate(`/reports/print?${new URLSearchParams({
    kind: 'stock', sections: sections.join(','), group_by: groupBy,
    ...(debouncedHs.trim() ? { hscode: debouncedHs.trim() } : {}),
    ...(ownerId ? { owner_id: ownerId } : {}), ...(anbarId ? { anbar_id: anbarId } : {}),
    ...(location ? { location } : {}),
    ...(byUnloadDate ? { unloaded_from: from, unloaded_to: to } : {}),
  })}`)

  const exportCsv = () => {
    const stamp = new Date().toISOString().slice(0, 10)
    if (groupBy === 'none') {
      downloadCsv(`stock-rows_${stamp}.csv`,
        ['تالی', 'تاریخ تخلیه', 'صاحب کالا', 'HS Code', 'شرح کالا', 'نوع بسته‌بندی', 'انبار', 'طاق', 'نوع محل',
          'نوع بار', 'نوع کانتینر', 'شماره کانتینر', 'حامل', 'تعداد', 'وزن اظهار (kg)', 'وزن باسکول (kg)', 'پالت',
          'ارزش کالا (گمرکی)', 'ارزش بیمه‌نامهٔ تالی'],
        data.rows.map((r) => [r.tally_number, jalali(r.unloaded_at), r.owner_name, r.hscode, r.description,
          r.package_type, r.anbar_name, r.tagh_name, r.location_label, r.cargo_type && CARGO[r.cargo_type],
          r.container_type, r.container_number, r.carrier, r.quantity, r.weight, r.baskol, r.pallets,
          r.customs_value, r.insured_value]))
      return
    }
    downloadCsv(`stock-by-${groupBy}_${stamp}.csv`,
      [groupLabel, 'شرح کالا', 'نوع بسته‌بندی', 'صاحب کالا', 'انبار', 'نوع محل', 'تعداد تالی', 'تعداد ردیف',
        'وزن اظهار (kg)', 'پالت', 'کانتینر', 'ارزش کالا (گمرکی)', 'ارزش بیمه‌شده (هر تالی یک‌بار)'],
      [...data.groups.map((g) => [g.label, list(g.descriptions), list(g.package_types), list(g.owners),
        list(g.anbars), list(g.locations), g.tallies, g.rows, g.weight, g.pallets, g.containers,
        g.customs_value, g.insured_value]),
      ['جمع کل', '', '', '', '', '', t.tallies, t.rows, t.weight, t.pallets, t.containers,
        t.customs_value, t.insured_value]])
  }

  return (
    <Stack gap="lg">
      <SimpleGrid cols={{ base: 1, sm: 2, lg: 4 }} spacing="md">
        <Figure label="تالی‌های دارای کالا" value={t.tallies.toLocaleString('fa-IR')}
          hint={`${t.rows.toLocaleString('fa-IR')} ردیف کالا`} />
        <Figure label="وزن اظهار کل (کیلوگرم)" value={amount(t.weight)}
          hint={`${amount(t.weight / 1000, 3)} تن؛ باسکول: ${amount(t.baskol)} کیلوگرم`} />
        <Figure label="پالت (جمع پالت حامل‌ها)" value={amount(t.pallets)}
          hint={t.pallets_missing > 0
            ? `برای ${t.pallets_missing.toLocaleString('fa-IR')} تالی حجمی، پالت برخی حامل‌ها ثبت نشده و در جمع نیست` : undefined} />
        <Figure label="کانتینر" value={amount(t.containers, 0)} />
        <Figure label="ارزش کل کالاها (گمرکی، ریال)" value={money(t.customs_value)} />
        <Figure label="ارزش کل بیمه‌شده (ریال)" value={money(t.insured_value)}
          hint={t.insurance_unknown > 0 ? `${t.insurance_unknown.toLocaleString('fa-IR')} تالی بیمه‌دار بدون مبلغ بیمه‌نامه، در این جمع نیست` : undefined} />
      </SimpleGrid>

      <Paper withBorder p="md" radius="md">
        <Stack gap="md">
          <Group justify="space-between" wrap="wrap">
            <Stack gap={2}>
              <Title order={4}>موجودی انبار</Title>
              <Text size="xs" c="dimmed">وضعیت لحظه‌ای تا {asOf}</Text>
            </Stack>
            <Group gap="xs">
              <PrintButton title="چاپ گزارش موجودی انبار" onPrint={print}
                defaults={groupBy === 'none' ? ['totals', 'rows'] : ['totals', 'groups']} options={[
                  { value: 'totals', label: 'ارقام کل (تالی، وزن، پالت، کانتینر، ارزش کالا و بیمه)' },
                  { value: 'groups', label: `جدول گروه‌بندی‌شده بر اساس ${groupLabel}`, disabled: groupBy === 'none',
                    description: groupBy === 'none' ? 'ابتدا یک گروه‌بندی انتخاب کنید.' : undefined },
                  { value: 'rows', label: 'ریز تک‌تک ردیف‌های کالا' },
                ]} />
              <Button variant="light" color="forest" size="xs" onClick={exportCsv}
                disabled={!data.rows.length}>خروجی Excel (CSV)</Button>
            </Group>
          </Group>
          <Group align="flex-end" wrap="wrap">
            <div>
              <Text size="sm" mb={4}>گروه‌بندی بر اساس</Text>
              <SegmentedControl value={groupBy} onChange={(v) => setGroupBy(v as StockGroupBy)} data={GROUPS} />
            </div>
          </Group>
          <Group align="flex-end" wrap="wrap">
            <TextInput label="HS Code" placeholder="بخشی از کد" value={hscode}
              onChange={(e) => setHscode(e.currentTarget.value)} w={160} />
            <Select label="صاحب کالا" placeholder="همه" clearable searchable value={ownerId} onChange={setOwnerId}
              data={data.facets.owners.map((o) => ({ value: String(o.id), label: o.name }))} w={220} />
            <Select label="انبار" placeholder="همه" clearable value={anbarId} onChange={setAnbarId}
              data={data.facets.anbars.map((a) => ({ value: String(a.id), label: a.name }))} w={140} />
            <Select label="نوع محل" placeholder="همه" clearable value={location} onChange={setLocation}
              data={data.facets.locations.map((l) => ({ value: l.id, label: l.name }))} w={160} />
            <Switch label="فقط کالاهای تخلیه‌شده در بازهٔ زمانی بالا" checked={byUnloadDate}
              onChange={(e) => setByUnloadDate(e.currentTarget.checked)} mb={6} />
          </Group>

          {!data.rows.length ? <Text c="dimmed">کالایی با این شرایط در انبار موجود نیست.</Text> :
            groupBy === 'none' ? <RowsTable rows={data.rows} /> : <GroupsTable data={data} groupLabel={groupLabel} />}

          <Text size="xs" c="dimmed">
            موجودی = کالاهای تالی‌شده‌ای که هنوز خروج نخورده‌اند و صورتحساب ترخیص آن‌ها صادر نشده است (همان منطق صفحهٔ متروکه)؛ ردیفی که بخشی از آن ترخیص شده، فقط به‌اندازهٔ باقی‌مانده حساب می‌شود.
            ارزش کالا همان «ارزش کالای گمرکی» ردیف تالی است (برای ردیف نیمه‌ترخیص‌شده، به نسبت باقی‌مانده).
            ارزش بیمه‌شده همان «ارزش کالای بیمه‌شده» تالی و عدد کل بیمه‌نامه است که روی ردیف‌ها تکرار می‌شود؛ بنابراین در هر گروه و در جمع کل برای هر تالی فقط یک بار حساب می‌شود (برای تالی‌هایی که «بیمه‌دار» نیستند صفر است).
            جمع پالت از تعداد پالت ثبت‌شده برای هر حامل به دست می‌آید؛ پالت‌های قبض‌های ترخیص‌شده کم می‌شود.
          </Text>
        </Stack>
      </Paper>
    </Stack>
  )
}
