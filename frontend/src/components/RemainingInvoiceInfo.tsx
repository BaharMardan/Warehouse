import type { RemainingSnapshot } from '../pages/invoiceTypes'
import { quantity } from '../pages/invoiceTypes'

export function RemainingInvoiceInfo({ info, receiptNumber }: { info?: RemainingSnapshot | null; receiptNumber?: string | null }) {
  if (!info) return null
  return <div dir="rtl" style={{ marginBlock: 12, padding: 12, border: '1px solid #ddd', borderRadius: 8 }}>
    <strong>صورتحساب باقی‌مانده</strong>
    <div>صورتحساب اصلی: <a href={`/invoice/${info.original_invoice_id}`}>{info.original_invoice_id}</a>
      {' — '}قبض اصلی: <a href={`/ghabz/${info.receipt_id}`}><bdi dir="ltr">{receiptNumber || '—'}</bdi></a></div>
    {info.inputs.days != null && <div>تعداد روز: {quantity(info.inputs.days)}</div>}
    {info.inputs.insurance_percent != null && <div>درصد بیمه باقی‌مانده: {quantity(info.inputs.insurance_percent)}٪</div>}
    {(info.rows ?? [{ inputs: info.inputs, source: info.source }]).map((row, index) => <div key={index}>
    {info.inputs.days == null && row.inputs.days != null && <div>تعداد روز: {quantity(row.inputs.days)}</div>}
    <div>{row.source.description} — HS Code: <bdi>{row.inputs.hscode}</bdi> — کد گروه کالا: <bdi>{row.inputs.kala_code}</bdi></div>
    <div>{info.cargo === 'volumetric' ? 'تعداد پالت باقی‌مانده' : 'وزن باقی‌مانده (کیلوگرم)'}: {quantity(row.inputs.amount)}
      {info.inputs.insurance_percent == null && row.inputs.insurance_percent != null && <> — درصد بیمه: {quantity(row.inputs.insurance_percent)}٪</>}</div>
    </div>)}
  </div>
}
