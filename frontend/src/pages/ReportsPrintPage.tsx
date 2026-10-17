import { Alert, Center, Group, Loader } from '@mantine/core'
import { useSearchParams } from 'react-router-dom'
import {
  useIncomeLines, useIncomeSummary, useStockReport,
  type IncomeSummary, type StockData, type StockGroupBy,
} from '../api/reports'
import { useCurrentUser, usePermissions } from '../auth/usePermissions'
import { BackButton } from '../components/BackButton'
import { CompanyLogo } from '../components/CompanyLogo'
import { IconPrint } from '../components/icons'
import { amount, jalali, money, percent } from '../components/reports/reportFormat'
import './ReportsPrintPage.css'

const CARGO: Record<string, string> = { weight: 'وزنی', volumetric: 'حجمی', container: 'کانتینری', yes: 'حجمی', no: 'وزنی' }
const GROUP_LABEL: Record<string, string> = {
  hscode: 'HS Code', owner: 'صاحب کالا', anbar: 'انبار', location: 'نوع محل', tally: 'تالی',
}
const list = (values: string[]) => values.join('، ') || '—'
const ltr = (value: string | number) => <bdi dir="ltr">{value}</bdi>

function Sheet({ title, meta, children }: { title: string; meta: string[]; children: React.ReactNode }) {
  const { data: user } = useCurrentUser()
  return (
    <section className="rp-sheet">
      <header className="rp-heading">
        <div className="rp-heading-main">
          <button className="rp-print-action" type="button" onClick={() => window.print()}
            aria-label="چاپ گزارش" title="چاپ گزارش">
            <IconPrint size={27} stroke={1.8} />
          </button>
          <div>
            <h1>{title}</h1>
            <p>چاپ روی کاغذ A4 با حالت افقی</p>
          </div>
        </div>
        <div className="rp-brand">
          <div>
            <strong>شرکت آسان تجارت فلات شرق</strong>
            <small>سامانه انبار — کاربر: {user?.full_name || user?.username || '—'}</small>
          </div>
          <CompanyLogo />
        </div>
      </header>
      <div className="rp-info">
        {meta.map((line) => <span key={line}>{line}</span>)}
        <span>تاریخ چاپ: {new Date().toLocaleString('fa-IR')}</span>
      </div>
      {children}
    </section>
  )
}

function IncomePrint({ sections, from, to, category }: { sections: string[]; from: string; to: string; category: string | null }) {
  const summary = useIncomeSummary(from, to, true)
  const wantLines = sections.includes('lines')
  const lines = useIncomeLines(from, to, category, wantLines)
  const data: IncomeSummary | undefined = summary.data
  if (summary.isError || (wantLines && lines.isError)) return <Alert color="red">دریافت گزارش ناموفق بود.</Alert>
  if (!data || (wantLines && !lines.data)) return <Center py="xl"><Loader color="forest" /></Center>

  const t = data.summary
  const cat = (key: string) => data.categories.find((c) => c.key === key)!
  const label = category ? cat(category)?.label : 'همهٔ ردیف‌ها'
  const row = (name: string, value: number, key: string, strong = false, counts?: [number, number]) => (
    <tr key={key} className={strong ? 'rp-strong' : undefined}>
      <td className="rp-text">{name}</td>
      <td>{counts ? ltr(counts[0].toLocaleString('fa-IR')) : ''}</td>
      <td>{counts ? ltr(counts[1].toLocaleString('fa-IR')) : ''}</td>
      <td>{ltr(money(value))}</td>
      <td>{!strong && counts && t.gross ? ltr(percent(value, t.gross)) : ''}</td>
    </tr>)
  const entry = (key: string) => row(cat(key).label, cat(key).amount, key, false, [cat(key).invoices, cat(key).lines])

  return (
    <Sheet title="گزارش درآمد صورتحساب‌ها" meta={[
      `بازهٔ صدور: از ${jalali(from)} تا ${jalali(to)}`,
      `تعداد صورتحساب: ${data.invoice_count.toLocaleString('fa-IR')}`]}>
      {sections.includes('summary') && <>
        <h2>خلاصهٔ درآمد به تفکیک نوع ردیف (ریال)</h2>
        <table className="rp-table">
          <thead><tr><th>دسته</th><th>تعداد صورتحساب</th><th>تعداد ردیف</th><th>مبلغ</th><th>سهم از جمع هزینه‌ها</th></tr></thead>
          <tbody>
            {data.categories.filter((c) => c.section === 'charge' && c.lines > 0).map((c) => entry(c.key))}
            {row('جمع هزینه‌ها', t.gross, 'gross', true)}
            {cat('discount').lines > 0 && entry('discount')}
            {row('جمع کل درآمد (قبل از مالیات)', t.net, 'net', true)}
            {entry('tax')}
            {row('جمع صورتحساب‌ها با مالیات', t.total_with_tax, 'withTax', true)}
            {cat('prepayment').lines > 0 && entry('prepayment')}
            {row('مانده قابل پرداخت (جمع با مالیات − کسر پیش‌پرداخت)', t.payable, 'payable', true)}
          </tbody>
        </table>
        <p className="rp-note">
          پیش‌پرداخت درآمد نیست و فقط از مانده قابل پرداخت کم می‌شود. فقط صورتحساب‌های فعال شمرده شده‌اند.
          {data.left_out.lines > 0 && ` ${data.left_out.lines.toLocaleString('fa-IR')} ردیف قدیمی استریپ/تخلیه (یا استافینگ/بارگیری) یک‌جاثبت‌شده به مبلغ ${money(data.left_out.amount)} ریال در رقم‌ها نیامده است.`}
          {data.supplementary.invoices > 0 && ` شامل ${data.supplementary.invoices.toLocaleString('fa-IR')} صورتحساب تکمیلی به مبلغ ${money(data.supplementary.amount)} ریال.`}
        </p>
      </>}

      {wantLines && lines.data && <>
        <h2>جزئیات ردیف‌ها — {label}</h2>
        <table className="rp-table">
          <thead><tr><th>تاریخ صدور</th><th>صورتحساب</th><th>تالی</th><th>قبض</th><th>خریدار</th><th>دسته</th><th>شرح</th><th>مبلغ (ریال)</th></tr></thead>
          <tbody>
            {lines.data.lines.map((l) => (
              <tr key={l.line_id}>
                <td>{jalali(l.issued_at)}</td><td>{ltr(l.invoice_id)}</td><td>{l.tally_number ?? '—'}</td>
                <td>{ltr(l.receipt_number ?? '—')}</td><td className="rp-text">{l.buyer_name ?? '—'}</td>
                <td className="rp-text">{l.category_label}</td><td className="rp-text">{l.description ?? '—'}</td>
                <td>{ltr(money(l.amount))}</td>
              </tr>
            ))}
            <tr className="rp-strong"><td colSpan={7} className="rp-text">جمع</td><td>{ltr(money(lines.data.total))}</td></tr>
          </tbody>
        </table>
        {lines.data.truncated && <p className="rp-note">فهرست به‌دلیل تعداد زیاد کوتاه شده است؛ جمع، کل ردیف‌ها را شامل می‌شود.</p>}
      </>}

      {sections.includes('cancelled') && data.cancelled.count > 0 && <>
        <h2>صورتحساب‌های باطل‌شده (در درآمد نیامده‌اند) — جمع {money(data.cancelled.amount)} ریال</h2>
        <table className="rp-table">
          <thead><tr><th>صورتحساب</th><th>تاریخ صدور</th><th>تاریخ ابطال</th><th>تالی</th><th>قبض</th><th>خریدار</th><th>مبلغ</th><th>وضعیت</th></tr></thead>
          <tbody>
            {data.cancelled.invoices.map((c) => (
              <tr key={c.invoice_id}>
                <td>{ltr(c.invoice_id)}</td><td>{jalali(c.issued_at)}</td><td>{jalali(c.cancelled_at)}</td>
                <td>{c.tally_number ?? '—'}</td><td>{ltr(c.receipt_number ?? '—')}</td>
                <td className="rp-text">{c.buyer_name ?? '—'}</td><td>{ltr(money(c.amount))}</td>
                <td>{c.reissued ? 'دوباره صادر شده' : 'صادر نشده'}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </>}
    </Sheet>
  )
}

function StockPrint({ sections, params }: { sections: string[]; params: URLSearchParams }) {
  const groupBy = (params.get('group_by') ?? 'hscode') as StockGroupBy
  const stock = useStockReport({
    groupBy, hscode: params.get('hscode') ?? '', ownerId: params.get('owner_id'),
    anbarId: params.get('anbar_id'), location: params.get('location'),
    unloadedFrom: params.get('unloaded_from'), unloadedTo: params.get('unloaded_to'),
  }, true)
  const data: StockData | undefined = stock.data
  if (stock.isError) return <Alert color="red">دریافت گزارش ناموفق بود.</Alert>
  if (!data) return <Center py="xl"><Loader color="forest" /></Center>

  const t = data.totals
  const owner = data.facets.owners.find((o) => String(o.id) === params.get('owner_id'))?.name
  const anbar = data.facets.anbars.find((a) => String(a.id) === params.get('anbar_id'))?.name
  const place = data.facets.locations.find((l) => l.id === params.get('location'))?.name
  const filters = [
    params.get('hscode') && `HS Code شامل ${params.get('hscode')}`, owner && `صاحب کالا: ${owner}`,
    anbar && `انبار: ${anbar}`, place && `نوع محل: ${place}`,
    params.get('unloaded_from') && `تخلیه از ${jalali(params.get('unloaded_from'))} تا ${jalali(params.get('unloaded_to'))}`,
  ].filter(Boolean) as string[]
  const figures: [string, string][] = [
    ['تعداد تالی', t.tallies.toLocaleString('fa-IR')], ['تعداد ردیف کالا', t.rows.toLocaleString('fa-IR')],
    ['وزن اظهار (kg)', amount(t.weight)], ['وزن باسکول (kg)', amount(t.baskol)],
    ['پالت', amount(t.pallets)], ['کانتینر', amount(t.containers, 0)],
    ['ارزش کل کالاها (گمرکی، ریال)', money(t.customs_value)], ['ارزش کل بیمه‌شده (ریال)', money(t.insured_value)],
  ]

  return (
    <Sheet title="گزارش موجودی انبار" meta={[
      `وضعیت لحظه‌ای تا ${new Date(data.as_of).toLocaleString('fa-IR')}`,
      filters.length ? `فیلتر: ${filters.join('؛ ')}` : 'بدون فیلتر']}>
      {sections.includes('totals') && <>
        <h2>ارقام کل</h2>
        <div className="rp-figures">
          {figures.map(([name, value]) => <div key={name}><span>{name}</span><b>{ltr(value)}</b></div>)}
        </div>
        {(t.pallets_missing > 0 || t.insurance_unknown > 0) && <p className="rp-note">
          {t.pallets_missing > 0 && `برای ${t.pallets_missing.toLocaleString('fa-IR')} تالی حجمی، پالت برخی حامل‌ها ثبت نشده و در جمع نیست. `}
          {t.insurance_unknown > 0 && `${t.insurance_unknown.toLocaleString('fa-IR')} تالی بیمه‌دار بدون مبلغ بیمه‌نامه در جمع بیمه نیست.`}
        </p>}
      </>}

      {sections.includes('groups') && groupBy !== 'none' && <>
        <h2>موجودی به تفکیک {GROUP_LABEL[groupBy]}</h2>
        <table className="rp-table">
          <thead><tr>
            <th>{GROUP_LABEL[groupBy]}</th><th>شرح کالا</th><th>نوع بسته‌بندی</th><th>صاحب کالا</th><th>انبار / نوع محل</th>
            <th>ردیف</th><th>وزن (kg)</th><th>پالت</th><th>کانتینر</th><th>ارزش کالا</th><th>ارزش بیمه‌شده</th>
          </tr></thead>
          <tbody>
            {data.groups.map((g) => (
              <tr key={g.key}>
                <td>{ltr(g.label)}</td><td className="rp-text">{list(g.descriptions)}</td><td>{list(g.package_types)}</td>
                <td className="rp-text">{list(g.owners)}</td><td>{list(g.anbars)} / {list(g.locations)}</td>
                <td>{ltr(g.rows.toLocaleString('fa-IR'))}</td><td>{ltr(amount(g.weight))}</td><td>{ltr(amount(g.pallets))}</td>
                <td>{ltr(amount(g.containers, 0))}</td><td>{ltr(money(g.customs_value))}</td><td>{ltr(money(g.insured_value))}</td>
              </tr>
            ))}
            <tr className="rp-strong">
              <td colSpan={5} className="rp-text">جمع کل</td>
              <td>{ltr(t.rows.toLocaleString('fa-IR'))}</td><td>{ltr(amount(t.weight))}</td><td>{ltr(amount(t.pallets))}</td>
              <td>{ltr(amount(t.containers, 0))}</td><td>{ltr(money(t.customs_value))}</td><td>{ltr(money(t.insured_value))}</td>
            </tr>
          </tbody>
        </table>
        <p className="rp-note">ارزش بیمه‌شدهٔ هر تالی در هر گروه یک بار شمرده می‌شود؛ اگر یک تالی در چند گروه باشد، جمع گروه‌ها ممکن است از جمع کل بیشتر شود.</p>
      </>}

      {sections.includes('rows') && <>
        <h2>ریز ردیف‌های کالا</h2>
        <table className="rp-table">
          <thead><tr>
            <th>تالی</th><th>تاریخ تخلیه</th><th>صاحب کالا</th><th>HS Code</th><th>شرح کالا</th><th>بسته‌بندی</th>
            <th>انبار / طاق</th><th>نوع محل</th><th>نوع بار</th><th>تعداد</th><th>وزن (kg)</th><th>پالت</th>
            <th>ارزش کالا</th><th>ارزش بیمه‌نامهٔ تالی</th>
          </tr></thead>
          <tbody>
            {data.rows.map((r) => (
              <tr key={r.detail_id}>
                <td>{r.tally_number ?? r.tally_id}</td><td>{jalali(r.unloaded_at)}</td><td className="rp-text">{r.owner_name}</td>
                <td>{ltr(r.hscode ?? '—')}</td><td className="rp-text">{r.description ?? '—'}</td><td>{r.package_type ?? '—'}</td>
                <td>{r.anbar_name}{r.tagh_name ? ` / ${r.tagh_name}` : ''}</td><td>{r.location_label}</td>
                <td>{(r.cargo_type && CARGO[r.cargo_type]) || '—'}</td><td>{ltr(amount(r.quantity))}</td>
                <td>{ltr(amount(r.weight))}</td><td>{ltr(amount(r.pallets))}</td>
                <td>{ltr(money(r.customs_value))}</td><td>{r.insured_value == null ? 'نامشخص' : ltr(money(r.insured_value))}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </>}
    </Sheet>
  )
}

export function ReportsPrintPage() {
  const [params] = useSearchParams()
  const { can } = usePermissions()
  const sections = (params.get('sections') ?? '').split(',').filter(Boolean)
  const kind = params.get('kind')
  const from = params.get('from') ?? ''
  const to = params.get('to') ?? ''

  return (
    <main className="rp-page" dir="rtl">
      <Group className="rp-actions">
        <BackButton to="/reports" />
      </Group>
      {kind === 'income' && can('reports.income') && from && to && sections.length > 0 &&
        <IncomePrint sections={sections} from={from} to={to} category={params.get('category')} />}
      {kind === 'stock' && can('reports.stock') && sections.length > 0 &&
        <StockPrint sections={sections} params={params} />}
      {!((kind === 'income' && can('reports.income')) || (kind === 'stock' && can('reports.stock'))) &&
        <Alert color="red">گزارش درخواستی نامعتبر است یا دسترسی آن را ندارید.</Alert>}
    </main>
  )
}
