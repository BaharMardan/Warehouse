import type { RemainingSnapshot } from '../pages/invoiceTypes'
import { quantity } from '../pages/invoiceTypes'

export function RemainingInvoiceInfo({ info, receiptNumber }: { info?: RemainingSnapshot | null; receiptNumber?: string | null }) {
  if (!info) return null
  return <div dir="rtl" style={{ marginBlock: 12, padding: 12, border: '1px solid #ddd', borderRadius: 8 }}>
    <strong>صورتحساب باقی‌مانده</strong>
    <div>صورتحساب اصلی: <a href={`/invoice/${info.original_invoice_id}`}>{info.original_invoice_id}</a>
      {' — '}قبض اصلی: <a href={`/ghabz/${info.receipt_id}`}><bdi dir="ltr">{receiptNumber || '—'}</bdi></a></div>
    {info.inputs.days != null && <div>تعداد روز: {quantity(info.inputs.days)}</div>}
    <div>{info.source.description} — HS Code: <bdi>{info.inputs.hscode}</bdi> — کد گروه کالا: <bdi>{info.inputs.kala_code}</bdi></div>
    <div>{info.cargo === 'volumetric' ? 'تعداد پالت باقی‌مانده' : 'وزن باقی‌مانده (کیلوگرم)'}: {quantity(info.inputs.amount)}
      {' — '}درصد بیمه: {quantity(info.inputs.insurance_percent)}٪</div>
  </div>
}
