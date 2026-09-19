import './IranianPlate.css'

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
  const parts = toLatinDigits(String(value ?? '').trim()).split('-').map((part) => part.trim())
  if (parts.length !== 4) return null

  const [leading, letter, serial, region] = parts
  if (
    !/^\d{1,2}$/.test(leading)
    || !/^[\u0600-\u06FF]+$/.test(letter)
    || !/^\d{1,3}$/.test(serial)
    || !/^\d{1,2}$/.test(region)
  ) return null

  return { leading, letter, serial, region }
}

/** A read-only Iranian plate, always rendered in its physical left-to-right order. */
export function IranianPlate({
  value,
  size = 'select',
}: {
  value: string | null | undefined
  size?: 'print' | 'select'
}) {
  const parts = parsePlate(value)
  if (!parts) {
    return <span className="iranian-plate-fallback" dir="ltr">{value?.trim() || '—'}</span>
  }

  return (
    <span
      className={`iranian-plate iranian-plate-${size}`}
      dir="ltr"
      aria-label={`پلاک ${parts.leading} ${parts.letter} ${parts.serial} ایران ${parts.region}`}
    >
      <span className="iranian-plate-blue">
        <span>🇮🇷</span>
        <small>I.R.</small>
      </span>
      <span>{toPersianDigits(parts.leading)}</span>
      <span className="iranian-plate-letter" dir="rtl">{parts.letter}</span>
      <span>{toPersianDigits(parts.serial)}</span>
      <span className="iranian-plate-region" dir="rtl">
        <small>ایران</small>
        <strong>{toPersianDigits(parts.region)}</strong>
      </span>
    </span>
  )
}
