import { useState } from 'react'
import { Alert, Button, Group, Paper, Stack, Tabs, Text } from '@mantine/core'
import { BackButton } from '../components/BackButton'
import { JalaliDate } from '../components/JalaliDate'
import { PageHeader } from '../components/PageHeader'
import { IncomeReport } from '../components/reports/IncomeReport'
import { StockReport } from '../components/reports/StockReport'
import { isoDate, periodPresets } from '../components/reports/reportFormat'
import { usePermissions } from '../auth/usePermissions'

export function ReportsPage() {
  const { can } = usePermissions()
  const presets = periodPresets()
  const [from, setFrom] = useState(presets[1].from)
  const [to, setTo] = useState(isoDate(new Date()))
  const canIncome = can('reports.income')
  const canStock = can('reports.stock')
  const [tab, setTab] = useState<string | null>(canIncome ? 'income' : 'stock')

  const validPeriod = from <= to

  return (
    <div dir="rtl">
      <PageHeader title="گزارش‌گیری" subtitle="درآمد صورتحساب‌ها و موجودی انبار" actions={<BackButton to="/" />} />
      <Stack gap="lg">
        <Paper withBorder p="md" radius="md">
          <Group align="flex-end" wrap="wrap" gap="md">
            <div style={{ width: 200 }}><JalaliDate label="از تاریخ" value={from} onChange={(v) => v && setFrom(v)} /></div>
            <div style={{ width: 200 }}><JalaliDate label="تا تاریخ" value={to} onChange={(v) => v && setTo(v)} /></div>
            <Group gap="xs">
              {presets.map((preset) => (
                <Button key={preset.label} size="xs" variant="light" color="forest"
                  onClick={() => { setFrom(preset.from); setTo(preset.to) }}>{preset.label}</Button>
              ))}
            </Group>
          </Group>
          <Text size="xs" c="dimmed" mt="xs">
            بازه روی تاریخ صدور صورتحساب‌ها اعمال می‌شود. موجودی انبار لحظه‌ای است؛ برای محدود کردن آن به تاریخ تخلیه، گزینهٔ مربوط را در همان بخش روشن کنید.
          </Text>
          {!validPeriod && <Alert color="red" mt="sm">تاریخ پایان نمی‌تواند پیش از تاریخ شروع باشد.</Alert>}
        </Paper>

        <Tabs value={tab} onChange={setTab} color="forest" keepMounted={false}>
          <Tabs.List mb="md">
            {canIncome && <Tabs.Tab value="income">درآمد و صورتحساب‌ها</Tabs.Tab>}
            {canStock && <Tabs.Tab value="stock">موجودی انبار</Tabs.Tab>}
          </Tabs.List>
          {canIncome && <Tabs.Panel value="income">
            <IncomeReport from={from} to={to} enabled={validPeriod} />
          </Tabs.Panel>}
          {canStock && <Tabs.Panel value="stock">
            <StockReport from={from} to={to} enabled />
          </Tabs.Panel>}
        </Tabs>
      </Stack>
    </div>
  )
}
