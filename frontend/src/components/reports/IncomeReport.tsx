import { useRef, useState } from 'react'
import { Alert, Badge, Button, Center, Group, Loader, Paper, Select, SimpleGrid, Stack, Table, Text, Title } from '@mantine/core'
import { Link, useNavigate } from 'react-router-dom'
import { PrintButton } from './PrintDialog'
import { useIncomeLines, useIncomeSummary, type IncomeCategory } from '../../api/reports'
import { amount, downloadCsv, jalali, money } from './reportFormat'

const ALL = 'all'

function Figure({ label, value, hint, strong = false }: {
  label: string; value: number; hint?: string; strong?: boolean
}) {
  return (
    <Paper withBorder p="md" radius="md" bg={strong ? 'var(--app-accent-light)' : undefined}>
      <Text size="sm" c="dimmed">{label}</Text>
      <Text fw={700} size={strong ? 'xl' : 'lg'}><bdi dir="ltr">{money(value)}</bdi></Text>
      {hint && <Text size="xs" c="dimmed">{hint}</Text>}
    </Paper>
  )
}

/** Income of saved invoices issued in the period, per invoice-row category. */
export function IncomeReport({ from, to, enabled }: { from: string; to: string; enabled: boolean }) {
  const [selected, setSelected] = useState<string>(ALL)
  const linesRef = useRef<HTMLDivElement>(null)
  const navigate = useNavigate()
  const summary = useIncomeSummary(from, to, enabled)
  const lines = useIncomeLines(from, to, selected === ALL ? null : selected, enabled)
  const data = summary.data

  if (summary.isError) return <Alert color="red">دریافت گزارش درآمد ناموفق بود.</Alert>
  if (!data) return <Center py="xl"><Loader color="forest" /></Center>

  const showLines = (key: string) => {
    setSelected(key)
    // The list sits below the summary; bring it into view so the click visibly does something.
    requestAnimationFrame(() => linesRef.current?.scrollIntoView({ behavior: 'smooth', block: 'start' }))
  }

  const charges = data.categories.filter((c) => c.section === 'charge' && (!['other', 'vehicle_enter', 'night_stop'].includes(c.key) || c.amount !== 0))
  const adjustment = (key: string) => data.categories.find((c) => c.key === key)!
  const adjustmentOrCharge = (key: string) => data.categories.find((c) => c.key === key)?.label ?? key
  const { summary: totals } = data

  const categoryRow = (category: IncomeCategory) => (
    <Table.Tr key={category.key} c={category.lines === 0 ? 'dimmed' : undefined}
      bg={selected === category.key ? 'var(--app-accent-light)' : undefined}>
      <Table.Td>{category.label}</Table.Td>
      <Table.Td><bdi dir="ltr">{category.invoices.toLocaleString('fa-IR')}</bdi></Table.Td>
      <Table.Td><bdi dir="ltr">{category.lines.toLocaleString('fa-IR')}</bdi></Table.Td>
      <Table.Td ta="left"><bdi dir="ltr">{money(category.amount)}</bdi></Table.Td>
      <Table.Td>
        <Button size="compact-sm" variant="subtle" color="forest" disabled={category.lines === 0}
          onClick={() => showLines(category.key)}>مشاهده ردیف‌ها</Button>
      </Table.Td>
    </Table.Tr>
  )

  const subtotal = (label: string, value: number, key: string, count?: number) => (
    <Table.Tr key={key} fw={700} bg="var(--mantine-color-default-hover)"
      style={{ borderTop: `${key === 'payable' ? 4 : 2}px solid var(--mantine-color-forest-8)` }}>
      <Table.Td>{label}</Table.Td>
      <Table.Td>{count == null ? '' : <bdi dir="ltr">{count.toLocaleString('fa-IR')}</bdi>}</Table.Td>
      <Table.Td />
      <Table.Td ta="left"><bdi dir="ltr">{money(value)}</bdi></Table.Td>
      <Table.Td />
    </Table.Tr>
  )

  const exportCategories = () => downloadCsv(
    `income-by-category_${from}_${to}.csv`,
    ['دسته', 'تعداد صورتحساب', 'تعداد ردیف', 'مبلغ (ریال)'],
    [...charges.map((c) => [c.label, c.invoices, c.lines, c.amount]),
      ['جمع هزینه‌ها', '', '', totals.gross],
      ['تخفیف', adjustment('discount').invoices, adjustment('discount').lines, -totals.discount],
      ['جمع', data.invoice_count, '', totals.net],
      ['مالیات بر ارزش افزوده', adjustment('tax').invoices, adjustment('tax').lines, totals.tax],
      ['جمع کل', '', '', totals.total_with_tax],
      ['کسر پیش‌پرداخت', adjustment('prepayment').invoices, adjustment('prepayment').lines, -totals.prepayment],
      ['مبلغ قابل پرداخت', '', '', totals.payable]],
  )

  const categoryOptions = [{ value: ALL, label: 'همهٔ ردیف‌ها' },
    ...data.categories.filter((c) => (!['other', 'vehicle_enter', 'night_stop'].includes(c.key) || c.amount !== 0) && (c.lines > 0 || c.key === selected)).map((c) => ({ value: c.key, label: c.label }))]

  const exportLines = () => lines.data && downloadCsv(
    `income-lines_${selected}_${from}_${to}.csv`,
    ['تاریخ صدور', 'شماره صورتحساب', 'شماره تالی', 'شماره قبض', 'خریدار', 'دسته', 'شرح', 'تعداد', 'وزن', 'مبلغ (ریال)'],
    lines.data.lines.map((l) => [jalali(l.issued_at), l.invoice_id, l.tally_number, l.receipt_number,
      l.buyer_name, l.category_label, l.description, l.quantity, l.weight, l.amount]),
  )

  const selectedLabel = selected === ALL ? 'همهٔ ردیف‌ها' : adjustmentOrCharge(selected)
  const print = (sections: string[]) => navigate(`/reports/print?${new URLSearchParams({
    kind: 'income', from, to, sections: sections.join(','), ...(selected === ALL ? {} : { category: selected }),
  })}`)

  return (
    <Stack gap="lg">
      <Group justify="flex-end">
        <PrintButton title="چاپ گزارش درآمد" defaults={['cards', 'summary']} onPrint={print} options={[
          { value: 'cards', label: 'ارقام کلی (جمع درآمد، تخفیف، مالیات، پیش‌پرداخت و مبلغ قابل پرداخت)' },
          { value: 'summary', label: 'خلاصهٔ درآمد به تفکیک نوع ردیف و جمع‌ها' },
          { value: 'lines', label: `جزئیات ردیف‌ها — ${selectedLabel}`,
            description: 'دسته را در بخش «جزئیات ردیف‌ها» پایین صفحه انتخاب کنید.' },
          { value: 'cancelled', label: 'صورتحساب‌های باطل‌شده', disabled: data.cancelled.count === 0 },
        ]} />
      </Group>
      <SimpleGrid cols={{ base: 1, sm: 2, lg: 4 }} spacing="md">
        <Figure strong label="جمع" value={totals.net}
          hint={`${data.invoice_count.toLocaleString('fa-IR')} صورتحساب`} />
        <Figure label="جمع هزینه‌ها (قبل از تخفیف)" value={totals.gross} />
        <Figure label="تخفیف" value={totals.discount} />
        <Figure label="مالیات بر ارزش افزوده" value={totals.tax} />
        <Figure label="جمع کل" value={totals.total_with_tax} />
        <Figure label="کسر پیش‌پرداخت" value={totals.prepayment} hint="از درآمد کم نمی‌شود" />
        <Figure strong label="مبلغ قابل پرداخت" value={totals.payable}
          hint="پس از مالیات و کسر پیش‌پرداخت" />
      </SimpleGrid>

      <Paper withBorder p="md" radius="md">
        <Group justify="space-between" mb="md">
          <Title order={4}>خلاصه: درآمد به تفکیک نوع ردیف (ریال)</Title>
          <Button variant="light" color="forest" size="xs" onClick={exportCategories}>خروجی Excel (CSV)</Button>
        </Group>
        {data.invoice_count === 0 ? <Text c="dimmed">در این بازه صورتحسابی صادر نشده است.</Text> :
          <Table.ScrollContainer minWidth={700}>
            <Table highlightOnHover>
              <Table.Thead><Table.Tr>
                <Table.Th>دسته</Table.Th><Table.Th>تعداد صورتحساب</Table.Th><Table.Th>تعداد ردیف</Table.Th>
                <Table.Th ta="left">مبلغ</Table.Th><Table.Th />
              </Table.Tr></Table.Thead>
              <Table.Tbody>
                {charges.map((c) => categoryRow(c))}
                {subtotal('جمع هزینه‌ها', totals.gross, 'gross')}
                {categoryRow(adjustment('discount'))}
                {subtotal('جمع', totals.net, 'net', data.invoice_count)}
                {categoryRow(adjustment('tax'))}
                {subtotal('جمع کل', totals.total_with_tax, 'withTax')}
                {categoryRow(adjustment('prepayment'))}
                {subtotal('مبلغ قابل پرداخت', totals.payable, 'payable')}
              </Table.Tbody>
            </Table>
          </Table.ScrollContainer>}
        {/* <Text size="xs" c="dimmed" mt="sm">
          مبلغ هر ردیف همان مبلغ چاپ‌شده در صورتحساب است (قیمت منهای تخفیف ردیف). پیش‌پرداخت درآمد نیست و فقط از مانده قابل پرداخت کم می‌شود.
          فقط صورتحساب‌های فعال شمرده می‌شوند؛ اگر صورتحسابی باطل و دوباره صادر شده باشد، فقط صورتحساب جدید (به تاریخ صدور خودش) در درآمد می‌آید. ردیف‌های صفر‌ریالی نمایش داده نمی‌شوند.
          صورتحساب‌های جدید استریپ، تخلیه، استافینگ و بارگیری را جدا ذخیره می‌کنند.
        </Text> */}
        
        {/* {data.supplementary.invoices > 0 && <Text size="xs" c="dimmed" mt={4}>
          در این جمع {data.supplementary.invoices.toLocaleString('fa-IR')} صورتحساب تکمیلی (باقی‌مانده) به مبلغ{' '}
          <bdi dir="ltr">{money(data.supplementary.amount)}</bdi> ریال هم هست؛ این‌ها درآمد جداگانه‌اند و دوبار شمرده نشده‌اند.
        </Text>} */}
      </Paper>

      <Paper withBorder p="md" radius="md" ref={linesRef} style={{ scrollMarginTop: 80 }}>
        <Group justify="space-between" align="flex-end" mb="md" wrap="wrap">
          <Group align="flex-end">
            <Title order={4}>جزئیات ردیف‌ها (تک‌تک ردیف‌های صورتحساب‌ها)</Title>
            <Select aria-label="دسته" data={categoryOptions} value={selected}
              onChange={(value) => setSelected(value ?? ALL)} allowDeselect={false} w={260} />
          </Group>
          <Group>
            {lines.data && <Badge color="forest" variant="light" size="lg">
              جمع: <bdi dir="ltr">{money(lines.data.total)}</bdi>
            </Badge>}
            <Button variant="light" color="forest" size="xs" disabled={!lines.data?.lines.length}
              onClick={exportLines}>خروجی Excel (CSV)</Button>
          </Group>
        </Group>
        {lines.isError && <Alert color="red">دریافت ردیف‌ها ناموفق بود.</Alert>}
        {lines.isFetching && !lines.data && <Center py="md"><Loader color="forest" size="sm" /></Center>}
        {lines.data && lines.data.truncated &&
          <Alert color="orange" mb="sm">تعداد ردیف‌ها زیاد است و فقط بخشی نمایش داده شد؛ بازه را کوتاه‌تر کنید. جمع بالا کل ردیف‌ها را شامل می‌شود.</Alert>}
        {lines.data && !lines.data.lines.length && <Text c="dimmed">ردیفی یافت نشد.</Text>}
        {lines.data && lines.data.lines.length > 0 &&
          <Table.ScrollContainer minWidth={1000}>
            <Table striped highlightOnHover>
              <Table.Thead><Table.Tr>
                <Table.Th>تاریخ صدور</Table.Th><Table.Th>صورتحساب</Table.Th><Table.Th>تالی</Table.Th>
                <Table.Th>قبض</Table.Th><Table.Th>خریدار</Table.Th><Table.Th>دسته</Table.Th>
                <Table.Th>شرح</Table.Th><Table.Th>تعداد</Table.Th><Table.Th>وزن</Table.Th>
                <Table.Th ta="left">مبلغ (ریال)</Table.Th>
              </Table.Tr></Table.Thead>
              <Table.Tbody>
                {lines.data.lines.map((l) => (
                  <Table.Tr key={l.line_id}>
                    <Table.Td>{jalali(l.issued_at)}</Table.Td>
                    <Table.Td><Button component={Link} to={`/invoice/${l.invoice_id}`} variant="subtle"
                      color="forest" size="compact-sm">{l.invoice_id.toLocaleString('en-US')}</Button></Table.Td>
                    <Table.Td>{l.tally_id ? <Button component={Link} to={`/tally/id/${l.tally_id}`}
                      variant="subtle" color="forest" size="compact-sm">{l.tally_number ?? l.tally_id}</Button> : '—'}</Table.Td>
                    <Table.Td><bdi dir="ltr">{l.receipt_number ?? '—'}</bdi></Table.Td>
                    <Table.Td>{l.buyer_name ?? '—'}</Table.Td>
                    <Table.Td>{l.category_label}</Table.Td>
                    <Table.Td>{l.description ?? '—'}</Table.Td>
                    <Table.Td><bdi dir="ltr">{amount(l.quantity, 4)}</bdi></Table.Td>
                    <Table.Td><bdi dir="ltr">{amount(l.weight)}</bdi></Table.Td>
                    <Table.Td ta="left"><bdi dir="ltr">{money(l.amount)}</bdi></Table.Td>
                  </Table.Tr>
                ))}
              </Table.Tbody>
            </Table>
          </Table.ScrollContainer>}
      </Paper>

      <Paper withBorder p="md" radius="md">
        <Group justify="space-between" mb="xs">
          <Title order={4}>صورتحساب‌های باطل‌شده (در درآمد نیامده‌اند)</Title>
          <Badge color="gray" variant="light" size="lg">
            {data.cancelled.count.toLocaleString('fa-IR')} مورد؛ <bdi dir="ltr">{money(data.cancelled.amount)}</bdi>
          </Badge>
        </Group>
        {data.cancelled.count === 0 ? <Text c="dimmed">در این بازه صورتحساب باطل‌شده‌ای وجود ندارد.</Text> :
          <Table.ScrollContainer minWidth={850}>
            <Table striped>
              <Table.Thead><Table.Tr>
                <Table.Th>صورتحساب</Table.Th><Table.Th>تاریخ صدور</Table.Th><Table.Th>تاریخ ابطال</Table.Th>
                <Table.Th>تالی</Table.Th><Table.Th>قبض</Table.Th><Table.Th>خریدار</Table.Th>
                <Table.Th ta="left">مبلغ باطل‌شده</Table.Th><Table.Th>وضعیت</Table.Th>
              </Table.Tr></Table.Thead>
              <Table.Tbody>
                {data.cancelled.invoices.map((c) => (
                  <Table.Tr key={c.invoice_id}>
                    <Table.Td><bdi dir="ltr">{c.invoice_id}</bdi></Table.Td>
                    <Table.Td>{jalali(c.issued_at)}</Table.Td>
                    <Table.Td>{jalali(c.cancelled_at)}</Table.Td>
                    <Table.Td>{c.tally_number ?? '—'}</Table.Td>
                    <Table.Td><bdi dir="ltr">{c.receipt_number ?? '—'}</bdi></Table.Td>
                    <Table.Td>{c.buyer_name ?? '—'}</Table.Td>
                    <Table.Td ta="left"><bdi dir="ltr">{money(c.amount)}</bdi></Table.Td>
                    <Table.Td>{c.reissued ? 'دوباره صادر شده' : 'صادر نشده'}</Table.Td>
                  </Table.Tr>
                ))}
              </Table.Tbody>
            </Table>
          </Table.ScrollContainer>}
      </Paper>
    </Stack>
  )
}
