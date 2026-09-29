/** Match Persian, Arabic-Indic and Latin digits without changing displayed text. */
export function normalizeSearchDigits(value: string): string {
  return value
    .replace(/[۰-۹]/g, digit => String(digit.charCodeAt(0) - 0x06f0))
    .replace(/[٠-٩]/g, digit => String(digit.charCodeAt(0) - 0x0660))
}
