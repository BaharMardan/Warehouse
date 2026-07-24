import { useEffect } from 'react'
import { useQuery } from '@tanstack/react-query'
import { Button, Center, Group, Loader, Text } from '@mantine/core'
import { useParams } from 'react-router-dom'
import { toJalaali } from 'jalaali-js'
import { apiGet } from '../api/client'
import { IconPrint } from '../components/icons'
import './TallyPrintPage.css'

type PrintDetail = {
  id_tali_details: number
  tagh_name: string | null
  number_ghabze_anbar: number | null
  code_groupe_kala: number | null
  description_kala: string | null
  hscode: string | null
  type_bastem: string | null
  number_kala: number | null
  weighte: number | null
  number_hamel: string | null
  type_number_kantiner: string | null
  number_ghabze_bskol: number | null
  weighte_baskol: number | null
  container_type: string | null
  container_number: string | null
}

type TallyPrintData = {
  id_tali: number
  tali_number: string
  number_karaneh: string | null
  radef_marze: number | null
  date_enter_marze: string | null
  date_unloading: string | null
  number_bimeh: string | null
  number_barnameh: string | null
  name_arzyab: string | null
  is_bimeh: string | null
  name_anbardar: string | null
  accepted_gomrok: string | null
  company_bimeh: string | null
  marze_name: string | null
  country_name: string | null
  company_name: string | null
  representative_name: string | null
  owner_name: string | null
  owner_national_code: string | null
  print_user_name: string | null
  details: PrintDetail[]
}

type TallyHeaderLookup = {
  id_tali: number
  tali_number: string
}

type CurrentUser = {
  username: string
  full_name: string | null
}

const ROWS_PER_PAGE = 6
const EMPTY = '\u00a0'

function valueOf(value: unknown): string {
  if (value == null || String(value).trim() === '') return EMPTY
  return String(value)
}

function firstValue(...values: unknown[]): string | null {
  for (const value of values) {
    if (value != null && String(value).trim() !== '') return String(value).trim()
  }
  return null
}

function toPersianDigits(value: string): string {
  return value.replace(/\d/g, (digit) => '۰۱۲۳۴۵۶۷۸۹'[Number(digit)])
}

function toLatinDigits(value: string): string {
  return value
    .replace(/[\u06F0-\u06F9]/g, (digit) => String(digit.charCodeAt(0) - 0x06f0))
    .replace(/[\u0660-\u0669]/g, (digit) => String(digit.charCodeAt(0) - 0x0660))
}

function formatJalaliDate(value: string | null): string {
  if (!value) return EMPTY
  const [gy, gm, gd] = value.slice(0, 10).split('-').map(Number)
  if (!gy || !gm || !gd) return valueOf(value)
  const { jy, jm, jd } = toJalaali(gy, gm, gd)
  return `${jy}/${String(jm).padStart(2, '0')}/${String(jd).padStart(2, '0')}`
}

function isInsured(value: string | null): boolean {
  const normalized = String(value ?? '').trim().toLowerCase()
  return normalized === 'بله' || normalized === 'دارد' || normalized === 'yes' || normalized === 'true'
}

function splitRows(rows: PrintDetail[]): PrintDetail[][] {
  const source = rows.length > 0 ? rows : []
  const pages: PrintDetail[][] = []
  for (let index = 0; index < source.length; index += ROWS_PER_PAGE) {
    pages.push(source.slice(index, index + ROWS_PER_PAGE))
  }
  return pages.length > 0 ? pages : [[]]
}

function InfoLine({
  label,
  value,
  ltr = false,
}: {
  label: string
  value: unknown
  ltr?: boolean
}) {
  return (
    <div className="tally-print-info-line">
      <span className="tally-print-label">{label}:</span>
      <span className={ltr ? 'tally-print-value tally-print-ltr' : 'tally-print-value'}>
        {valueOf(value)}
      </span>
    </div>
  )
}

function IndustrialEstateLogo() {
  return (
    <div className="tally-print-logo" aria-label="شهرک صنعتی توس">
      <svg viewBox="0 0 64 64" aria-hidden>
        <circle cx="32" cy="23" r="17" fill="none" stroke="currentColor" strokeWidth="2.5" />
        <path d="M15 23h34M32 6c-7 6-10 11-10 17s3 12 10 17M32 6c7 6 10 11 10 17s-3 12-10 17M18 15c8 4 20 4 28 0M18 31c8-4 20-4 28 0" fill="none" stroke="currentColor" strokeWidth="2" />
        <path d="M13 39l19 10 19-10v10L32 59 13 49z" fill="currentColor" />
      </svg>
      <span>شرکت شهرک‌های صنعتی</span>
      <small>شهرک صنعتی توس</small>
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

function containerLabel(row: PrintDetail): string {
  const structured = [row.container_type, row.container_number]
    .map((part) => String(part ?? '').trim())
    .filter(Boolean)
    .join(' - ')
  return structured || valueOf(row.type_number_kantiner)
}

type PlateParts = {
  leading: string
  letter: string
  serial: string
  region: string
}

function parsePlate(value: string | null | undefined): PlateParts | null {
  const normalized = toLatinDigits(String(value ?? '').trim())
  const parts = normalized.split('-').map((part) => part.trim())
  if (parts.length !== 4) return null

  const [leading, letter, serial, region] = parts
  if (
    !/^\d{1,2}$/.test(leading)
    || !/^[\u0600-\u06FF]+$/.test(letter)
    || !/^\d{1,3}$/.test(serial)
    || !/^\d{1,2}$/.test(region)
  ) {
    return null
  }

  return { leading, letter, serial, region }
}

function IranianPlate({ value }: { value: string | null | undefined }) {
  const parts = parsePlate(value)
  if (!parts) {
    return <span className="tally-print-ltr">{valueOf(value)}</span>
  }

  return (
    <span
      className="tally-print-plate"
      dir="ltr"
      aria-label={`پلاک ${parts.leading} ${parts.letter} ${parts.serial} ایران ${parts.region}`}
    >
      <span className="tally-print-plate-blue">
        <span>🇮🇷</span>
        <small>I.R.</small>
      </span>
      <span>{toPersianDigits(parts.leading)}</span>
      <span className="tally-print-plate-letter" dir="rtl">{parts.letter}</span>
      <span>{toPersianDigits(parts.serial)}</span>
      <span className="tally-print-plate-region" dir="rtl">
        <small>ایران</small>
        <strong>{toPersianDigits(parts.region)}</strong>
      </span>
    </span>
  )
}

function TallySheet({
  data,
  rows,
  page,
  pageCount,
}: {
  data: TallyPrintData
  rows: PrintDetail[]
  page: number
  pageCount: number
}) {
  const insured = isInsured(data.is_bimeh)
  const paddedRows: Array<PrintDetail | null> = [
    ...rows,
    ...Array.from({ length: Math.max(0, ROWS_PER_PAGE - rows.length) }, () => null),
  ]

  return (
    <section className="tally-print-sheet" dir="rtl">
      <div className="tally-print-user">
        کاربر: {valueOf(data.print_user_name)}
      </div>

      <div className="tally-print-form">
        <header className="tally-print-heading">
          <IndustrialEstateLogo />
          <div className="tally-print-heading-title">
            <strong>((تالی))</strong>
            <span>شرکت آسان تجارت فلات شرق</span>
          </div>
        </header>

        <div className="tally-print-header-fields">
          <div>
            <InfoLine label="شماره کارنه / ترانزیت" value={data.number_karaneh} ltr />
            <InfoLine label="ردیف مرزی" value={data.radef_marze} ltr />
            <InfoLine label="تاریخ ورود به مرز" value={formatJalaliDate(data.date_enter_marze)} ltr />
            <InfoLine label="تاریخ تخلیه" value={formatJalaliDate(data.date_unloading)} ltr />
            <InfoLine label="نام مرز ورود" value={data.marze_name} />
          </div>
          <div>
            <InfoLine label="نام شرکت حمل" value={data.company_name} />
            <InfoLine label="نام نماینده شرکت حمل" value={data.representative_name} />
            <InfoLine label="صاحب کالا (الزاماً به اظهار شرکت حمل)" value={data.owner_name} />
            <InfoLine label="مبدأ حمل" value={data.country_name} />
            <InfoLine
              label="شماره بیمه‌نامه / شرکت بیمه‌گر"
              value={[data.number_bimeh, data.company_bimeh].filter(Boolean).join(' / ')}
              ltr
            />
          </div>
          <div>
            <InfoLine label="شماره تالی" value={data.tali_number} ltr />
            <InfoLine label="شناسه ملی صاحب کالا" value={data.owner_national_code} ltr />
            <InfoLine label="شماره بارنامه" value={data.number_barnameh} ltr />
            <InfoLine label="نام ارزیاب" value={data.name_arzyab} />
          </div>
        </div>

        <table className="tally-print-table">
          <colgroup>
            <col style={{ width: '3%' }} />
            <col style={{ width: '5%' }} />
            <col style={{ width: '6%' }} />
            <col style={{ width: '6%' }} />
            <col style={{ width: '13%' }} />
            <col style={{ width: '8%' }} />
            <col style={{ width: '7%' }} />
            <col style={{ width: '4%' }} />
            <col style={{ width: '6%' }} />
            <col style={{ width: '11%' }} />
            <col style={{ width: '14%' }} />
            <col style={{ width: '7%' }} />
            <col style={{ width: '10%' }} />
          </colgroup>
          <thead>
            <tr>
              <th>ردیف</th>
              <th>ش. طاق</th>
              <th>قبض انبار</th>
              <th>علامت کالا</th>
              <th>شرح کالا</th>
              <th dir="ltr">H S C O D E</th>
              <th>نوع بسته‌بندی</th>
              <th>تعداد</th>
              <th>وزن</th>
              <th>شماره حامل</th>
              <th>نوع و شماره کانتینر</th>
              <th>ش. قبض باسکول</th>
              <th>وزن باسکول</th>
            </tr>
          </thead>
          <tbody>
            {paddedRows.map((row, index) => (
              <tr key={row?.id_tali_details ?? `empty-${index}`}>
                <td>{page * ROWS_PER_PAGE + index + 1}</td>
                <td>{valueOf(row?.tagh_name)}</td>
                <td className="tally-print-ltr">{valueOf(row?.number_ghabze_anbar)}</td>
                <td className="tally-print-ltr">{valueOf(row?.code_groupe_kala)}</td>
                <td>{valueOf(row?.description_kala)}</td>
                <td className="tally-print-ltr">{valueOf(row?.hscode)}</td>
                <td>{valueOf(row?.type_bastem)}</td>
                <td className="tally-print-ltr">{valueOf(row?.number_kala)}</td>
                <td className="tally-print-ltr">{valueOf(row?.weighte)}</td>
                <td><IranianPlate value={row?.number_hamel} /></td>
                <td className="tally-print-ltr">{row ? containerLabel(row) : EMPTY}</td>
                <td className="tally-print-ltr">{valueOf(row?.number_ghabze_bskol)}</td>
                <td className="tally-print-ltr">{valueOf(row?.weighte_baskol)}</td>
              </tr>
            ))}
          </tbody>
        </table>

        <div className="tally-print-insurance">
          <div className="tally-print-insurance-choice">
            <CheckBox checked={insured} label="بیمه دارد" />
            <CheckBox checked={!insured} label="بیمه ندارد" />
          </div>
          <div className="tally-print-notes">
            <strong>توضیحات:</strong>
            <span>{EMPTY}</span>
          </div>
          <div className="tally-print-law">
            {insured
              ? 'طبق ماده ۲۵ قانون امور گمرکی و بر اساس شماره بیمه‌نامه فوق، کالای درج‌شده در تالی بیمه می‌باشد و نیازی به بیمه مجدد توسط گمرک شهرک صنعتی توس (شرکت آسان تجارت فلات شرق) در طول مدت انبارداری و اعتبار بیمه‌نامه مذکور ندارد.'
              : <span className="tally-print-no-insurance"></span>}
          </div>
        </div>

        <footer className="tally-print-signatures">
          <div>
            <strong>نام و امضاء انباردار</strong>
            <span>{valueOf(data.name_anbardar)}</span>
          </div>
          <div>
            <strong>تأیید گمرک</strong>
            <span>{valueOf(data.accepted_gomrok)}</span>
          </div>
          <div>
            <strong>مهر و امضاء شرکت حمل و ناقل</strong>
            <span>{valueOf(data.company_name)}</span>
          </div>
        </footer>
      </div>

      {pageCount > 1 && (
        <div className="tally-print-page-number">
          صفحه {page + 1} از {pageCount}
        </div>
      )}
    </section>
  )
}

export function TallyPrintPage() {
  const { tallyNumber = '' } = useParams<{ tallyNumber: string }>()
  const isLegacyId = /^\d+$/.test(tallyNumber)

  const {
    data: header,
    isLoading: isHeaderLoading,
    isError: isHeaderError,
  } = useQuery({
    queryKey: ['tally-print-header', tallyNumber],
    queryFn: () => apiGet<TallyHeaderLookup>(
      isLegacyId
        ? `/tally-header/${tallyNumber}`
        : `/tally-header/by-number/${encodeURIComponent(tallyNumber)}`
    ),
  })

  const headerId = header?.id_tali == null ? undefined : Number(header.id_tali)
  const {
    data,
    isLoading: isPrintLoading,
    isError: isPrintError,
  } = useQuery({
    queryKey: ['tally-print-data', headerId],
    queryFn: () => apiGet<TallyPrintData>(`/tally/${headerId}/print`),
    enabled: headerId != null,
  })

  const {
    data: currentUser,
    isLoading: isUserLoading,
  } = useQuery({
    queryKey: ['current-user'],
    queryFn: () => apiGet<CurrentUser>('/auth/me'),
  })

  const printData = data
    ? {
        ...data,
        print_user_name: firstValue(
          currentUser?.full_name,
          currentUser?.username,
          data.print_user_name,
        ),
      }
    : undefined

  useEffect(() => {
    if (data?.tali_number) document.title = `تالی ${data.tali_number}`
    return () => {
      document.title = 'سامانه انبار'
    }
  }, [data?.tali_number])

  if (
    isHeaderLoading
    || isPrintLoading
    || isUserLoading
  ) {
    return (
      <Center className="tally-print-state">
        <Loader />
        <Text>در حال آماده‌سازی تالی برای چاپ…</Text>
      </Center>
    )
  }

  if (isHeaderError || isPrintError || !printData) {
    return (
      <Center className="tally-print-state">
        <Text c="red">اطلاعات تالی برای چاپ بارگذاری نشد.</Text>
        <Button variant="default" onClick={() => window.close()}>بستن</Button>
      </Center>
    )
  }

  const pages = splitRows(printData.details)

  return (
    <main className="tally-print-page">
      <div className="tally-print-toolbar" dir="rtl">
        <Group justify="space-between">
          <div>
            <Text fw={700}>پیش‌نمایش تالی {printData.tali_number}</Text>
            <Text size="sm" c="dimmed">چاپ روی کاغذ A4 با حالت افقی</Text>
          </div>
          <Group>
            <Button leftSection={<IconPrint size={18} />} onClick={() => window.print()}>
              چاپ
            </Button>
            <Button variant="default" onClick={() => window.close()}>
              بستن
            </Button>
          </Group>
        </Group>
      </div>

      {pages.map((rows, page) => (
        <TallySheet
          key={page}
          data={printData}
          rows={rows}
          page={page}
          pageCount={pages.length}
        />
      ))}
    </main>
  )
}
