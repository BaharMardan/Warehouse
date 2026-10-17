import { useEffect, useState } from 'react'
import { Alert, Button, Center, Group, Loader, Text } from '@mantine/core'
import { useLocation } from 'react-router-dom'
import { useAbandoned, type AgingItem } from '../api/abandoned'
import { useCurrentUser } from '../auth/usePermissions'
import { AbandonedTable } from '../components/AbandonedTable'
import { BackButton } from '../components/BackButton'
import { CompanyLogo } from '../components/CompanyLogo'
import { IconPrint } from '../components/icons'
import './AbandonedPrintPage.css'

export function AbandonedPrintPage() {
  const { data: user } = useCurrentUser()
  const location = useLocation()
  const snapshot = location.state as { rows?: AgingItem[]; userId?: number } | null
  // Print the displayed list in its original order. Direct links load a fresh
  // list once; polling must not change rows while the user prepares a printout.
  const [rows, setRows] = useState<AgingItem[] | null>(() =>
    snapshot?.userId === user?.id && Array.isArray(snapshot?.rows)
      ? snapshot.rows.filter(row => row.stage === 'abandoned') : null)
  const { data, isError, refetch } = useAbandoned(rows === null)
  useEffect(() => {
    if (rows === null && data) setRows(data.items.filter(row => row.stage === 'abandoned'))
  }, [data, rows])

  if (rows === null) return <Center mih="100vh" dir="rtl">
    {isError ? <Alert color="red" title="دریافت فهرست متروکه ناموفق بود">
      <Button variant="light" onClick={() => refetch()}>تلاش مجدد</Button>
      <BackButton to="/abandoned?section=abandoned" />
    </Alert> : <Loader color="yellow" />}
  </Center>

  return <main className="abandoned-print-page" dir="rtl">
    <Group className="abandoned-print-actions" justify="space-between">
      <Button color="yellow" leftSection={<IconPrint size={18} />} onClick={() => window.print()} disabled={!rows.length}>چاپ فهرست</Button>
      <BackButton to="/abandoned?section=abandoned" />
    </Group>
    <section className="abandoned-print-sheet">
      <header className="abandoned-print-heading">
        <div>
          <h1>فهرست متروکه — ۹۰ روز و بیشتر</h1>
          <p>سامانه انبار آسان تجارت فلات شرق</p>
        </div>
        <CompanyLogo />
      </header>
      <div className="abandoned-print-info">
        <span>تعداد تالی‌ها: {rows.length.toLocaleString('fa-IR')} — تعداد ردیف‌های کالا: {rows.reduce((sum, row) => sum + (row.goods?.length ?? 0), 0).toLocaleString('fa-IR')}</span>
        <span>کاربر: {user?.full_name || user?.username || '—'}</span>
      </div>
      {rows.length ? <AbandonedTable rows={rows} printable /> : <Text>موردی وجود ندارد.</Text>}
    </section>
  </main>
}
