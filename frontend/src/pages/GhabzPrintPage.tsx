import { useEffect, type ReactNode } from 'react'
import { useQuery } from '@tanstack/react-query'
import { Button, Center, Loader, Text } from '@mantine/core'
import { useParams } from 'react-router-dom'
import { toJalaali } from 'jalaali-js'
import {
  Building2, CalendarDays, FileText, IdCard, MapPin, PackageCheck,
  PencilLine, ReceiptText, ShieldCheck, Stamp, Truck, UserRound,
} from 'lucide-react'
import { apiGet } from '../api/client'
import { IconPrint } from '../components/icons'
import './TallyPrintPage.css'
import './GhabzPrintPage.css'

type GhabzHeader = {
  id_ghabz: number
  ghabz_number: string | null
  number_ghabz: number | null
  number_ghabz_uniqe: number | null
  number_tali: string | null
  number_karaneh: string | null
  number_royea: string | null
  number_marze: string | null
  tracking_number: string | null
  date_unloading: string | null
  date_enter_marze: string | null
  marze_name: string | null
  country_name: string | null
  company_name: string | null
  owner_name: string | null
  anbar_name: string | null
  anbar_masol: string | null
  name_anbardar: string | null
  status_bimeh: string | null
  number_bimeh: string | null
  company_bimeh: string | null
  description: string | null
  create_at: string | null
  created_by_username: string | null
  created_by_full_name: string | null
}

type GhabzLine = {
  id_ghabz_anbar_details: number
  code_kala: number | null
  description_kala: string | null
  hscode: string | null
  type_basteh: string | null
  number_kala: number | null
  weighte_asnad: number | null
  weighte_baskol: number | null
  number_hamel: string | null
  tagh_name: string | null
}

type CurrentUser = { username: string; full_name: string | null }

const ROWS_PER_PAGE = 4
const EMPTY = '—'

function valueOf(value: unknown): string {
  return value == null || String(value).trim() === '' ? EMPTY : String(value)
}

function formatJalaliDate(value: string | null): string {
  if (!value) return EMPTY
  const [gy, gm, gd] = value.slice(0, 10).split('-').map(Number)
  if (!gy || !gm || !gd) return valueOf(value)
  const { jy, jm, jd } = toJalaali(gy, gm, gd)
  return `${jy}/${String(jm).padStart(2, '0')}/${String(jd).padStart(2, '0')}`
}

function isInsured(value: string | null): boolean {
  return ['بله', 'دارد', 'yes', 'true'].includes(String(value ?? '').trim().toLowerCase())
}

function splitRows(rows: GhabzLine[]): GhabzLine[][] {
  const pages: GhabzLine[][] = []
  for (let index = 0; index < rows.length; index += ROWS_PER_PAGE) {
    pages.push(rows.slice(index, index + ROWS_PER_PAGE))
  }
  return pages.length ? pages : [[]]
}

function InfoLine({ icon, label, value, ltr = false }: {
  icon: ReactNode
  label: string
  value: unknown
  ltr?: boolean
}) {
  return (
    <div className="tally-print-info-line">
      <span className="tally-print-info-icon" aria-hidden>{icon}</span>
      <span className="tally-print-label">{label}:</span>
      <span className={`tally-print-value${ltr ? ' tally-print-ltr' : ''}`}>{valueOf(value)}</span>
    </div>
  )
}

function IndustrialEstateMark() {
  return (
    <div className="tally-print-brand-mark" aria-label="شهرک صنعتی توس">
      <svg viewBox="0 0 64 64" aria-hidden>
        <circle cx="32" cy="23" r="17" fill="none" stroke="currentColor" strokeWidth="2.5" />
        <path d="M15 23h34M32 6c-7 6-10 11-10 17s3 12 10 17M32 6c7 6 10 11 10 17s-3 12-10 17M18 15c8 4 20 4 28 0M18 31c8-4 20-4 28 0" fill="none" stroke="currentColor" strokeWidth="2" />
        <path d="M13 39l19 10 19-10v10L32 59 13 49z" fill="currentColor" />
      </svg>
    </div>
  )
}

function CheckBox({ checked, label }: { checked: boolean; label: string }) {
  return (
    <span className="tally-print-check">
      <span className="tally-print-check-box" aria-hidden>{checked ? '✓' : ''}</span>
      {label}
    </span>
  )
}

type PlateParts = {
  leading: string
  letter: string
  serial: string
  region: string
}

function toLatinDigits(value: string): string {
  return value
    .replace(/[\u06F0-\u06F9]/g, (digit) => String(digit.charCodeAt(0) - 0x06f0))
    .replace(/[\u0660-\u0669]/g, (digit) => String(digit.charCodeAt(0) - 0x0660))
}

function toPersianDigits(value: string): string {
  return value.replace(/\d/g, (digit) => '۰۱۲۳۴۵۶۷۸۹'[Number(digit)])
}

function parsePlate(value: string | null | undefined): PlateParts | null {
  const normalized = toLatinDigits(String(value ?? '').trim())
  const separated = normalized.split('-').map((part) => part.trim()).filter(Boolean)
  if (separated.length === 4) {
    const [leading, letter, serial, region] = separated
    if (/^\d{1,2}$/.test(leading) && /^[\u0600-\u06FF]+$/.test(letter)
      && /^\d{1,3}$/.test(serial) && /^\d{1,2}$/.test(region)) {
      return { leading, letter, serial, region }
    }
  }

  const compact = normalized.replace(/[\sـ_]/g, '').match(
    /^(\d{1,2})-?([\u0600-\u06FF]+)-?(\d{1,3})-?(\d{1,2})$/,
  )
  return compact
    ? { leading: compact[1], letter: compact[2], serial: compact[3], region: compact[4] }
    : null
}

function IranianPlate({ value }: { value: string | null | undefined }) {
  const parts = parsePlate(value)
  if (!parts) return <span className="tally-print-ltr">{valueOf(value)}</span>

  return (
    <span className="tally-print-plate" dir="ltr" aria-label={`پلاک ${value}`}>
      <span className="tally-print-plate-blue"><span>🇮🇷</span><small>I.R.</small></span>
      <span>{toPersianDigits(parts.leading)}</span>
      <span className="tally-print-plate-letter" dir="rtl">{parts.letter}</span>
      <span>{toPersianDigits(parts.serial)}</span>
      <span className="tally-print-plate-region" dir="rtl">
        <small>ایران</small><strong>{toPersianDigits(parts.region)}</strong>
      </span>
    </span>
  )
}

function GhabzSheet({ header, rows, page, pageCount, carriers, printUser }: {
  header: GhabzHeader
  rows: GhabzLine[]
  page: number
  pageCount: number
  carriers: string[]
  printUser: string
}) {
  const receiptNumber = header.ghabz_number ?? header.number_ghabz
  const insured = isInsured(header.status_bimeh)
  const isLastPage = page === pageCount - 1

  return (
    <section className="tally-print-sheet" dir="rtl">
      <div className="tally-print-form">
        <header className="tally-print-heading">
          <div className="tally-print-preview-heading">
            <button className="tally-print-action" type="button" onClick={() => window.print()}
              aria-label="چاپ قبض انبار" title="چاپ قبض انبار">
              <IconPrint size={27} stroke={1.8} />
            </button>
            <div>
              <h1>
                <span className="tally-print-screen-title">پیش‌نمایش</span>
                <span className="tally-print-paper-title">قبض انبار</span>
                <bdi dir="ltr">{valueOf(receiptNumber)}</bdi>
              </h1>
              <p>چاپ روی کاغذ A4 با حالت افقی</p>
            </div>
          </div>
          <div className="tally-print-brand">
            <IndustrialEstateMark />
            <div className="tally-print-brand-copy">
              <strong>شرکت آسان تجارت فلات شرق</strong>
              <span>شرکت شهرک‌های صنعتی</span>
              <small>شهرک صنعتی توس</small>
              <div className="tally-print-user">کاربر: <b>{valueOf(printUser)}</b></div>
            </div>
          </div>
        </header>

        <div className="tally-print-header-fields">
          <div className="tally-print-info-card">
            <InfoLine icon={<ReceiptText />} label="شماره کارنه / ترانزیت" value={header.number_karaneh} ltr />
            <InfoLine icon={<FileText />} label="رویه" value={header.number_royea} />
            <InfoLine icon={<PackageCheck />} label="ردیف مرزی" value={header.number_marze} ltr />
            <InfoLine icon={<CalendarDays />} label="تاریخ ورود به مرز" value={formatJalaliDate(header.date_enter_marze)} ltr />
            <InfoLine icon={<CalendarDays />} label="تاریخ تخلیه" value={formatJalaliDate(header.date_unloading)} ltr />
          </div>
          <div className="tally-print-info-card tally-print-info-card-wide">
            <InfoLine icon={<Truck />} label="شرکت حمل" value={header.company_name} />
            <InfoLine icon={<UserRound />} label="صاحب کالا" value={header.owner_name} />
            <InfoLine icon={<MapPin />} label="مبدأ حمل" value={header.country_name} />
            <InfoLine icon={<Building2 />} label="انبار" value={header.anbar_name} />
            <InfoLine icon={<UserRound />} label="مسئول انبار" value={header.anbar_masol ?? header.name_anbardar} />
          </div>
          <div className="tally-print-info-card">
            <InfoLine icon={<IdCard />} label="شماره قبض انبار" value={receiptNumber} ltr />
            <InfoLine icon={<IdCard />} label="شناسه یکتا" value={header.number_ghabz_uniqe} ltr />
            <InfoLine icon={<IdCard />} label="شماره تالی" value={header.number_tali} ltr />
            <InfoLine icon={<FileText />} label="شناسه پیگیری" value={header.tracking_number} ltr />
            <InfoLine icon={<MapPin />} label="مرز ورودی" value={header.marze_name} />
            <InfoLine icon={<CalendarDays />} label="تاریخ صدور" value={formatJalaliDate(header.create_at)} ltr />
          </div>
        </div>

        <div className="ghabz-print-insurance-top">
          <span className="tally-print-info-icon" aria-hidden><ShieldCheck /></span>
          <CheckBox checked={insured} label="بیمه دارد" />
          <CheckBox checked={!insured} label="بیمه ندارد" />
          <span>شماره بیمه: <bdi dir="ltr">{valueOf(header.number_bimeh)}</bdi></span>
          <span>شرکت بیمه: {valueOf(header.company_bimeh)}</span>
        </div>

        <div className="tally-print-table-frame">
          <table className="tally-print-table ghabz-print-table">
            <thead><tr>
              <th>ردیف</th><th>کد گروه کالا</th><th dir="ltr">HS CODE</th>
              <th>شرح کالا</th><th>طاق انبار</th><th>نوع بسته‌بندی</th>
              <th>تعداد بسته</th><th>وزن اسناد</th><th>وزن باسکول</th>
            </tr></thead>
            <tbody>
              {rows.map((row, index) => (
                <tr key={row.id_ghabz_anbar_details}>
                  <td>{page * ROWS_PER_PAGE + index + 1}</td>
                  <td className="tally-print-ltr">{valueOf(row.code_kala)}</td>
                  <td className="tally-print-ltr">{valueOf(row.hscode)}</td>
                  <td>{valueOf(row.description_kala)}</td>
                  <td>{valueOf(row.tagh_name)}</td>
                  <td>{valueOf(row.type_basteh)}</td>
                  <td className="tally-print-ltr">{valueOf(row.number_kala)}</td>
                  <td className="tally-print-ltr">{valueOf(row.weighte_asnad)}</td>
                  <td className="tally-print-ltr">{valueOf(row.weighte_baskol)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        {isLastPage && (
          <div className="ghabz-print-carriers">
            <strong>شماره‌های حامل:</strong>
            <div>
              {carriers.length
                ? carriers.map((carrier, index) => (
                    <IranianPlate value={carrier} key={`${carrier}-${index}`} />
                  ))
                : <span>{EMPTY}</span>}
            </div>
          </div>
        )}

        <div className="tally-print-insurance ghabz-print-notes">
          <div className="tally-print-notes"><strong>توضیحات:</strong><span>{valueOf(header.description)}</span></div>
        </div>

        <footer className="tally-print-signatures ghabz-print-signatures">
          <div><strong><PencilLine aria-hidden /> مدیر عملیات</strong><span /></div>
          <div><strong><Stamp aria-hidden /> صدور اسناد</strong><span /></div>
        </footer>
      </div>
      {pageCount > 1 && <div className="tally-print-page-number">صفحه {page + 1} از {pageCount}</div>}
    </section>
  )
}

export function GhabzPrintPage() {
  const { id } = useParams<{ id: string }>()
  const headerId = Number(id)
  const headerQuery = useQuery({
    queryKey: ['ghabz-print-summary', headerId],
    queryFn: () => apiGet<GhabzHeader>(`/ghabz/${headerId}/summary`),
    enabled: Number.isFinite(headerId),
  })
  const linesQuery = useQuery({
    queryKey: ['ghabz-print-details', headerId],
    queryFn: () => apiGet<GhabzLine[]>(`/ghabz/${headerId}/details`),
    enabled: Number.isFinite(headerId),
  })
  const userQuery = useQuery({ queryKey: ['current-user'], queryFn: () => apiGet<CurrentUser>('/auth/me') })

  const receiptNumber = headerQuery.data?.ghabz_number ?? headerQuery.data?.number_ghabz
  useEffect(() => {
    if (receiptNumber) document.title = `قبض انبار ${receiptNumber}`
    return () => { document.title = 'سامانه انبار' }
  }, [receiptNumber])

  if (headerQuery.isLoading || linesQuery.isLoading || userQuery.isLoading) {
    return <Center className="tally-print-state"><Loader /><Text>در حال آماده‌سازی قبض انبار برای چاپ…</Text></Center>
  }
  if (headerQuery.isError || linesQuery.isError || !headerQuery.data || !linesQuery.data) {
    return <Center className="tally-print-state"><Text c="red">اطلاعات قبض انبار برای چاپ بارگذاری نشد.</Text><Button variant="default" onClick={() => window.close()}>بستن</Button></Center>
  }

  const carriers = linesQuery.data
    .map((line) => String(line.number_hamel ?? '').trim())
    .filter(Boolean)
  const pages = splitRows(linesQuery.data)
  const printUser = userQuery.data?.full_name || userQuery.data?.username
    || headerQuery.data.created_by_full_name || headerQuery.data.created_by_username || ''

  return (
    <main className="tally-print-page ghabz-print-page">
      {pages.map((rows, page) => (
        <GhabzSheet key={page} header={headerQuery.data} rows={rows} page={page}
          pageCount={pages.length} carriers={carriers} printUser={printUser} />
      ))}
    </main>
  )
}
