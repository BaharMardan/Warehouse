import { normalizeSearchDigits } from './normalizeSearchDigits'

const normalize = (value: string) => normalizeSearchDigits(value).toLowerCase()

/** True when every whitespace-separated term of `query` appears in one of `fields`. */
export function matchesSearch(query: string, fields: Array<string | number | null | undefined>): boolean {
  const terms = normalize(query.trim()).split(/\s+/).filter(Boolean)
  if (!terms.length) return true
  const haystack = normalize(fields.map(field => field ?? '').join(' '))
  return terms.every(term => haystack.includes(term))
}
