import { TextInput } from '@mantine/core'
import { normalizeSearchDigits } from '../utils/normalizeSearchDigits'

export const validInvoiceNumber = (value: string) => /^[0-9]{1,15}$/.test(value) && Number(value) > 0

export function InvoiceNumberInput({ value, onChange, disabled = false }: {
  value: string; onChange: (value: string) => void; disabled?: boolean
}) {
  return <TextInput label="شماره صورتحساب" placeholder="شماره صورتحساب را وارد کنید" required description="شمارهٔ صورتحساب باطل‌شده قابل استفادهٔ مجدد است؛ شمارهٔ فعال باید یکتا باشد."
    value={value} onChange={event => onChange(normalizeSearchDigits(event.currentTarget.value).trim())}
    inputMode="numeric" maxLength={15} disabled={disabled}
    error={value && !validInvoiceNumber(value) ? 'شماره باید عدد صحیح مثبت و حداکثر ۱۵ رقمی باشد' : undefined}
    styles={{ input: { direction: 'ltr', textAlign: 'right' } }} />
}
