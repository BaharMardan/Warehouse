import { useCurrentUser } from '../auth/usePermissions'
import { CompanyLogo } from '../components/CompanyLogo'
import { useEffect, useRef } from 'react'
import { useQuery } from '@tanstack/react-query'
import { useParams } from 'react-router-dom'
import { apiGet } from '../api/client'
import { IconPrint } from '../components/icons'
import { InvoiceLine, SavedInvoice, invoiceSections, jalali, money, quantity, signedMoney } from './invoiceTypes'
import './TallyPrintPage.css'
import './InvoicePrintPage.css'

const shown = (value: string | number | null | undefined) =>
  value == null || value === '' ? '—' : value

export function InvoicePrintPage() {
  const { id } = useParams()
  const invoiceId = Number(id)
  const userQuery = useCurrentUser()
  const sheetRef = useRef<HTMLElement>(null)

  useEffect(() => {
    const resetScale = () => {
      const sheet = sheetRef.current
      sheet?.parentElement?.classList.remove('invoice-print-layout', 'invoice-print-compact')
      sheet?.style.removeProperty('--invoice-print-scale')
      sheet?.style.removeProperty('--invoice-print-width')
    }
    const fitToPage = () => {
      const sheet = sheetRef.current
      const page = sheet?.parentElement
      if (!sheet || !page) return
      resetScale()
      // Apply the actual print layout before measuring, even if the browser
      // dispatches beforeprint while screen media styles are still active.
      page.classList.add('invoice-print-layout')
      const availableHeight = 198 * 96 / 25.4
      if (sheet.offsetHeight <= availableHeight) return
      page.classList.add('invoice-print-compact')
      let scale = 1
      for (let attempt = 0; attempt < 8; attempt++) {
        const height = sheet.offsetHeight * scale
        if (height <= availableHeight) break
        scale *= (availableHeight - 2) / height
        sheet.style.setProperty('--invoice-print-scale', String(scale))
        // Compensate the width so scaling never leaves a narrow, right-aligned form.
        sheet.style.setProperty('--invoice-print-width', `${285 / scale}mm`)
      }
    }
    window.addEventListener('beforeprint', fitToPage)
    window.addEventListener('afterprint', resetScale)
    return () => {
      window.removeEventListener('beforeprint', fitToPage)
      window.removeEventListener('afterprint', resetScale)
    }
  }, [])

  const { data, isLoading, isError } = useQuery({
    queryKey: ['invoice', invoiceId],
    queryFn: () => apiGet<SavedInvoice>(`/invoice/${invoiceId}`),
    enabled: Number.isInteger(invoiceId) && invoiceId > 0,
  })

  if (isLoading || userQuery.isLoading) return <p dir="rtl">در حال بارگذاری صورتحساب…</p>
  if (isError || !data) return <p dir="rtl">صورتحساب یافت نشد.</p>

  const h = data.header
  const printUser = userQuery.data?.full_name || userQuery.data?.username

  return (
    <main className="tally-print-page invoice-print-page" dir="rtl">
      <section ref={sheetRef} className="tally-print-sheet invoice-print-sheet">
        <header className="tally-print-heading invoice-print-heading">
          <div className="tally-print-preview-heading">
            <button
              className="tally-print-action"
              type="button"
              onClick={() => window.print()}
              aria-label="چاپ صورتحساب"
              title="چاپ صورتحساب"
            >
              <IconPrint size={27} stroke={1.8} />
            </button>

            <div>
              <h1>
                <span className="tally-print-screen-title">پیش‌نمایش</span>
                <span className="tally-print-paper-title">{data.remaining ? 'صورتحساب باقی‌مانده' : 'صورتحساب'}</span>
                <bdi dir="ltr">{h.id_sorat}</bdi>
              </h1>
              <p>چاپ روی کاغذ A4 با حالت افقی</p>
            </div>
          </div>

          <div className="tally-print-brand invoice-print-brand">
            <CompanyLogo />
            <div className="tally-print-brand-copy">
              <strong>{shown(h.seller_name)}</strong>
              <small>صورتحساب خدمات انبار</small>
              <div className="tally-print-user">کاربر: <b>{shown(printUser)}</b></div>
              <div className="tally-print-user">
                تاریخ: <b>{jalali(h.created_at)}</b>
              </div>
            </div>
          </div>
        </header>

        <div className="invoice-print-parties">
          <section className="invoice-print-box">
            <h2>مشخصات فروشنده</h2>
            <div className="invoice-print-fields">
              <span>نام شرکت: {shown(h.seller_name)}</span>
              <span>شناسه ملی: {shown(h.seller_national_id)}</span>
              <span className="invoice-print-wide">
                نشانی: {shown(h.seller_address)}
              </span>
            </div>
          </section>

          <section className="invoice-print-box">
            <h2>مشخصات خریدار</h2>
            <div className="invoice-print-fields invoice-print-buyer-fields">
              <span>نام خریدار: {shown(h.buyer_name)}</span>
              <span>شناسه ملی: {shown(h.buyer_national_id)}</span>
              <span>کد اقتصادی: {shown(h.buyer_economic_code)}</span>
              <span>شماره تماس: {shown(h.buyer_phone)}</span>
              <span>شماره کوتاژ: <bdi dir="ltr">{shown(h.buyer_kotath_code)}</bdi></span>
              <span>
                شماره قبض: <bdi dir="ltr">{shown(h.ghabz_number ?? h.buyer_ghabz_number ?? h.ghabz_id)}</bdi>
              </span>
              <span>نشانی: {shown(h.buyer_address)}</span>
            </div>
          </section>
        </div>

        {invoiceSections(data.details).modern ? <ModernTable data={data} /> :
        <table className="invoice-print-table">
          <thead>
            <tr>
              <th>ردیف</th>
              <th>شرح</th>
              <th>تعداد</th>
              <th>مبلغ کل (ریال)</th>
              <th>تخفیف (ریال)</th>
              <th>مبلغ خالص (ریال)</th>
            </tr>
          </thead>
          <tbody>
            {invoiceSections(data.details).charges.map((line, index) => (
              <tr key={line.id_detail}>
                <td>{index + 1}</td>
                <td>{shown(line.description)}</td>
                <td>{shown(line.quantity)}</td>
                <td>{money(line.price)}</td>
                <td>{money(line.discount)}</td>
                <td>
                  {money(
                    line.price == null
                      ? null
                      : Number(line.price) - Number(line.discount ?? 0)
                  )}
                </td>
              </tr>
            ))}
            <tr className="invoice-print-total">
              <td colSpan={5}>جمع کل</td>
              <td>{money(data.grand_total)}</td>
            </tr>
          </tbody>
        </table>}

        <footer className="invoice-print-footer">
          <section className="invoice-print-signature">
            <strong>تأییدکننده</strong>
            <small className="invoice-print-distribution">توزیع نسخ الکترونیکی: ۱- صدور اسناد ۲- امور مالی</small>
          </section>
          <section className="invoice-print-signature">
            <strong>نماینده صاحب کالا</strong>
            <span>{h.representative_name || ' '}</span>
          </section>
        </footer>
      </section>
    </main>
  )
}
// Combine crane charges only for printing; saved details and totals stay intact.
function printCharges(charges: InvoiceLine[]): InvoiceLine[] {
  const label = 'جابه‌جایی کانتینر با جرثقیل'
  const result: InvoiceLine[] = []
  let crane: InvoiceLine | undefined
  for (const line of charges) {
    if (line.row_kind !== 'service' || !line.description?.startsWith(label)) {
      result.push(line)
      continue
    }
    if (!crane) {
      crane = { ...line, description: label, quantity: null, weight: null, calc_note: null }
      result.push(crane)
    } else {
      crane.price = String(Number(crane.price ?? 0) + Number(line.price ?? 0))
    }
  }
  return result
}

// 1405 invoices: compact charges followed by summary rows
// «جمع مبالغ − تخفیف + مالیات − پیش‌پرداخت = مبلغ قابل پرداخت».
function ModernTable({ data }: { data: SavedInvoice }) {
  const { charges, subtotal, adjustments, prepayments, totalBeforePrepayment } = invoiceSections(data.details)
  return (
    <>
      <table className="invoice-print-table invoice-print-table-calc">
        <thead>
          <tr>
            <th>ردیف</th>
            <th>شرح</th>
            <th>تعداد</th>
            <th>وزن (کیلوگرم)</th>
            <th>مبلغ (ریال)</th>
          </tr>
        </thead>
        <tbody>
          {printCharges(charges).map((line, index) => (
            <tr key={line.id_detail}>
              <td>{index + 1}</td>
              <td>{shown(line.description)}</td>
              <td><bdi dir="ltr">{quantity(line.quantity)}</bdi></td>
              <td><bdi dir="ltr">{quantity(line.weight)}</bdi></td>
              <td><bdi dir="ltr">{money(line.price)}</bdi></td>
            </tr>
          ))}
          <tr className="invoice-print-subtotal">
            <td colSpan={4}>جمع مبالغ</td>
            <td><bdi dir="ltr">{money(subtotal)}</bdi></td>
          </tr>
          {adjustments.map((line) => (
            <tr key={line.id_detail} className="invoice-print-summary">
              <td colSpan={4}>{shown(line.description)}</td>
              <td><bdi dir="ltr">{signedMoney(line.price)}</bdi></td>
            </tr>
          ))}
          <tr className="invoice-print-total invoice-print-before-prepayment">
            <td colSpan={4}>جمع کل</td>
            <td><bdi dir="ltr">{money(totalBeforePrepayment)}</bdi></td>
          </tr>
          {prepayments.map((line) => (
            <tr key={line.id_detail} className="invoice-print-summary">
              <td colSpan={4}>{shown(line.description)}</td>
              <td><bdi dir="ltr">{signedMoney(line.price)}</bdi></td>
            </tr>
          ))}
          <tr className="invoice-print-total invoice-print-payable">
            <td colSpan={4}>مبلغ قابل پرداخت</td>
            <td><bdi dir="ltr">{money(data.grand_total)}</bdi></td>
          </tr>
        </tbody>
      </table>
    </>
  )
}
