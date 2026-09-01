// import { useEffect, useState } from 'react'
// import { useParams, useNavigate } from 'react-router-dom'
// import { BackButton } from '../components/BackButton'
// import { useQuery } from '@tanstack/react-query'
// import { toJalaali } from 'jalaali-js'
// import {
//   Title, Button, Group, Paper, Loader, Center, Text,
// } from '@mantine/core'
// import {
//   Bookmark,
//   CalendarDays,
//   ClipboardList,
//   FileText,
//   MapPin,
//   PencilLine,
//   ReceiptText,
//   ShieldCheck,
//   Truck,
//   UserRound,
// } from 'lucide-react'
// import { IconPrint } from '../components/icons'
// import { apiGet } from '../api/client'
// // import { TallyDiamoundSection } from '../components/TallyDiamoundSection'
// import { GhabzIssueModal } from '../components/GhabzIssueModal'
// import { TallyJunctionSection } from '../components/TallyJunctionSection'
// import { TallyGoodsGrid } from '../components/TallyGoodsGrid'
// import { tallyJunctions } from '../components/junctions'
// import { TallyNumber } from '../components/TallyNumber'
// import './TallyDetailPage.css'
// /**
//  * TallyDetailPage — one tally's detail view at /tally/:tallyNumber.
//  * Top: header actions (edit button returns to the form).
//  * Below: the goods-lines grid (جزئیات تالی), now owned by TallyGoodsGrid — rows are
//  * added and edited IN PLACE so the operator can read the row above while filling the
//  * next one, instead of entering them through a modal that covered it.
//  */

// type TallySummaryData = {
//   number_karaneh: string | null
//   radef_marze: number | null
//   date_enter_marze: string | null
//   number_bimeh: string | null
//   company_bimeh: string | null
//   owner_name: string | null
//   country_name: string | null
//   company_name: string | null
//   representative_name: string | null
// }

// function firstPresent(...values: unknown[]): unknown {
//   return values.find((value) => value != null && String(value).trim() !== '') ?? null
// }

// function displayValue(value: unknown): string {
//   return value == null || String(value).trim() === '' ? '—' : String(value)
// }

// function formatJalaliDate(value: unknown): string {
//   if (value == null || String(value).trim() === '') return '—'
//   const raw = String(value)
//   const [gy, gm, gd] = raw.slice(0, 10).split('-').map(Number)
//   if (!gy || !gm || !gd) return raw

//   try {
//     const { jy, jm, jd } = toJalaali(gy, gm, gd)
//     return `${jy}/${String(jm).padStart(2, '0')}/${String(jd).padStart(2, '0')}`
//   } catch {
//     return raw
//   }
// }

// function SummaryLine({
//   icon,
//   label,
//   value,
//   tone,
//   ltr = false,
// }: {
//   icon: React.ReactNode
//   label: string
//   value: unknown
//   tone: 'blue' | 'violet' | 'green'
//   ltr?: boolean
// }) {
//   return (
//     <div className="tally-detail-summary-line">
//       <span
//         className={`tally-detail-summary-icon tally-detail-summary-icon-${tone}`}
//         aria-hidden
//       >
//         {icon}
//       </span>
//       <div className="tally-detail-summary-content">
//         <span className="tally-detail-summary-label">{label}</span>
//         <strong className="tally-detail-summary-value">
//           <bdi dir={ltr ? 'ltr' : 'auto'}>{displayValue(value)}</bdi>
//         </strong>
//       </div>
//     </div>
//   )
// }

// export function TallyDetailPage() {
//   const { tallyNumber, tallyId } = useParams<{
//     tallyNumber?: string
//     tallyId?: string
//   }>()
//   const reference = tallyId ?? tallyNumber ?? ''
//   const isLegacyId = tallyId != null
//   const navigate = useNavigate()
//   const [issueOpen, setIssueOpen] = useState(false)

//   // The public URL uses TALI_NUMBER. The database ID is resolved once and then
//   // retained only for relational API calls below this page.
//   const {
//     data: header,
//     isLoading: isHeaderLoading,
//     isError: isHeaderError,
//   } = useQuery({
//     queryKey: ['tally-header', isLegacyId ? 'id' : 'number', reference],
//     queryFn: () => apiGet<Record<string, any>>(
//       isLegacyId
//         ? `/tally-header/${tallyId}`
//         : `/tally-header/by-number/${encodeURIComponent(tallyNumber ?? '')}`
//     ),
//     enabled: reference !== '',
//   })
//   const headerId = header?.id_tali == null ? undefined : Number(header.id_tali)

//   const { data: summary } = useQuery({
//     queryKey: ['tally-summary', headerId],
//     queryFn: () => apiGet<TallySummaryData>(`/tally/${headerId}/print`),
//     enabled: headerId != null,
//   })

//   useEffect(() => {
//     if (isLegacyId && header?.tali_number) {
//       navigate(`/tally/${encodeURIComponent(String(header.tali_number))}`, { replace: true })
//     }
//   }, [header?.tali_number, isLegacyId, navigate])

//   return (
//     <div dir="rtl" className="tally-detail-page">
//       <Paper className="tally-detail-hero" radius="xl">
//         <div className="tally-detail-title-block">
//           <span className="tally-detail-title-icon" aria-hidden>
//             <ClipboardList size={29} strokeWidth={1.8} />
//           </span>
//           <div>
//             <Text className="tally-detail-eyebrow">مدیریت اطلاعات تالی</Text>
//             <Title order={2} className="tally-detail-title">
//               جزئیات تالی شماره{' '}
//               <TallyNumber value={header?.tali_number ?? tallyNumber} />
//             </Title>
//             <Text className="tally-detail-subtitle">
//               ردیف‌های کالا و تمام خدمات مرتبط با این تالی را از این صفحه مدیریت کنید.
//             </Text>
//           </div>
//         </div>

//         <Group className="tally-detail-actions" gap="sm">
//           <Button
//             variant="filled"
//             leftSection={<IconPrint size={18} />}
//             onClick={() => {
//               const publicNumber = header?.tali_number ?? tallyNumber
//               const printPath = publicNumber
//                 ? `/tally/${encodeURIComponent(String(publicNumber))}/print`
//                 : `/tally/id/${tallyId}/print`
//               window.open(printPath, '_blank', 'noopener,noreferrer')
//             }}
//             disabled={headerId == null}
//           >
//             چاپ تالی
//           </Button>
//           <Button
//             variant="light"
//             leftSection={<PencilLine size={17} />}
//             onClick={() => {
//               const publicNumber = header?.tali_number ?? tallyNumber
//               navigate(publicNumber
//                 ? `/tally/${encodeURIComponent(String(publicNumber))}/edit`
//                 : `/tally/id/${tallyId}/edit`)
//             }}
//           >
//             ویرایش سربرگ
//           </Button>
//           <Button
//             variant="light"
//             color="teal"
//             leftSection={<ReceiptText size={17} />}
//             onClick={() => setIssueOpen(true)}
//             disabled={headerId == null}
//           >
//             صدور قبض انبار
//           </Button>
//           <BackButton to="/tally" />
//         </Group>
//       </Paper>

//       <section className="tally-detail-summary-grid" aria-label="خلاصه اطلاعات تالی">
//         <Paper className="tally-detail-summary-card" radius="lg">
//           <SummaryLine
//             icon={<FileText size={20} strokeWidth={1.8} />}
//             label="شماره کارنه / ترانزیت"
//             value={firstPresent(summary?.number_karaneh, header?.number_karaneh)}
//             tone="blue"
//             ltr
//           />
//           <SummaryLine
//             icon={<ShieldCheck size={20} strokeWidth={1.8} />}
//             label="شماره بیمه‌نامه / بیمه‌گر"
//             value={[
//               firstPresent(summary?.number_bimeh, header?.number_bimeh),
//               firstPresent(summary?.company_bimeh, header?.company_bimeh),
//             ].filter((value) => value != null && String(value).trim() !== '').join(' / ')}
//             tone="blue"
//             ltr
//           />
//         </Paper>

//         <Paper className="tally-detail-summary-card" radius="lg">
//           <SummaryLine
//             icon={<UserRound size={20} strokeWidth={1.8} />}
//             label="صاحب کالا (بنا به اظهار شرکت حمل)"
//             value={summary?.owner_name}
//             tone="violet"
//           />
//           <SummaryLine
//             icon={<MapPin size={20} strokeWidth={1.8} />}
//             label="مبدأ حمل"
//             value={summary?.country_name}
//             tone="violet"
//           />
//         </Paper>

//         <Paper className="tally-detail-summary-card" radius="lg">
//           <SummaryLine
//             icon={<Truck size={20} strokeWidth={1.8} />}
//             label="نام شرکت حمل"
//             value={summary?.company_name}
//             tone="green"
//           />
//           <SummaryLine
//             icon={<UserRound size={20} strokeWidth={1.8} />}
//             label="نماینده شرکت حمل"
//             value={summary?.representative_name}
//             tone="green"
//           />
//         </Paper>

//         <Paper className="tally-detail-summary-card" radius="lg">
//           <SummaryLine
//             icon={<Bookmark size={20} strokeWidth={1.8} />}
//             label="ردیف مرزی"
//             value={firstPresent(summary?.radef_marze, header?.radef_marze)}
//             tone="blue"
//             ltr
//           />
//           <SummaryLine
//             icon={<CalendarDays size={20} strokeWidth={1.8} />}
//             label="تاریخ ورود به مرز"
//             value={formatJalaliDate(firstPresent(summary?.date_enter_marze, header?.date_enter_marze))}
//             tone="blue"
//             ltr
//           />
//         </Paper>
//       </section>

//       {isHeaderLoading && (
//         <Center className="tally-detail-state">
//           <Loader size="sm" />
//           <Text>در حال بارگذاری تالی...</Text>
//         </Center>
//       )}
//       {isHeaderError && (
//         <Center className="tally-detail-state tally-detail-state-error">
//           <Text>خطا در بارگذاری تالی.</Text>
//         </Center>
//       )}

//       <TallyGoodsGrid tallyId={headerId} />

//       <div className="tally-detail-junctions">
//         {headerId != null && tallyJunctions.map((cfg) => (
//           <TallyJunctionSection key={cfg.key} config={cfg} tallyId={headerId} />
//         ))}
//       </div>

//       <GhabzIssueModal
//         opened={issueOpen}
//         onClose={() => setIssueOpen(false)}
//         tallyId={headerId}
//         tallyNumber={header?.tali_number ?? tallyNumber}
//         onIssued={(result) => {
//           setIssueOpen(false)
//           navigate(`/ghabz/${result.id_ghabz}`)
//         }}
//       />

//     </div>
//   )
// }

import { useEffect, useState } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { BackButton } from '../components/BackButton'
import { useQuery } from '@tanstack/react-query'
import { toJalaali } from 'jalaali-js'
import {
  Alert, Title, Button, Group, Paper, Loader, Center, Text,
} from '@mantine/core'
import {
  Bookmark,
  CalendarDays,
  ClipboardList,
  FileText,
  MapPin,
  PencilLine,
  ReceiptText,
  ShieldCheck,
  TriangleAlert,
  Truck,
  UserRound,
} from 'lucide-react'
import { IconPrint } from '../components/icons'
import { apiGet } from '../api/client'
// import { TallyDiamoundSection } from '../components/TallyDiamoundSection'
import { GhabzIssueModal } from '../components/GhabzIssueModal'
import { TallyJunctionSection } from '../components/TallyJunctionSection'
import { TallyGoodsGrid } from '../components/TallyGoodsGrid'
import { tallyJunctions } from '../components/junctions'
import { TallyNumber } from '../components/TallyNumber'
import './TallyDetailPage.css'
/**
 * TallyDetailPage — one tally's detail view at /tally/:tallyNumber.
 * Top: header actions (edit button returns to the form).
 * Below: the goods-lines grid (جزئیات تالی), now owned by TallyGoodsGrid — rows are
 * added and edited IN PLACE so the operator can read the row above while filling the
 * next one, instead of entering them through a modal that covered it.
 */

type TallySummaryData = {
  number_karaneh: string | null
  radef_marze: number | null
  date_enter_marze: string | null
  number_bimeh: string | null
  company_bimeh: string | null
  owner_name: string | null
  country_name: string | null
  company_name: string | null
  representative_name: string | null
}

// One entry per (بیمه نامه, ثبت سفارش) pair of this tally. Customs values are
// summed across all tallies that share the pair; insured_ceiling is the
// policy's single value (repeated on rows, extracted with MAX, never summed).
// is_over entries carry the invoice difference.
type InsuranceCheckEntry = {
  number_bimeh: string
  sabt_sefaresh_number: string
  total_customs_value: number
  insured_ceiling: number | null
  overage: number | null
  is_over: boolean
  tally_numbers: string[]
}

function formatMoney(value: number): string {
  return Number(value).toLocaleString('fa-IR')
}

function firstPresent(...values: unknown[]): unknown {
  return values.find((value) => value != null && String(value).trim() !== '') ?? null
}

function displayValue(value: unknown): string {
  return value == null || String(value).trim() === '' ? '—' : String(value)
}

function formatJalaliDate(value: unknown): string {
  if (value == null || String(value).trim() === '') return '—'
  const raw = String(value)
  const [gy, gm, gd] = raw.slice(0, 10).split('-').map(Number)
  if (!gy || !gm || !gd) return raw

  try {
    const { jy, jm, jd } = toJalaali(gy, gm, gd)
    return `${jy}/${String(jm).padStart(2, '0')}/${String(jd).padStart(2, '0')}`
  } catch {
    return raw
  }
}

function SummaryLine({
  icon,
  label,
  value,
  tone,
  ltr = false,
}: {
  icon: React.ReactNode
  label: string
  value: unknown
  tone: 'blue' | 'violet' | 'green'
  ltr?: boolean
}) {
  return (
    <div className="tally-detail-summary-line">
      <span
        className={`tally-detail-summary-icon tally-detail-summary-icon-${tone}`}
        aria-hidden
      >
        {icon}
      </span>
      <div className="tally-detail-summary-content">
        <span className="tally-detail-summary-label">{label}</span>
        <strong className="tally-detail-summary-value">
          <bdi dir={ltr ? 'ltr' : 'auto'}>{displayValue(value)}</bdi>
        </strong>
      </div>
    </div>
  )
}

export function TallyDetailPage() {
  const { tallyNumber, tallyId } = useParams<{
    tallyNumber?: string
    tallyId?: string
  }>()
  const reference = tallyId ?? tallyNumber ?? ''
  const isLegacyId = tallyId != null
  const navigate = useNavigate()
  const [issueOpen, setIssueOpen] = useState(false)

  // The public URL uses TALI_NUMBER. The database ID is resolved once and then
  // retained only for relational API calls below this page.
  const {
    data: header,
    isLoading: isHeaderLoading,
    isError: isHeaderError,
  } = useQuery({
    queryKey: ['tally-header', isLegacyId ? 'id' : 'number', reference],
    queryFn: () => apiGet<Record<string, any>>(
      isLegacyId
        ? `/tally-header/${tallyId}`
        : `/tally-header/by-number/${encodeURIComponent(tallyNumber ?? '')}`
    ),
    enabled: reference !== '',
  })
  const headerId = header?.id_tali == null ? undefined : Number(header.id_tali)

  const { data: summary } = useQuery({
    queryKey: ['tally-summary', headerId],
    queryFn: () => apiGet<TallySummaryData>(`/tally/${headerId}/print`),
    enabled: headerId != null,
  })

  const { data: insuranceCheck } = useQuery({
    queryKey: ['tally-insurance-check', headerId],
    queryFn: () => apiGet<InsuranceCheckEntry[]>(`/tally/${headerId}/insurance-check`),
    enabled: headerId != null,
  })
  const overInsured = (insuranceCheck ?? []).filter((entry) => entry.is_over)

  useEffect(() => {
    if (isLegacyId && header?.tali_number) {
      navigate(`/tally/${encodeURIComponent(String(header.tali_number))}`, { replace: true })
    }
  }, [header?.tali_number, isLegacyId, navigate])

  return (
    <div dir="rtl" className="tally-detail-page">
      {overInsured.map((entry) => (
        <Alert
          key={`${entry.number_bimeh}|${entry.sabt_sefaresh_number}`}
          color="red"
          variant="light"
          radius="lg"
          mb="md"
          icon={<TriangleAlert size={20} />}
          title="سقف ارزش کالای بیمه‌شده پر شده است."
        >
          مجموع ارزش کالای گمرکی تالی‌های بیمه‌نامه{' '}
          <bdi dir="ltr">«{entry.number_bimeh || '—'}»</bdi>
          {entry.sabt_sefaresh_number !== '' && (
            <> (ثبت سفارش <bdi dir="ltr">«{entry.sabt_sefaresh_number}»</bdi>)</>
          )}{' '}
          برابر {formatMoney(entry.total_customs_value)} است و از سقف ارزش
          کالای بیمه‌شده ({formatMoney(entry.insured_ceiling ?? 0)}) بیشتر شده
          است؛ مبلغ مابه‌التفاوت {formatMoney(entry.overage ?? 0)} باید در
          صورتحساب اعمال شود.
          {entry.tally_numbers.length > 0 && (
            <> تالی‌های این بیمه: {entry.tally_numbers.join('، ')}</>
          )}
        </Alert>
      ))}
      <Paper className="tally-detail-hero" radius="xl">
        <div className="tally-detail-title-block">
          <span className="tally-detail-title-icon" aria-hidden>
            <ClipboardList size={29} strokeWidth={1.8} />
          </span>
          <div>
            <Text className="tally-detail-eyebrow">مدیریت اطلاعات تالی</Text>
            <Title order={2} className="tally-detail-title">
              جزئیات تالی شماره{' '}
              <TallyNumber value={header?.tali_number ?? tallyNumber} />
            </Title>
            <Text className="tally-detail-subtitle">
              ردیف‌های کالا و تمام خدمات مرتبط با این تالی را از این صفحه مدیریت کنید.
            </Text>
          </div>
        </div>

        <Group className="tally-detail-actions" gap="sm">
          <Button
            variant="filled"
            leftSection={<IconPrint size={18} />}
            onClick={() => {
              const publicNumber = header?.tali_number ?? tallyNumber
              const printPath = publicNumber
                ? `/tally/${encodeURIComponent(String(publicNumber))}/print`
                : `/tally/id/${tallyId}/print`
              window.open(printPath, '_blank', 'noopener,noreferrer')
            }}
            disabled={headerId == null}
          >
            چاپ تالی
          </Button>
          <Button
            variant="light"
            leftSection={<PencilLine size={17} />}
            onClick={() => {
              const publicNumber = header?.tali_number ?? tallyNumber
              navigate(publicNumber
                ? `/tally/${encodeURIComponent(String(publicNumber))}/edit`
                : `/tally/id/${tallyId}/edit`)
            }}
          >
            ویرایش سربرگ
          </Button>
          <Button
            variant="light"
            color="teal"
            leftSection={<ReceiptText size={17} />}
            onClick={() => setIssueOpen(true)}
            disabled={headerId == null}
          >
            صدور قبض انبار
          </Button>
          <BackButton to="/tally" />
        </Group>
      </Paper>

      <section className="tally-detail-summary-grid" aria-label="خلاصه اطلاعات تالی">
        <Paper className="tally-detail-summary-card" radius="lg">
          <SummaryLine
            icon={<FileText size={20} strokeWidth={1.8} />}
            label="شماره کارنه / ترانزیت"
            value={firstPresent(summary?.number_karaneh, header?.number_karaneh)}
            tone="blue"
            ltr
          />
          <SummaryLine
            icon={<ShieldCheck size={20} strokeWidth={1.8} />}
            label="شماره بیمه‌نامه / بیمه‌گر"
            value={[
              firstPresent(summary?.number_bimeh, header?.number_bimeh),
              firstPresent(summary?.company_bimeh, header?.company_bimeh),
            ].filter((value) => value != null && String(value).trim() !== '').join(' / ')}
            tone="blue"
            ltr
          />
        </Paper>

        <Paper className="tally-detail-summary-card" radius="lg">
          <SummaryLine
            icon={<UserRound size={20} strokeWidth={1.8} />}
            label="صاحب کالا (بنا به اظهار شرکت حمل)"
            value={summary?.owner_name}
            tone="violet"
          />
          <SummaryLine
            icon={<MapPin size={20} strokeWidth={1.8} />}
            label="مبدأ حمل"
            value={summary?.country_name}
            tone="violet"
          />
        </Paper>

        <Paper className="tally-detail-summary-card" radius="lg">
          <SummaryLine
            icon={<Truck size={20} strokeWidth={1.8} />}
            label="نام شرکت حمل"
            value={summary?.company_name}
            tone="green"
          />
          <SummaryLine
            icon={<UserRound size={20} strokeWidth={1.8} />}
            label="نماینده شرکت حمل"
            value={summary?.representative_name}
            tone="green"
          />
        </Paper>

        <Paper className="tally-detail-summary-card" radius="lg">
          <SummaryLine
            icon={<Bookmark size={20} strokeWidth={1.8} />}
            label="ردیف مرزی"
            value={firstPresent(summary?.radef_marze, header?.radef_marze)}
            tone="blue"
            ltr
          />
          <SummaryLine
            icon={<CalendarDays size={20} strokeWidth={1.8} />}
            label="تاریخ ورود به مرز"
            value={formatJalaliDate(firstPresent(summary?.date_enter_marze, header?.date_enter_marze))}
            tone="blue"
            ltr
          />
        </Paper>
      </section>

      {isHeaderLoading && (
        <Center className="tally-detail-state">
          <Loader size="sm" />
          <Text>در حال بارگذاری تالی...</Text>
        </Center>
      )}
      {isHeaderError && (
        <Center className="tally-detail-state tally-detail-state-error">
          <Text>خطا در بارگذاری تالی.</Text>
        </Center>
      )}

      <TallyGoodsGrid tallyId={headerId} />

      <div className="tally-detail-junctions">
        {headerId != null && tallyJunctions.map((cfg) => (
          <TallyJunctionSection key={cfg.key} config={cfg} tallyId={headerId} />
        ))}
      </div>

      <GhabzIssueModal
        opened={issueOpen}
        onClose={() => setIssueOpen(false)}
        tallyId={headerId}
        tallyNumber={header?.tali_number ?? tallyNumber}
        onIssued={(result) => {
          setIssueOpen(false)
          navigate(`/ghabz/${result.id_ghabz}`)
        }}
      />

    </div>
  )
}