// import { useEffect, useMemo, useRef, useState } from 'react'
// import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
// import {
//   ActionIcon, Button, Center, Group, Loader, Modal, Paper, Popover,
//   Select, Stack, Table, Text, TextInput, Title, Tooltip,
// } from '@mantine/core'
// import { AlertTriangle, ArrowUp, Check, PackageOpen, Plus, X } from 'lucide-react'
// import { IconEdit, IconTrash } from './icons'
// import { apiGet, apiSend } from '../api/client'
// import { RefSelect } from './RefSelect'
// import { TermValueSelect } from './TermValueSelect'
// import { CommodityPicker, type Commodity } from './CommodityPicker'
// import { PlateInput } from './PlateInput'
// import { CONTAINER_TYPES, TYPES_WITH_NUMBER } from './ContainerFields'
// import type { StorageGroup } from './StorageGroupSelect'
// import {
//   isoToJalaliInput,
//   normalizeFlexibleJalaliInput,
//   parseFlexibleJalaliDate,
// } from '../utils/flexibleJalaliDate'
// import './TallyGoodsGrid.css'

// /**
//  * TallyGoodsGrid — the tally's goods lines (ردیف‌های کالا) as ONE in-place editable grid.
//  *
//  * Replaces the old "افزودن ردیف → modal" flow. Operators enter the same commodity across
//  * several containers, so every row repeats except the weights / weighbridge ticket /
//  * carrier plate / container number. The modal hid the previous row exactly when they
//  * needed to read it, so they were retyping from memory.
//  *
//  * The design constraint from the customer was explicit: copying is fine, INVISIBLE copying
//  * is not ("ممکن این وسط یه چیزی عوض شده باشه و متوجه نشیم"). So:
//  *   - the draft row is a real row at the bottom of the same table — the row above stays
//  *     on screen, column-aligned, which is what makes visual comparison possible;
//  *   - nothing is ever copied automatically. The operator copies, per cell (⬆ / Ctrl+D)
//  *     or per row (Alt+C), and only the fields in COPYABLE_FIELDS;
//  *   - anything filled by copy is tinted amber and STAYS amber until reviewed, and save
//  *     asks for confirmation while any amber cell is left;
//  *   - fields that usually differ (NEVER_COPY_FIELDS) are never touched by copy and are
//  *     warned about if they duplicate another row. They remain optional.
//  *
//  * Save uses the generic CRUD endpoints (POST/PUT/DELETE /tally-details).
//  */

// export type DetailRow = {
//   id_tali_details: number
//   id_headers_tali: number
//   id_anbar: number | null
//   anbar_name: string | null
//   id_tagh_anbar: number | null
//   tagh_name: string | null
//   number_ghabze_anbar: number | null
//   code_groupe_kala: number | null
//   description_kala: string | null
//   hscode: string | null
//   type_bastem: string | null
//   number_kala: number | null
//   number_pallet: number | null
//   value_kala: number | string | null
//   customs_value: number | string | null
//   insured_value: number | string | null
//   insurance_expiry_date: string | null
//   weighte: number | null
//   type_number_kantiner: string | null
//   number_ghabze_bskol: number | null
//   weighte_baskol: number | null
//   number_hamel: string | null
//   zarib_mahal: string | null
//   container_type: string | null
//   container_number: string | null
// }

// export type LineForm = {
//   id_anbar: number | null
//   id_tagh_anbar: number | null
//   code_groupe_kala: string
//   description_kala: string
//   hscode: string
//   type_bastem: string
//   number_kala: string
//   number_pallet: string
//   value_kala: string
//   customs_value: string
//   insured_value: string
//   insurance_expiry_date: string
//   weighte: string
//   number_ghabze_bskol: string
//   weighte_baskol: string
//   type_number_kantiner: string
//   number_hamel: string
//   zarib_mahal: string
//   container_type: string
//   container_number: string
// }

// type FieldKey = keyof LineForm

// const EMPTY_LINE: LineForm = {
//   id_anbar: null, id_tagh_anbar: null, code_groupe_kala: '', description_kala: '',
//   hscode: '', type_bastem: '', number_kala: '', number_pallet: '', value_kala: '',
//   customs_value: '', insured_value: '', insurance_expiry_date: '', weighte: '',
//   number_ghabze_bskol: '', weighte_baskol: '',
//   type_number_kantiner: '', number_hamel: '', zarib_mahal: '',
//   container_type: '', container_number: '',
// }

// /**
//  * The two field sets that make the whole feature safe. Move a key between them and the
//  * grid, the ⬆ buttons, the "کپی از بالا" button and the review warning all follow.
//  *
//  * number_kala / number_pallet / id_tagh_anbar sit in COPYABLE on purpose: in the
//  * one-commodity-many-containers case they repeat. If the customer says otherwise, move
//  * them down — nothing else needs to change.
//  */
// const COPYABLE_FIELDS: FieldKey[] = [
//   'code_groupe_kala', 'description_kala', 'hscode', 'type_bastem',
//   'number_kala', 'number_pallet', 'value_kala', 'customs_value', 'insured_value',
//   'insurance_expiry_date',
//   'id_anbar', 'id_tagh_anbar', 'zarib_mahal', 'container_type',
// ]

// const NEVER_COPY_FIELDS: FieldKey[] = [
//   'weighte', 'number_ghabze_bskol', 'weighte_baskol', 'number_hamel', 'container_number',
// ]

// /** Repeating one of these inside a single tally is nearly always a copy-paste slip. */
// const UNIQUE_FIELDS: FieldKey[] = ['number_ghabze_bskol', 'number_hamel', 'container_number']

// const ZARIB_OPTIONS = [
//   'انبارداری مسقف', 'انبارداری هانگار', 'انبارداری بارانداز', 'انبارداری محوطه',
// ]

// // ── digit / value helpers (same semantics the modal used) ────────────────────────────

// function normalizeDigits(s: string): string {
//   return s
//     .replace(/[\u06F0-\u06F9]/g, (d) => String(d.charCodeAt(0) - 0x06f0))
//     .replace(/[\u0660-\u0669]/g, (d) => String(d.charCodeAt(0) - 0x0660))
// }

// function normalizeIntegerInput(s: string): string {
//   return normalizeDigits(s).replace(/\D/g, '')
// }

// function normalizeDecimalInput(s: string): string {
//   const normalized = normalizeDigits(s)
//     .replace(/[,\u066C\s]/g, '')
//     .replace(/\u066B/g, '.')
//     .replace(/[^\d.]/g, '')
//   const [whole, ...fractionParts] = normalized.split('.')
//   return fractionParts.length === 0 ? whole : `${whole}.${fractionParts.join('')}`
// }

// function formatAmount(value: number | string | null): string {
//   if (value == null || String(value).trim() === '') return '—'
//   const amount = Number(normalizeDigits(String(value)))
//   if (!Number.isFinite(amount)) return String(value)
//   return amount.toLocaleString('en-US', { maximumFractionDigits: 2 })
// }

// const dash = (v: unknown) => (v == null || String(v).trim() === '' ? '—' : String(v))

// /** "12-ط-345-67|TR-34" -> "۱۲ ط ۳۴۵ ایران ۶۷ · TR-34" for read-only cells. */
// function formatPlate(value: string | null): string {
//   if (!value || value.trim() === '') return '—'
//   const [iranPart, foreignPart] = value.split('|')
//   const parts = (iranPart ?? '').split('-')
//   const iran = parts.length === 4 && parts.some(Boolean)
//     ? `${parts[0]} ${parts[1]} ${parts[2]} ایران ${parts[3]}`
//     : ''
//   return [iran, foreignPart].filter((p) => p && p.trim() !== '').join(' · ') || '—'
// }

// const isBlank = (v: string | number | null) =>
//   v == null || String(v).trim() === ''

// // ── column model — one source of truth for header, cells and copy ────────────────────

// type GroupKey = 'kala' | 'baskol' | 'mahal' | 'haml'

// const GROUPS: { key: GroupKey; label: string }[] = [
//   { key: 'kala', label: 'کالا' },
//   { key: 'baskol', label: 'باسکول' },
//   { key: 'mahal', label: 'محل نگهداری' },
//   { key: 'haml', label: 'حمل و کانتینر' },
// ]

// type CellKind =
//   | 'commodity' | 'text' | 'term' | 'int' | 'decimal' | 'date'
//   | 'anbar' | 'tagh' | 'zarib' | 'plate' | 'containerType' | 'containerNumber'

// type ColumnDef = {
//   key: FieldKey
//   label: string
//   group: GroupKey
//   kind: CellKind
//   width: number
// }

// const COLUMNS: ColumnDef[] = [
//   { key: 'code_groupe_kala', label: 'کالا / گروه قیمت', group: 'kala', kind: 'commodity', width: 190 },
//   { key: 'description_kala', label: 'شرح کالا', group: 'kala', kind: 'text', width: 240 },
//   { key: 'hscode', label: 'HS Code', group: 'kala', kind: 'text', width: 110 },
//   { key: 'type_bastem', label: 'نوع بسته‌بندی', group: 'kala', kind: 'term', width: 130 },
//   { key: 'number_kala', label: 'تعداد', group: 'kala', kind: 'int', width: 80 },
//   { key: 'number_pallet', label: 'تعداد پالت', group: 'kala', kind: 'int', width: 90 },
//   { key: 'value_kala', label: 'ارزش کالا', group: 'kala', kind: 'decimal', width: 110 },
//   { key: 'customs_value', label: 'ارزش کالای گمرکی', group: 'kala', kind: 'decimal', width: 140 },
//   { key: 'insured_value', label: 'ارزش کالای بیمه‌شده', group: 'kala', kind: 'decimal', width: 150 },
//   { key: 'insurance_expiry_date', label: 'تاریخ اتمام بیمه', group: 'kala', kind: 'date', width: 145 },
//   { key: 'weighte', label: 'وزن اظهار', group: 'baskol', kind: 'decimal', width: 100 },
//   { key: 'number_ghabze_bskol', label: 'شماره قبض باسکول', group: 'baskol', kind: 'int', width: 130 },
//   { key: 'weighte_baskol', label: 'وزن باسکول', group: 'baskol', kind: 'decimal', width: 110 },
//   { key: 'id_anbar', label: 'انبار', group: 'mahal', kind: 'anbar', width: 130 },
//   { key: 'id_tagh_anbar', label: 'طاق', group: 'mahal', kind: 'tagh', width: 110 },
//   { key: 'zarib_mahal', label: 'ضریب محل', group: 'mahal', kind: 'zarib', width: 150 },
//   { key: 'number_hamel', label: 'شماره حامل', group: 'haml', kind: 'plate', width: 180 },
//   { key: 'container_type', label: 'نوع کانتینر', group: 'haml', kind: 'containerType', width: 130 },
//   { key: 'container_number', label: 'شماره کانتینر', group: 'haml', kind: 'containerNumber', width: 140 },
// ]

// const LABELS = Object.fromEntries(COLUMNS.map((c) => [c.key, c.label])) as Record<FieldKey, string>
// const isCopyable = (k: FieldKey) => COPYABLE_FIELDS.includes(k)
// const isNeverCopy = (k: FieldKey) => NEVER_COPY_FIELDS.includes(k)

// /** DetailRow (server shape) -> LineForm (all-strings edit shape). */
// function toForm(row: DetailRow): LineForm {
//   return {
//     id_anbar: row.id_anbar,
//     id_tagh_anbar: row.id_tagh_anbar,
//     code_groupe_kala: String(row.code_groupe_kala ?? ''),
//     description_kala: row.description_kala ?? '',
//     hscode: row.hscode ?? '',
//     type_bastem: row.type_bastem ?? '',
//     number_kala: String(row.number_kala ?? ''),
//     number_pallet: row.number_pallet == null ? '' : String(row.number_pallet),
//     value_kala: row.value_kala == null ? '' : String(row.value_kala),
//     customs_value: row.customs_value == null ? '' : String(row.customs_value),
//     insured_value: row.insured_value == null ? '' : String(row.insured_value),
//     insurance_expiry_date: isoToJalaliInput(row.insurance_expiry_date),
//     weighte: String(row.weighte ?? ''),
//     number_ghabze_bskol: row.number_ghabze_bskol == null ? '' : String(row.number_ghabze_bskol),
//     weighte_baskol: String(row.weighte_baskol ?? ''),
//     type_number_kantiner: row.type_number_kantiner ?? '',
//     number_hamel: row.number_hamel ?? '',
//     zarib_mahal: row.zarib_mahal == null ? '' : String(row.zarib_mahal),
//     container_type: row.container_type ?? '',
//     container_number: row.container_number ?? '',
//   }
// }

// type Props = {
//   /** FA_HEADERS_TALI.ID_TALI — undefined while the header query is still resolving */
//   tallyId: number | undefined
// }

// export function TallyGoodsGrid({ tallyId }: Props) {
//   const qc = useQueryClient()

//   const {
//     data: lines,
//     isLoading,
//     isError,
//   } = useQuery({
//     queryKey: ['tally-details', tallyId],
//     queryFn: () => apiGet<DetailRow[]>(`/tally/${tallyId}/details`),
//     enabled: tallyId != null,
//   })

//   // Same query key StorageGroupSelect uses, so this rides its cache instead of refetching.
//   // Lets a saved row show «۱۰۲ — محصولات فولادی» rather than a bare group id.
//   const { data: groups } = useQuery({
//     queryKey: ['storage-groups'],
//     queryFn: () => apiGet<StorageGroup[]>('/commodity/storage-groups'),
//     staleTime: 5 * 60 * 1000,
//   })
//   const groupLabel = useMemo(() => {
//     const byId = new Map<number, string>()
//     for (const g of groups ?? []) {
//       const name = (g.name ?? '').trim()
//       byId.set(g.id, name ? `${g.code ?? g.id} — ${name}` : String(g.code ?? g.id))
//     }
//     return (id: number | string | null) => {
//       if (isBlank(id)) return '—'
//       return byId.get(Number(id)) ?? String(id)
//     }
//   }, [groups])

//   // ── draft state ───────────────────────────────────────────────────────────────────
//   // draft != null means one row is being entered or edited. editingId tells which.
//   const [draft, setDraft] = useState<LineForm | null>(null)
//   const [editingId, setEditingId] = useState<number | null>(null)
//   const [picked, setPicked] = useState<Commodity | null>(null)
//   /** copied but not yet reviewed — these render amber and block a silent save */
//   const [copied, setCopied] = useState<Set<FieldKey>>(new Set())
//   const [focusedKey, setFocusedKey] = useState<FieldKey | null>(null)
//   /** which popover-backed cell is open — controlled so it survives dropdown clicks */
//   const [openCell, setOpenCell] = useState<'commodity' | 'plate' | null>(null)
//   const [confirmOpen, setConfirmOpen] = useState(false)
//   const [keepGoing, setKeepGoing] = useState(true)
//   const draftRowRef = useRef<HTMLTableRowElement | null>(null)

//   const rows = lines ?? []
//   const editingIndex = editingId == null ? -1 : rows.findIndex((r) => r.id_tali_details === editingId)
//   /** the row the ⬆ buttons copy from: the one physically above the draft */
//   const sourceRow: DetailRow | null =
//     draft == null ? null
//       : editingId == null ? (rows.length > 0 ? rows[rows.length - 1] : null)
//         : (editingIndex > 0 ? rows[editingIndex - 1] : null)
//   const sourceForm = sourceRow == null ? null : toForm(sourceRow)
//   const sourceRowNumber = sourceRow == null ? null
//     : (editingId == null ? rows.length : editingIndex)

//   function setField(key: FieldKey, value: string | number | null) {
//     setDraft((d) => (d == null ? d : { ...d, [key]: value } as LineForm))
//     // a manual edit means the operator has looked at it — drop the amber flag
//     setCopied((prev) => {
//       if (!prev.has(key)) return prev
//       const next = new Set(prev)
//       next.delete(key)
//       return next
//     })
//   }

//   function markReviewed(key: FieldKey) {
//     setCopied((prev) => {
//       if (!prev.has(key)) return prev
//       const next = new Set(prev)
//       next.delete(key)
//       return next
//     })
//   }

//   function copyCell(key: FieldKey) {
//     if (sourceForm == null || !isCopyable(key)) return
//     const value = sourceForm[key]
//     setDraft((d) => (d == null ? d : { ...d, [key]: value } as LineForm))
//     setCopied((prev) => new Set(prev).add(key))
//   }

//   function copyRow() {
//     if (sourceForm == null || draft == null) return
//     const filled = COPYABLE_FIELDS.filter(
//       (key) => !isBlank(sourceForm[key] as string | number | null),
//     )
//     const next = { ...draft }
//     for (const key of filled) (next as Record<string, unknown>)[key] = sourceForm[key]
//     setDraft(next)
//     setCopied((prev) => {
//       const merged = new Set(prev)
//       for (const key of filled) merged.add(key)
//       return merged
//     })
//   }

//   function startAdd() {
//     setEditingId(null)
//     setPicked(null)
//     setCopied(new Set())
//     setDraft({ ...EMPTY_LINE })
//   }

//   function startEdit(row: DetailRow) {
//     setEditingId(row.id_tali_details)
//     setPicked(null)
//     setCopied(new Set())
//     setDraft(toForm(row))
//   }

//   function cancelDraft() {
//     setOpenCell(null)
//     setDraft(null)
//     setEditingId(null)
//     setPicked(null)
//     setCopied(new Set())
//     setFocusedKey(null)
//   }

//   // focus the first cell whenever a draft row opens, so entry starts on the keyboard
//   useEffect(() => {
//     if (draft == null) return
//     const id = window.requestAnimationFrame(() => {
//       draftRowRef.current?.querySelector<HTMLElement>('input,button[data-cell-open]')?.focus()
//     })
//     return () => window.cancelAnimationFrame(id)
//     // eslint-disable-next-line react-hooks/exhaustive-deps
//   }, [draft != null, editingId])

//   function onPickCommodity(c: Commodity | null) {
//     setPicked(c)
//     if (!c) return
//     setDraft((d) => (d == null ? d : {
//       ...d,
//       description_kala: c.description_fa ?? '',
//       hscode: c.hs_code ?? '',
//     }))
//     markReviewed('description_kala')
//     markReviewed('hscode')
//   }

//   /** non-blocking: the same truck can legitimately carry two commodities */
//   const duplicates = useMemo(() => {
//     if (draft == null) return [] as { key: FieldKey; rowNumber: number }[]
//     const found: { key: FieldKey; rowNumber: number }[] = []
//     for (const key of UNIQUE_FIELDS) {
//       const value = String(draft[key] ?? '').trim()
//       if (value === '') continue
//       const hit = rows.findIndex(
//         (r) =>
//           r.id_tali_details !== editingId &&
//           String(toForm(r)[key] ?? '').trim() === value,
//       )
//       if (hit >= 0) found.push({ key, rowNumber: hit + 1 })
//     }
//     return found
//   }, [draft, rows, editingId])

//   const insuranceDateInvalid = draft != null
//     && parseFlexibleJalaliDate(draft.insurance_expiry_date).status === 'invalid'

//   // ── persistence ───────────────────────────────────────────────────────────────────

//   function toPayload(f: LineForm) {
//     if (tallyId == null) throw new Error('شناسه داخلی تالی بارگذاری نشده است.')
//     const intOrNull = (v: string) => {
//       const n = normalizeIntegerInput(v)
//       return n === '' ? null : Number(n)
//     }
//     const decimalOrNull = (v: string) => {
//       const n = normalizeDecimalInput(v)
//       return n === '' ? null : n
//     }
//     const strOrNull = (v: string) => (v.trim() === '' ? null : v)
//     return {
//       id_headers_tali: tallyId,
//       id_anbar: f.id_anbar,
//       id_tagh_anbar: f.id_tagh_anbar,
//       code_groupe_kala: intOrNull(f.code_groupe_kala),
//       description_kala: strOrNull(f.description_kala),
//       hscode: strOrNull(f.hscode),
//       type_bastem: strOrNull(f.type_bastem),
//       number_kala: intOrNull(f.number_kala),
//       number_pallet: intOrNull(f.number_pallet),
//       value_kala: decimalOrNull(f.value_kala),
//       customs_value: decimalOrNull(f.customs_value),
//       insured_value: decimalOrNull(f.insured_value),
//       insurance_expiry_date: parseFlexibleJalaliDate(f.insurance_expiry_date).iso,
//       weighte: decimalOrNull(f.weighte),
//       number_ghabze_bskol: intOrNull(f.number_ghabze_bskol),
//       weighte_baskol: decimalOrNull(f.weighte_baskol),
//       type_number_kantiner: strOrNull(f.type_number_kantiner),
//       number_hamel: strOrNull(f.number_hamel),
//       zarib_mahal: strOrNull(f.zarib_mahal),
//       container_type: strOrNull(f.container_type),
//       container_number: strOrNull(f.container_number),
//     }
//   }

//   const saveMutation = useMutation({
//     mutationFn: (f: LineForm) =>
//       editingId == null
//         ? apiSend('/tally-details', 'POST', toPayload(f))
//         : apiSend(`/tally-details/${editingId}`, 'PUT', toPayload(f)),
//     // The confirmation dialog is only a review step. Close it as soon as the request
//     // starts; if saving fails, the draft and amber copied-cell markers stay in place so
//     // the operator can correct/retry without losing anything.
//     onMutate: () => {
//       setConfirmOpen(false)
//     },
//     onSuccess: () => {
//       qc.invalidateQueries({ queryKey: ['tally-details', tallyId] })
//       // chained entry: after saving a NEW row, drop straight into the next empty one
//       if (editingId == null && keepGoing) {
//         setPicked(null)
//         setCopied(new Set())
//         setDraft({ ...EMPTY_LINE })
//       } else {
//         cancelDraft()
//       }
//     },
//     onError: () => {
//       qc.invalidateQueries({ queryKey: ['tally-details', tallyId] })
//     },
//   })

//   const deleteMutation = useMutation({
//     mutationFn: (lineId: number) => apiSend(`/tally-details/${lineId}`, 'DELETE'),
//     onSuccess: () => qc.invalidateQueries({ queryKey: ['tally-details', tallyId] }),
//     onError: (e) => alert(`حذف ناموفق بود: ${(e as Error).message}`),
//   })

//   /**
//    * The customer's actual requirement lives here: a row is never saved with an
//    * unreviewed copied value without the operator seeing that value one more time.
//    */
//   function requestSave(next: boolean) {
//     if (draft == null) return
//     if (parseFlexibleJalaliDate(draft.insurance_expiry_date).status === 'invalid') {
//       setFocusedKey('insurance_expiry_date')
//       return
//     }
//     setKeepGoing(next)
//     if (copied.size > 0) {
//       setConfirmOpen(true)
//       return
//     }
//     saveMutation.mutate(draft)
//   }

//   function onDraftKeyDown(e: React.KeyboardEvent) {
//     if (e.ctrlKey && !e.shiftKey && (e.key === 'd' || e.key === 'D')) {
//       e.preventDefault()
//       if (focusedKey) copyCell(focusedKey)
//       return
//     }
//     if (e.altKey && (e.key === 'c' || e.key === 'C')) {
//       e.preventDefault()
//       copyRow()
//       return
//     }
//     if (e.ctrlKey && e.key === 'Enter') {
//       e.preventDefault()
//       requestSave(true)
//       return
//     }
//     if (e.key === 'Escape') {
//       e.preventDefault()
//       cancelDraft()
//     }
//   }

//   // ── cell rendering ────────────────────────────────────────────────────────────────

//   function readCell(col: ColumnDef, row: DetailRow): string {
//     switch (col.kind) {
//       case 'commodity': return groupLabel(row.code_groupe_kala)
//       case 'anbar': return dash(row.anbar_name)
//       case 'tagh': return dash(row.tagh_name)
//       case 'plate': return formatPlate(row.number_hamel)
//       case 'decimal': return formatAmount(row[col.key as 'weighte'] as number | string | null)
//       case 'date': return isoToJalaliInput(row.insurance_expiry_date) || '—'
//       default: return dash((row as unknown as Record<string, unknown>)[col.key])
//     }
//   }

//   function editCell(col: ColumnDef, f: LineForm): React.ReactNode {
//     const common = { size: 'xs' as const, variant: 'unstyled' as const }
//     switch (col.kind) {
//       case 'commodity':
//         return (
//           <Popover
//             width={430} position="bottom-start" withArrow shadow="md" trapFocus
//             opened={openCell === 'commodity'}
//             onChange={(o) => setOpenCell(o ? 'commodity' : null)}
//           >
//             <Popover.Target>
//               <button
//                 type="button" className="tgg-cell-button" data-cell-open
//                 onClick={() => setOpenCell((c) => (c === 'commodity' ? null : 'commodity'))}
//               >
//                 {isBlank(f.code_groupe_kala) ? 'انتخاب کالا…' : groupLabel(f.code_groupe_kala)}
//               </button>
//             </Popover.Target>
//             <Popover.Dropdown>
//               <Stack gap="sm">
//                 <CommodityPicker
//                   picked={picked}
//                   onPick={onPickCommodity}
//                   groupValue={isBlank(f.code_groupe_kala) ? null : Number(f.code_groupe_kala)}
//                   onGroupChange={(v) => setField('code_groupe_kala', v == null ? '' : String(v))}
//                   comboboxProps={{ withinPortal: false }}
//                 />
//                 <Group gap="xs" justify="flex-start">
//                   <Button size="xs" onClick={() => setOpenCell(null)}>تأیید</Button>
//                   {isBlank(f.code_groupe_kala) && (
//                     <Text size="xs" c="dimmed">گروه قیمت انتخاب نشده؛ در صورت نیاز انتخاب کنید.</Text>
//                   )}
//                 </Group>
//               </Stack>
//             </Popover.Dropdown>
//           </Popover>
//         )
//       case 'term':
//         return (
//           <TermValueSelect
//             {...common}
//             categoryId={3}
//             placeholder="—"
//             value={f.type_bastem || null}
//             onChange={(v) => setField('type_bastem', v ?? '')}
//           />
//         )
//       case 'anbar':
//         return (
//           <RefSelect
//             {...common}
//             path="/anbar" valueKey="id_anbar" labelKey="name_anbar" placeholder="—"
//             value={f.id_anbar}
//             onChange={(v) => setField('id_anbar', v)}
//           />
//         )
//       case 'tagh':
//         return (
//           <RefSelect
//             {...common}
//             path="/tagh" valueKey="id_tagh" labelKey="name_tagh" placeholder="—"
//             value={f.id_tagh_anbar}
//             onChange={(v) => setField('id_tagh_anbar', v)}
//           />
//         )
//       case 'zarib':
//         return (
//           <Select
//             {...common}
//             data={ZARIB_OPTIONS} clearable placeholder="—"
//             value={f.zarib_mahal || null}
//             onChange={(v) => setField('zarib_mahal', v ?? '')}
//           />
//         )
//       case 'containerType':
//         return (
//           <Select
//             {...common}
//             data={CONTAINER_TYPES} clearable placeholder="—"
//             value={f.container_type || null}
//             onChange={(v) => {
//               const next = v ?? ''
//               setField('container_type', next)
//               if (!TYPES_WITH_NUMBER.includes(next)) setField('container_number', '')
//             }}
//           />
//         )
//       case 'containerNumber': {
//         const enabled = TYPES_WITH_NUMBER.includes(f.container_type)
//         return (
//           <TextInput
//             {...common}
//             dir="ltr"
//             disabled={!enabled}
//             placeholder={enabled ? 'MSKU1234567' : '—'}
//             value={f.container_number}
//             onChange={(e) => setField('container_number', e.currentTarget.value.replace(/[^A-Za-z0-9]/g, ''))}
//           />
//         )
//       }
//       case 'plate':
//         return (
//           <Popover
//             width={540} position="bottom-end" withArrow shadow="md" trapFocus
//             opened={openCell === 'plate'}
//             onChange={(o) => setOpenCell(o ? 'plate' : null)}
//           >
//             <Popover.Target>
//               <button
//                 type="button" className="tgg-cell-button" data-cell-open
//                 onClick={() => setOpenCell((c) => (c === 'plate' ? null : 'plate'))}
//               >
//                 {isBlank(f.number_hamel) ? 'ثبت پلاک…' : formatPlate(f.number_hamel)}
//               </button>
//             </Popover.Target>
//             <Popover.Dropdown>
//               <Stack gap="sm">
//                 <PlateInput
//                   label="شماره حامل"
//                   value={f.number_hamel}
//                   onChange={(v) => setField('number_hamel', v)}
//                   comboboxProps={{ withinPortal: false }}
//                 />
//                 <Button size="xs" onClick={() => setOpenCell(null)}>تأیید</Button>
//               </Stack>
//             </Popover.Dropdown>
//           </Popover>
//         )
//       case 'int':
//         return (
//           <TextInput
//             {...common}
//             inputMode="numeric" placeholder="—"
//             value={f[col.key] as string}
//             onChange={(e) => setField(col.key, normalizeIntegerInput(e.currentTarget.value))}
//           />
//         )
//       case 'decimal':
//         return (
//           <TextInput
//             {...common}
//             inputMode="decimal" placeholder="—"
//             value={f[col.key] as string}
//             onChange={(e) => setField(col.key, normalizeDecimalInput(e.currentTarget.value))}
//           />
//         )
//       case 'date': {
//         return (
//           <TextInput
//             {...common}
//             dir="ltr"
//             inputMode="numeric"
//             placeholder="۱۴۰۵/۰۶/۱۲ یا ۱۲/۰۶/۱۴۰۵"
//             value={f.insurance_expiry_date}
//             error={insuranceDateInvalid}
//             aria-label="تاریخ اتمام بیمه"
//             onChange={(e) => setField(
//               'insurance_expiry_date',
//               normalizeFlexibleJalaliInput(e.currentTarget.value),
//             )}
//           />
//         )
//       }
//       default:
//         return (
//           <TextInput
//             {...common}
//             placeholder="—"
//             value={f[col.key] as string}
//             onChange={(e) => setField(col.key, e.currentTarget.value)}
//           />
//         )
//     }
//   }

//   /**
//    * Deliberately a plain function, not a <DraftCell/> component: declaring a component
//    * inside the render body gives React a new component type on every render, which
//    * remounts the cell and drops focus after each keystroke.
//    */
//   function renderDraftCell(col: ColumnDef, f: LineForm): React.ReactNode {
//     const amber = copied.has(col.key)
//     const duplicate = duplicates.some((d) => d.key === col.key)
//     const canCopy = sourceForm != null && isCopyable(col.key) && !isBlank(sourceForm[col.key] as string | number | null)
//     return (
//       <Table.Td
//         key={col.key}
//         className={[
//           'tgg-draft-cell',
//           amber ? 'tgg-cell-copied' : '',
//           duplicate ? 'tgg-cell-duplicate' : '',
//           isNeverCopy(col.key) ? 'tgg-cell-manual' : '',
//         ].filter(Boolean).join(' ')}
//         onFocusCapture={() => setFocusedKey(col.key)}
//       >
//         <div className="tgg-cell-inner">
//           <div className="tgg-cell-control">{editCell(col, f)}</div>
//           {amber ? (
//             <Tooltip label="بررسی شد" withArrow>
//               <ActionIcon
//                 size="xs" variant="subtle" color="yellow" tabIndex={-1}
//                 aria-label={`تأیید ${col.label}`}
//                 onClick={() => markReviewed(col.key)}
//               >
//                 <Check size={13} />
//               </ActionIcon>
//             </Tooltip>
//           ) : canCopy ? (
//             <Tooltip label={`کپی «${String(sourceForm?.[col.key])}» از ردیف ${sourceRowNumber}`} withArrow>
//               <ActionIcon
//                 className="tgg-copy-icon"
//                 size="xs" variant="subtle" color="gray" tabIndex={-1}
//                 aria-label={`کپی ${col.label} از ردیف بالا`}
//                 onClick={() => copyCell(col.key)}
//               >
//                 <ArrowUp size={13} />
//               </ActionIcon>
//             </Tooltip>
//           ) : null}
//         </div>
//       </Table.Td>
//     )
//   }

//   // ── render ────────────────────────────────────────────────────────────────────────

//   // table-layout is fixed, so this is the real width, not a floor
//   const tableWidth = COLUMNS.reduce((sum, c) => sum + c.width, 0) + 44 + 96

//   return (
//     <Paper className="tally-detail-section tally-detail-goods-section" radius="xl">
//       <div className="tally-detail-section-header">
//         <div className="tally-detail-section-heading">
//           <span className="tally-detail-section-icon" aria-hidden>
//             <PackageOpen size={23} strokeWidth={1.8} />
//           </span>
//           <div>
//             <Title order={3}>ردیف‌های کالا</Title>
//             <Text>اطلاعات کالا، باسکول، محل نگهداری و حامل</Text>
//           </div>
//         </div>
//         <Button
//           className="tally-detail-add-button"
//           leftSection={<Plus size={18} />}
//           onClick={startAdd}
//           disabled={tallyId == null || draft != null}
//         >
//           افزودن ردیف
//         </Button>
//       </div>
//       <div className="tally-detail-section-rule" />

//       {isLoading && (
//         <Center className="tally-detail-state">
//           <Loader size="sm" />
//           <Text>در حال بارگذاری ردیف‌ها...</Text>
//         </Center>
//       )}
//       {isError && (
//         <Center className="tally-detail-state tally-detail-state-error">
//           <Text>خطا در بارگذاری ردیف‌ها.</Text>
//         </Center>
//       )}

//       {rows.length === 0 && draft == null && !isLoading && (
//         <Center className="tally-detail-empty-state">
//           <PackageOpen size={28} strokeWidth={1.6} aria-hidden />
//           <Text fw={700}>هنوز ردیف کالایی ثبت نشده است.</Text>
//           <Text size="sm">برای شروع، گزینه «افزودن ردیف» را انتخاب کنید.</Text>
//         </Center>
//       )}

//       {(rows.length > 0 || draft != null) && (
//         <div className="tgg-shell">
//           <div className="tgg-scroll">
//             <Table className="tgg-table" style={{ width: tableWidth }}>
//               <colgroup>
//                 <col style={{ width: 44 }} />
//                 {COLUMNS.map((c) => <col key={c.key} style={{ width: c.width }} />)}
//                 <col style={{ width: 96 }} />
//               </colgroup>
//               <Table.Thead>
//                 <Table.Tr className="tgg-group-row">
//                   <Table.Th className="tgg-sticky-num" />
//                   {GROUPS.map((g) => {
//                     const span = COLUMNS.filter((c) => c.group === g.key).length
//                     return (
//                       <Table.Th key={g.key} colSpan={span} className={`tgg-group tgg-group-${g.key}`}>
//                         {g.label}
//                       </Table.Th>
//                     )
//                   })}
//                   <Table.Th className="tgg-sticky-actions" />
//                 </Table.Tr>
//                 <Table.Tr>
//                   <Table.Th className="tgg-sticky-num">#</Table.Th>
//                   {COLUMNS.map((c) => (
//                     <Table.Th key={c.key} title={c.label}>
//                       {c.label}
//                     </Table.Th>
//                   ))}
//                   <Table.Th className="tgg-sticky-actions">عملیات</Table.Th>
//                 </Table.Tr>
//               </Table.Thead>

//               <Table.Tbody>
//                 {rows.map((row, i) => (
//                   draft != null && editingId === row.id_tali_details ? (
//                     <Table.Tr
//                       key={row.id_tali_details}
//                       ref={draftRowRef}
//                       className="tgg-draft-row"
//                       onKeyDown={onDraftKeyDown}
//                     >
//                       <Table.Td className="tgg-sticky-num">{i + 1}</Table.Td>
//                       {COLUMNS.map((c) => renderDraftCell(c, draft))}
//                       <Table.Td className="tgg-sticky-actions">
//                         <Text size="xs" c="dimmed">در حال ویرایش</Text>
//                       </Table.Td>
//                     </Table.Tr>
//                   ) : (
//                     <Table.Tr key={row.id_tali_details}>
//                       <Table.Td className="tgg-sticky-num">{i + 1}</Table.Td>
//                       {COLUMNS.map((c) => {
//                         const text = readCell(c, row)
//                         return (
//                           <Table.Td
//                             key={c.key}
//                             title={text}
//                             className={c.key === 'description_kala' ? 'tgg-primary-cell' : undefined}
//                           >
//                             {text}
//                           </Table.Td>
//                         )
//                       })}
//                       <Table.Td className="tgg-sticky-actions">
//                         <Group gap={4} justify="center" wrap="nowrap">
//                           <Tooltip label="ویرایش" withArrow>
//                             <ActionIcon
//                               className="tally-detail-row-action"
//                               variant="light" color="blue" radius="md" aria-label="ویرایش"
//                               disabled={draft != null}
//                               onClick={() => startEdit(row)}
//                             >
//                               <IconEdit size={18} />
//                             </ActionIcon>
//                           </Tooltip>
//                           <Tooltip label="حذف" withArrow>
//                             <ActionIcon
//                               className="tally-detail-row-action"
//                               variant="light" color="red" radius="md" aria-label="حذف"
//                               disabled={draft != null}
//                               onClick={() => confirm('حذف این ردیف؟') && deleteMutation.mutate(row.id_tali_details)}
//                             >
//                               <IconTrash size={18} />
//                             </ActionIcon>
//                           </Tooltip>
//                         </Group>
//                       </Table.Td>
//                     </Table.Tr>
//                   )
//                 ))}

//                 {draft != null && editingId == null && (
//                   <Table.Tr ref={draftRowRef} className="tgg-draft-row" onKeyDown={onDraftKeyDown}>
//                     <Table.Td className="tgg-sticky-num">{rows.length + 1}</Table.Td>
//                     {COLUMNS.map((c) => renderDraftCell(c, draft))}
//                     <Table.Td className="tgg-sticky-actions">
//                       <Text size="xs" c="dimmed">ردیف جدید</Text>
//                     </Table.Td>
//                   </Table.Tr>
//                 )}
//               </Table.Tbody>
//             </Table>
//           </div>

//           {draft != null && (
//             <div className="tgg-actionbar">
//               <Group gap="sm" wrap="wrap">
//                 <Button
//                   size="xs" variant="light"
//                   leftSection={<ArrowUp size={15} />}
//                   onClick={copyRow}
//                   disabled={sourceForm == null}
//                 >
//                   کپی از ردیف بالا
//                 </Button>
//                 <Button
//                   size="xs"
//                   className="tally-detail-save-button"
//                   loading={saveMutation.isPending}
//                   onClick={() => requestSave(true)}
//                 >
//                   {editingId == null ? 'ذخیره و ردیف بعدی' : 'ذخیره تغییرات'}
//                 </Button>
//                 {editingId == null && (
//                   <Button
//                     size="xs" variant="default"
//                     loading={saveMutation.isPending}
//                     onClick={() => requestSave(false)}
//                   >
//                     ذخیره و بستن
//                   </Button>
//                 )}
//                 <Button size="xs" variant="subtle" color="gray" leftSection={<X size={15} />} onClick={cancelDraft}>
//                   انصراف
//                 </Button>
//                 <Text size="xs" c="dimmed" className="tgg-shortcuts">
//                   Ctrl+D کپی سلول · Alt+C کپی ردیف · Ctrl+Enter ذخیره · Esc انصراف
//                 </Text>
//               </Group>
//             </div>
//           )}

//           {draft != null && copied.size > 0 && (
//             <div className="tgg-banner tgg-banner-warn">
//               <AlertTriangle size={16} aria-hidden />
//               <span>
//                 {copied.size} فیلد از ردیف {sourceRowNumber} کپی شده و هنوز بررسی نشده:{' '}
//                 {[...copied].map((k) => LABELS[k]).join('، ')}
//               </span>
//               <Button size="compact-xs" variant="subtle" color="yellow" onClick={() => setCopied(new Set())}>
//                 همه بررسی شد
//               </Button>
//             </div>
//           )}

//           {draft != null && duplicates.length > 0 && (
//             <div className="tgg-banner tgg-banner-dup">
//               <AlertTriangle size={16} aria-hidden />
//               <span>
//                 {duplicates.map((d) => `«${LABELS[d.key]}» قبلاً در ردیف ${d.rowNumber} ثبت شده`).join(' · ')}
//               </span>
//             </div>
//           )}

//           {insuranceDateInvalid && (
//             <div className="tgg-banner tgg-banner-error">
//               <AlertTriangle size={16} aria-hidden />
//               <span>
//                 تاریخ اتمام بیمه نامعتبر است؛ تاریخ شمسی را به‌شکل «۱۴۰۵/۰۶/۱۲» یا
//                 «۱۲/۰۶/۱۴۰۵» وارد کنید.
//               </span>
//             </div>
//           )}

//           {saveMutation.isError && (
//             <div className="tgg-banner tgg-banner-error">
//               <span>ذخیره انجام نشد: {(saveMutation.error as Error).message}</span>
//             </div>
//           )}
//         </div>
//       )}

//       <Modal
//         opened={confirmOpen}
//         onClose={() => setConfirmOpen(false)}
//         title="تأیید مقادیر کپی‌شده"
//         radius="lg"
//         size="md"
//         dir="rtl"
//       >
//         <Stack gap="sm">
//           <Text size="sm">
//             این مقادیر از ردیف {sourceRowNumber} کپی شده‌اند و هنوز بررسی نشده‌اند. قبل از ذخیره یک بار
//             کنترلشان کنید:
//           </Text>
//           <Table withTableBorder withRowBorders className="tgg-confirm-table">
//             <Table.Tbody>
//               {[...copied].map((k) => (
//                 <Table.Tr key={k}>
//                   <Table.Td className="tgg-confirm-label">{LABELS[k]}</Table.Td>
//                   <Table.Td>
//                     {k === 'code_groupe_kala'
//                       ? groupLabel(draft?.code_groupe_kala ?? null)
//                       : dash(draft?.[k] as string | null)}
//                   </Table.Td>
//                 </Table.Tr>
//               ))}
//             </Table.Tbody>
//           </Table>
//           <Group gap="sm">
//             <Button
//               loading={saveMutation.isPending}
//               onClick={() => draft != null && saveMutation.mutate(draft)}
//             >
//               تأیید و ذخیره
//             </Button>
//             <Button variant="default" onClick={() => setConfirmOpen(false)}>
//               بازگشت و بررسی
//             </Button>
//           </Group>
//         </Stack>
//       </Modal>
//     </Paper>
//   )
// }


import { useEffect, useMemo, useRef, useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import {
  ActionIcon, Button, Center, Group, Loader, Modal, Paper, Popover,
  Select, Stack, Table, Text, TextInput, Title, Tooltip,
} from '@mantine/core'
import { AlertTriangle, ArrowUp, Check, PackageOpen, Plus, X } from 'lucide-react'
import { IconEdit, IconTrash } from './icons'
import { apiGet, apiSend } from '../api/client'
import { RefSelect } from './RefSelect'
import { TermValueSelect } from './TermValueSelect'
import { CommodityPicker, type Commodity } from './CommodityPicker'
import { PlateInput } from './PlateInput'
import { CONTAINER_TYPES, TYPES_WITH_NUMBER } from './ContainerFields'
import type { StorageGroup } from './StorageGroupSelect'
import {
  isoToJalaliInput,
  normalizeFlexibleJalaliInput,
  parseFlexibleJalaliDate,
} from '../utils/flexibleJalaliDate'
import './TallyGoodsGrid.css'

/**
 * TallyGoodsGrid — the tally's goods lines (ردیف‌های کالا) as ONE in-place editable grid.
 *
 * Replaces the old "افزودن ردیف → modal" flow. Operators enter the same commodity across
 * several containers, so every row repeats except the weights / weighbridge ticket /
 * carrier plate / container number. The modal hid the previous row exactly when they
 * needed to read it, so they were retyping from memory.
 *
 * The design constraint from the customer was explicit: copying is fine, INVISIBLE copying
 * is not ("ممکن این وسط یه چیزی عوض شده باشه و متوجه نشیم"). So:
 *   - the draft row is a real row at the bottom of the same table — the row above stays
 *     on screen, column-aligned, which is what makes visual comparison possible;
 *   - nothing is ever copied automatically. The operator copies, per cell (⬆ / Ctrl+D)
 *     or per row (Alt+C), and only the fields in COPYABLE_FIELDS;
 *   - anything filled by copy is tinted amber and STAYS amber until reviewed, and save
 *     asks for confirmation while any amber cell is left;
 *   - fields that usually differ (NEVER_COPY_FIELDS) are never touched by copy and are
 *     warned about if they duplicate another row. They remain optional.
 *
 * Save uses the generic CRUD endpoints (POST/PUT/DELETE /tally-details).
 */

export type DetailRow = {
  id_tali_details: number
  id_headers_tali: number
  id_anbar: number | null
  anbar_name: string | null
  id_tagh_anbar: number | null
  tagh_name: string | null
  number_ghabze_anbar: number | null
  code_groupe_kala: number | null
  description_kala: string | null
  hscode: string | null
  type_bastem: string | null
  number_kala: number | null
  number_pallet: number | null
  value_kala: number | string | null
  customs_value: number | string | null
  insured_value: number | string | null
  insurance_expiry_date: string | null
  weighte: number | null
  type_number_kantiner: string | null
  number_ghabze_bskol: number | null
  weighte_baskol: number | null
  number_hamel: string | null
  zarib_mahal: string | null
  container_type: string | null
  container_number: string | null
}

export type LineForm = {
  id_anbar: number | null
  id_tagh_anbar: number | null
  code_groupe_kala: string
  description_kala: string
  hscode: string
  type_bastem: string
  number_kala: string
  number_pallet: string
  value_kala: string
  customs_value: string
  insured_value: string
  insurance_expiry_date: string
  weighte: string
  number_ghabze_bskol: string
  weighte_baskol: string
  type_number_kantiner: string
  number_hamel: string
  zarib_mahal: string
  container_type: string
  container_number: string
}

type FieldKey = keyof LineForm

const EMPTY_LINE: LineForm = {
  id_anbar: null, id_tagh_anbar: null, code_groupe_kala: '', description_kala: '',
  hscode: '', type_bastem: '', number_kala: '', number_pallet: '', value_kala: '',
  customs_value: '', insured_value: '', insurance_expiry_date: '', weighte: '',
  number_ghabze_bskol: '', weighte_baskol: '',
  type_number_kantiner: '', number_hamel: '', zarib_mahal: '',
  container_type: '', container_number: '',
}

/**
 * The two field sets that make the whole feature safe. Move a key between them and the
 * grid, the ⬆ buttons, the "کپی از بالا" button and the review warning all follow.
 *
 * number_kala / number_pallet / id_tagh_anbar sit in COPYABLE on purpose: in the
 * one-commodity-many-containers case they repeat. If the customer says otherwise, move
 * them down — nothing else needs to change.
 */
const COPYABLE_FIELDS: FieldKey[] = [
  'code_groupe_kala', 'description_kala', 'hscode', 'type_bastem',
  'number_kala', 'number_pallet', 'value_kala', 'customs_value', 'insured_value',
  'insurance_expiry_date',
  'id_anbar', 'id_tagh_anbar', 'zarib_mahal', 'container_type',
]

const NEVER_COPY_FIELDS: FieldKey[] = [
  'weighte', 'number_ghabze_bskol', 'weighte_baskol', 'number_hamel', 'container_number',
]

/** Repeating one of these inside a single tally is nearly always a copy-paste slip. */
const UNIQUE_FIELDS: FieldKey[] = ['number_ghabze_bskol', 'number_hamel', 'container_number']

const ZARIB_OPTIONS = [
  'انبارداری مسقف', 'انبارداری هانگار', 'انبارداری بارانداز', 'انبارداری محوطه',
]

// ── digit / value helpers (same semantics the modal used) ────────────────────────────

function normalizeDigits(s: string): string {
  return s
    .replace(/[\u06F0-\u06F9]/g, (d) => String(d.charCodeAt(0) - 0x06f0))
    .replace(/[\u0660-\u0669]/g, (d) => String(d.charCodeAt(0) - 0x0660))
}

function normalizeIntegerInput(s: string): string {
  return normalizeDigits(s).replace(/\D/g, '')
}

function normalizeDecimalInput(s: string): string {
  const normalized = normalizeDigits(s)
    .replace(/[,\u066C\s]/g, '')
    .replace(/\u066B/g, '.')
    .replace(/[^\d.]/g, '')
  const [whole, ...fractionParts] = normalized.split('.')
  return fractionParts.length === 0 ? whole : `${whole}.${fractionParts.join('')}`
}

function formatAmount(value: number | string | null): string {
  if (value == null || String(value).trim() === '') return '—'
  const amount = Number(normalizeDigits(String(value)))
  if (!Number.isFinite(amount)) return String(value)
  return amount.toLocaleString('en-US', { maximumFractionDigits: 2 })
}

const dash = (v: unknown) => (v == null || String(v).trim() === '' ? '—' : String(v))

/** "12-ط-345-67|TR-34" -> "۱۲ ط ۳۴۵ ایران ۶۷ · TR-34" for read-only cells. */
function formatPlate(value: string | null): string {
  if (!value || value.trim() === '') return '—'
  const [iranPart, foreignPart] = value.split('|')
  const parts = (iranPart ?? '').split('-')
  const iran = parts.length === 4 && parts.some(Boolean)
    ? `${parts[0]} ${parts[1]} ${parts[2]} ایران ${parts[3]}`
    : ''
  return [iran, foreignPart].filter((p) => p && p.trim() !== '').join(' · ') || '—'
}

const isBlank = (v: string | number | null) =>
  v == null || String(v).trim() === ''

// ── column model — one source of truth for header, cells and copy ────────────────────

type GroupKey = 'kala' | 'baskol' | 'mahal' | 'haml'

const GROUPS: { key: GroupKey; label: string }[] = [
  { key: 'kala', label: 'کالا' },
  { key: 'baskol', label: 'باسکول' },
  { key: 'mahal', label: 'محل نگهداری' },
  { key: 'haml', label: 'حمل و کانتینر' },
]

type CellKind =
  | 'commodity' | 'text' | 'term' | 'int' | 'decimal' | 'date'
  | 'anbar' | 'tagh' | 'zarib' | 'plate' | 'containerType' | 'containerNumber'

type ColumnDef = {
  key: FieldKey
  label: string
  group: GroupKey
  kind: CellKind
  width: number
}

const COLUMNS: ColumnDef[] = [
  { key: 'code_groupe_kala', label: 'کالا / گروه قیمت', group: 'kala', kind: 'commodity', width: 190 },
  { key: 'description_kala', label: 'شرح کالا', group: 'kala', kind: 'text', width: 240 },
  { key: 'hscode', label: 'HS Code', group: 'kala', kind: 'text', width: 110 },
  { key: 'type_bastem', label: 'نوع بسته‌بندی', group: 'kala', kind: 'term', width: 130 },
  { key: 'number_kala', label: 'تعداد', group: 'kala', kind: 'int', width: 80 },
  { key: 'number_pallet', label: 'تعداد پالت', group: 'kala', kind: 'int', width: 90 },
  { key: 'value_kala', label: 'ارزش کالا', group: 'kala', kind: 'decimal', width: 110 },
  { key: 'customs_value', label: 'ارزش کالای گمرکی', group: 'kala', kind: 'decimal', width: 140 },
  { key: 'insured_value', label: 'ارزش کالای بیمه‌شده', group: 'kala', kind: 'decimal', width: 150 },
  { key: 'insurance_expiry_date', label: 'تاریخ اتمام بیمه', group: 'kala', kind: 'date', width: 145 },
  { key: 'weighte', label: 'وزن اظهار', group: 'baskol', kind: 'decimal', width: 100 },
  { key: 'number_ghabze_bskol', label: 'شماره قبض باسکول', group: 'baskol', kind: 'int', width: 130 },
  { key: 'weighte_baskol', label: 'وزن باسکول', group: 'baskol', kind: 'decimal', width: 110 },
  { key: 'id_anbar', label: 'انبار', group: 'mahal', kind: 'anbar', width: 130 },
  { key: 'id_tagh_anbar', label: 'طاق', group: 'mahal', kind: 'tagh', width: 110 },
  { key: 'zarib_mahal', label: 'ضریب محل', group: 'mahal', kind: 'zarib', width: 150 },
  { key: 'number_hamel', label: 'شماره حامل', group: 'haml', kind: 'plate', width: 180 },
  { key: 'container_type', label: 'نوع کانتینر', group: 'haml', kind: 'containerType', width: 130 },
  { key: 'container_number', label: 'شماره کانتینر', group: 'haml', kind: 'containerNumber', width: 140 },
]

const LABELS = Object.fromEntries(COLUMNS.map((c) => [c.key, c.label])) as Record<FieldKey, string>
const isCopyable = (k: FieldKey) => COPYABLE_FIELDS.includes(k)
const isNeverCopy = (k: FieldKey) => NEVER_COPY_FIELDS.includes(k)

/** DetailRow (server shape) -> LineForm (all-strings edit shape). */
function toForm(row: DetailRow): LineForm {
  return {
    id_anbar: row.id_anbar,
    id_tagh_anbar: row.id_tagh_anbar,
    code_groupe_kala: String(row.code_groupe_kala ?? ''),
    description_kala: row.description_kala ?? '',
    hscode: row.hscode ?? '',
    type_bastem: row.type_bastem ?? '',
    number_kala: String(row.number_kala ?? ''),
    number_pallet: row.number_pallet == null ? '' : String(row.number_pallet),
    value_kala: row.value_kala == null ? '' : String(row.value_kala),
    customs_value: row.customs_value == null ? '' : String(row.customs_value),
    insured_value: row.insured_value == null ? '' : String(row.insured_value),
    insurance_expiry_date: isoToJalaliInput(row.insurance_expiry_date),
    weighte: String(row.weighte ?? ''),
    number_ghabze_bskol: row.number_ghabze_bskol == null ? '' : String(row.number_ghabze_bskol),
    weighte_baskol: String(row.weighte_baskol ?? ''),
    type_number_kantiner: row.type_number_kantiner ?? '',
    number_hamel: row.number_hamel ?? '',
    zarib_mahal: row.zarib_mahal == null ? '' : String(row.zarib_mahal),
    container_type: row.container_type ?? '',
    container_number: row.container_number ?? '',
  }
}

type Props = {
  /** FA_HEADERS_TALI.ID_TALI — undefined while the header query is still resolving */
  tallyId: number | undefined
}

export function TallyGoodsGrid({ tallyId }: Props) {
  const qc = useQueryClient()

  const {
    data: lines,
    isLoading,
    isError,
  } = useQuery({
    queryKey: ['tally-details', tallyId],
    queryFn: () => apiGet<DetailRow[]>(`/tally/${tallyId}/details`),
    enabled: tallyId != null,
  })

  // Same query key StorageGroupSelect uses, so this rides its cache instead of refetching.
  // Lets a saved row show «۱۰۲ — محصولات فولادی» rather than a bare group id.
  const { data: groups } = useQuery({
    queryKey: ['storage-groups'],
    queryFn: () => apiGet<StorageGroup[]>('/commodity/storage-groups'),
    staleTime: 5 * 60 * 1000,
  })
  const groupLabel = useMemo(() => {
    const byId = new Map<number, string>()
    for (const g of groups ?? []) {
      const name = (g.name ?? '').trim()
      byId.set(g.id, name ? `${g.code ?? g.id} — ${name}` : String(g.code ?? g.id))
    }
    return (id: number | string | null) => {
      if (isBlank(id)) return '—'
      return byId.get(Number(id)) ?? String(id)
    }
  }, [groups])

  // ── draft state ───────────────────────────────────────────────────────────────────
  // draft != null means one row is being entered or edited. editingId tells which.
  const [draft, setDraft] = useState<LineForm | null>(null)
  const [editingId, setEditingId] = useState<number | null>(null)
  const [picked, setPicked] = useState<Commodity | null>(null)
  /** copied but not yet reviewed — these render amber and block a silent save */
  const [copied, setCopied] = useState<Set<FieldKey>>(new Set())
  const [focusedKey, setFocusedKey] = useState<FieldKey | null>(null)
  /** which popover-backed cell is open — controlled so it survives dropdown clicks */
  const [openCell, setOpenCell] = useState<'commodity' | 'plate' | null>(null)
  const [confirmOpen, setConfirmOpen] = useState(false)
  const [keepGoing, setKeepGoing] = useState(true)
  const draftRowRef = useRef<HTMLTableRowElement | null>(null)

  const rows = lines ?? []
  const editingIndex = editingId == null ? -1 : rows.findIndex((r) => r.id_tali_details === editingId)
  /** the row the ⬆ buttons copy from: the one physically above the draft */
  const sourceRow: DetailRow | null =
    draft == null ? null
      : editingId == null ? (rows.length > 0 ? rows[rows.length - 1] : null)
        : (editingIndex > 0 ? rows[editingIndex - 1] : null)
  const sourceForm = sourceRow == null ? null : toForm(sourceRow)
  const sourceRowNumber = sourceRow == null ? null
    : (editingId == null ? rows.length : editingIndex)

  function setField(key: FieldKey, value: string | number | null) {
    setDraft((d) => (d == null ? d : { ...d, [key]: value } as LineForm))
    // a manual edit means the operator has looked at it — drop the amber flag
    setCopied((prev) => {
      if (!prev.has(key)) return prev
      const next = new Set(prev)
      next.delete(key)
      return next
    })
  }

  function markReviewed(key: FieldKey) {
    setCopied((prev) => {
      if (!prev.has(key)) return prev
      const next = new Set(prev)
      next.delete(key)
      return next
    })
  }

  function copyCell(key: FieldKey) {
    if (sourceForm == null || !isCopyable(key)) return
    const value = sourceForm[key]
    setDraft((d) => (d == null ? d : { ...d, [key]: value } as LineForm))
    setCopied((prev) => new Set(prev).add(key))
  }

  function copyRow() {
    if (sourceForm == null || draft == null) return
    const filled = COPYABLE_FIELDS.filter(
      (key) => !isBlank(sourceForm[key] as string | number | null),
    )
    const next = { ...draft }
    for (const key of filled) (next as Record<string, unknown>)[key] = sourceForm[key]
    setDraft(next)
    setCopied((prev) => {
      const merged = new Set(prev)
      for (const key of filled) merged.add(key)
      return merged
    })
  }

  function startAdd() {
    setEditingId(null)
    setPicked(null)
    setCopied(new Set())
    setDraft({ ...EMPTY_LINE })
  }

  function startEdit(row: DetailRow) {
    setEditingId(row.id_tali_details)
    setPicked(null)
    setCopied(new Set())
    setDraft(toForm(row))
  }

  function cancelDraft() {
    setOpenCell(null)
    setDraft(null)
    setEditingId(null)
    setPicked(null)
    setCopied(new Set())
    setFocusedKey(null)
  }

  // focus the first cell whenever a draft row opens, so entry starts on the keyboard
  useEffect(() => {
    if (draft == null) return
    const id = window.requestAnimationFrame(() => {
      draftRowRef.current?.querySelector<HTMLElement>('input,button[data-cell-open]')?.focus()
    })
    return () => window.cancelAnimationFrame(id)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [draft != null, editingId])

  function onPickCommodity(c: Commodity | null) {
    setPicked(c)
    if (!c) return
    setDraft((d) => (d == null ? d : {
      ...d,
      description_kala: c.description_fa ?? '',
      hscode: c.hs_code ?? '',
    }))
    markReviewed('description_kala')
    markReviewed('hscode')
  }

  /** non-blocking: the same truck can legitimately carry two commodities */
  const duplicates = useMemo(() => {
    if (draft == null) return [] as { key: FieldKey; rowNumber: number }[]
    const found: { key: FieldKey; rowNumber: number }[] = []
    for (const key of UNIQUE_FIELDS) {
      const value = String(draft[key] ?? '').trim()
      if (value === '') continue
      const hit = rows.findIndex(
        (r) =>
          r.id_tali_details !== editingId &&
          String(toForm(r)[key] ?? '').trim() === value,
      )
      if (hit >= 0) found.push({ key, rowNumber: hit + 1 })
    }
    return found
  }, [draft, rows, editingId])

  const insuranceDateInvalid = draft != null
    && parseFlexibleJalaliDate(draft.insurance_expiry_date).status === 'invalid'

  // ── persistence ───────────────────────────────────────────────────────────────────

  function toPayload(f: LineForm) {
    if (tallyId == null) throw new Error('شناسه داخلی تالی بارگذاری نشده است.')
    const intOrNull = (v: string) => {
      const n = normalizeIntegerInput(v)
      return n === '' ? null : Number(n)
    }
    const decimalOrNull = (v: string) => {
      const n = normalizeDecimalInput(v)
      return n === '' ? null : n
    }
    const strOrNull = (v: string) => (v.trim() === '' ? null : v)
    return {
      id_headers_tali: tallyId,
      id_anbar: f.id_anbar,
      id_tagh_anbar: f.id_tagh_anbar,
      code_groupe_kala: intOrNull(f.code_groupe_kala),
      description_kala: strOrNull(f.description_kala),
      hscode: strOrNull(f.hscode),
      type_bastem: strOrNull(f.type_bastem),
      number_kala: intOrNull(f.number_kala),
      number_pallet: intOrNull(f.number_pallet),
      value_kala: decimalOrNull(f.value_kala),
      customs_value: decimalOrNull(f.customs_value),
      insured_value: decimalOrNull(f.insured_value),
      insurance_expiry_date: parseFlexibleJalaliDate(f.insurance_expiry_date).iso,
      weighte: decimalOrNull(f.weighte),
      number_ghabze_bskol: intOrNull(f.number_ghabze_bskol),
      weighte_baskol: decimalOrNull(f.weighte_baskol),
      type_number_kantiner: strOrNull(f.type_number_kantiner),
      number_hamel: strOrNull(f.number_hamel),
      zarib_mahal: strOrNull(f.zarib_mahal),
      container_type: strOrNull(f.container_type),
      container_number: strOrNull(f.container_number),
    }
  }

  const saveMutation = useMutation({
    mutationFn: (f: LineForm) =>
      editingId == null
        ? apiSend('/tally-details', 'POST', toPayload(f))
        : apiSend(`/tally-details/${editingId}`, 'PUT', toPayload(f)),
    // The confirmation dialog is only a review step. Close it as soon as the request
    // starts; if saving fails, the draft and amber copied-cell markers stay in place so
    // the operator can correct/retry without losing anything.
    onMutate: () => {
      setConfirmOpen(false)
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['tally-details', tallyId] })
      qc.invalidateQueries({ queryKey: ['tally-insurance-check', tallyId] })
      // chained entry: after saving a NEW row, drop straight into the next empty one
      if (editingId == null && keepGoing) {
        setPicked(null)
        setCopied(new Set())
        setDraft({ ...EMPTY_LINE })
      } else {
        cancelDraft()
      }
    },
    onError: () => {
      qc.invalidateQueries({ queryKey: ['tally-details', tallyId] })
    },
  })

  const deleteMutation = useMutation({
    mutationFn: (lineId: number) => apiSend(`/tally-details/${lineId}`, 'DELETE'),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['tally-details', tallyId] })
      qc.invalidateQueries({ queryKey: ['tally-insurance-check', tallyId] })
    },
    onError: (e) => alert(`حذف ناموفق بود: ${(e as Error).message}`),
  })

  /**
   * The customer's actual requirement lives here: a row is never saved with an
   * unreviewed copied value without the operator seeing that value one more time.
   */
  function requestSave(next: boolean) {
    if (draft == null) return
    if (parseFlexibleJalaliDate(draft.insurance_expiry_date).status === 'invalid') {
      setFocusedKey('insurance_expiry_date')
      return
    }
    setKeepGoing(next)
    if (copied.size > 0) {
      setConfirmOpen(true)
      return
    }
    saveMutation.mutate(draft)
  }

  function onDraftKeyDown(e: React.KeyboardEvent) {
    if (e.ctrlKey && !e.shiftKey && (e.key === 'd' || e.key === 'D')) {
      e.preventDefault()
      if (focusedKey) copyCell(focusedKey)
      return
    }
    if (e.altKey && (e.key === 'c' || e.key === 'C')) {
      e.preventDefault()
      copyRow()
      return
    }
    if (e.ctrlKey && e.key === 'Enter') {
      e.preventDefault()
      requestSave(true)
      return
    }
    if (e.key === 'Escape') {
      e.preventDefault()
      cancelDraft()
    }
  }

  // ── cell rendering ────────────────────────────────────────────────────────────────

  function readCell(col: ColumnDef, row: DetailRow): string {
    switch (col.kind) {
      case 'commodity': return groupLabel(row.code_groupe_kala)
      case 'anbar': return dash(row.anbar_name)
      case 'tagh': return dash(row.tagh_name)
      case 'plate': return formatPlate(row.number_hamel)
      case 'decimal': return formatAmount(row[col.key as 'weighte'] as number | string | null)
      case 'date': return isoToJalaliInput(row.insurance_expiry_date) || '—'
      default: return dash((row as unknown as Record<string, unknown>)[col.key])
    }
  }

  function editCell(col: ColumnDef, f: LineForm): React.ReactNode {
    const common = { size: 'xs' as const, variant: 'unstyled' as const }
    switch (col.kind) {
      case 'commodity':
        return (
          <Popover
            width={430} position="bottom-start" withArrow shadow="md" trapFocus
            opened={openCell === 'commodity'}
            onChange={(o) => setOpenCell(o ? 'commodity' : null)}
          >
            <Popover.Target>
              <button
                type="button" className="tgg-cell-button" data-cell-open
                onClick={() => setOpenCell((c) => (c === 'commodity' ? null : 'commodity'))}
              >
                {isBlank(f.code_groupe_kala) ? 'انتخاب کالا…' : groupLabel(f.code_groupe_kala)}
              </button>
            </Popover.Target>
            <Popover.Dropdown>
              <Stack gap="sm">
                <CommodityPicker
                  picked={picked}
                  onPick={onPickCommodity}
                  groupValue={isBlank(f.code_groupe_kala) ? null : Number(f.code_groupe_kala)}
                  onGroupChange={(v) => setField('code_groupe_kala', v == null ? '' : String(v))}
                  comboboxProps={{ withinPortal: false }}
                />
                <Group gap="xs" justify="flex-start">
                  <Button size="xs" onClick={() => setOpenCell(null)}>تأیید</Button>
                  {isBlank(f.code_groupe_kala) && (
                    <Text size="xs" c="dimmed">گروه قیمت انتخاب نشده؛ در صورت نیاز انتخاب کنید.</Text>
                  )}
                </Group>
              </Stack>
            </Popover.Dropdown>
          </Popover>
        )
      case 'term':
        return (
          <TermValueSelect
            {...common}
            categoryId={3}
            placeholder="—"
            value={f.type_bastem || null}
            onChange={(v) => setField('type_bastem', v ?? '')}
          />
        )
      case 'anbar':
        return (
          <RefSelect
            {...common}
            path="/anbar" valueKey="id_anbar" labelKey="name_anbar" placeholder="—"
            value={f.id_anbar}
            onChange={(v) => setField('id_anbar', v)}
          />
        )
      case 'tagh':
        return (
          <RefSelect
            {...common}
            path="/tagh" valueKey="id_tagh" labelKey="name_tagh" placeholder="—"
            value={f.id_tagh_anbar}
            onChange={(v) => setField('id_tagh_anbar', v)}
          />
        )
      case 'zarib':
        return (
          <Select
            {...common}
            data={ZARIB_OPTIONS} clearable placeholder="—"
            value={f.zarib_mahal || null}
            onChange={(v) => setField('zarib_mahal', v ?? '')}
          />
        )
      case 'containerType':
        return (
          <Select
            {...common}
            data={CONTAINER_TYPES} clearable placeholder="—"
            value={f.container_type || null}
            onChange={(v) => {
              const next = v ?? ''
              setField('container_type', next)
              if (!TYPES_WITH_NUMBER.includes(next)) setField('container_number', '')
            }}
          />
        )
      case 'containerNumber': {
        const enabled = TYPES_WITH_NUMBER.includes(f.container_type)
        return (
          <TextInput
            {...common}
            dir="ltr"
            disabled={!enabled}
            placeholder={enabled ? 'MSKU1234567' : '—'}
            value={f.container_number}
            onChange={(e) => setField('container_number', e.currentTarget.value.replace(/[^A-Za-z0-9]/g, ''))}
          />
        )
      }
      case 'plate':
        return (
          <Popover
            width={540} position="bottom-end" withArrow shadow="md" trapFocus
            opened={openCell === 'plate'}
            onChange={(o) => setOpenCell(o ? 'plate' : null)}
          >
            <Popover.Target>
              <button
                type="button" className="tgg-cell-button" data-cell-open
                onClick={() => setOpenCell((c) => (c === 'plate' ? null : 'plate'))}
              >
                {isBlank(f.number_hamel) ? 'ثبت پلاک…' : formatPlate(f.number_hamel)}
              </button>
            </Popover.Target>
            <Popover.Dropdown>
              <Stack gap="sm">
                <PlateInput
                  label="شماره حامل"
                  value={f.number_hamel}
                  onChange={(v) => setField('number_hamel', v)}
                  comboboxProps={{ withinPortal: false }}
                />
                <Button size="xs" onClick={() => setOpenCell(null)}>تأیید</Button>
              </Stack>
            </Popover.Dropdown>
          </Popover>
        )
      case 'int':
        return (
          <TextInput
            {...common}
            inputMode="numeric" placeholder="—"
            value={f[col.key] as string}
            onChange={(e) => setField(col.key, normalizeIntegerInput(e.currentTarget.value))}
          />
        )
      case 'decimal':
        return (
          <TextInput
            {...common}
            inputMode="decimal" placeholder="—"
            value={f[col.key] as string}
            onChange={(e) => setField(col.key, normalizeDecimalInput(e.currentTarget.value))}
          />
        )
      case 'date': {
        return (
          <TextInput
            {...common}
            dir="ltr"
            inputMode="numeric"
            placeholder="۱۴۰۵/۰۶/۱۲ یا ۱۲/۰۶/۱۴۰۵"
            value={f.insurance_expiry_date}
            error={insuranceDateInvalid}
            aria-label="تاریخ اتمام بیمه"
            onChange={(e) => setField(
              'insurance_expiry_date',
              normalizeFlexibleJalaliInput(e.currentTarget.value),
            )}
          />
        )
      }
      default:
        return (
          <TextInput
            {...common}
            placeholder="—"
            value={f[col.key] as string}
            onChange={(e) => setField(col.key, e.currentTarget.value)}
          />
        )
    }
  }

  /**
   * Deliberately a plain function, not a <DraftCell/> component: declaring a component
   * inside the render body gives React a new component type on every render, which
   * remounts the cell and drops focus after each keystroke.
   */
  function renderDraftCell(col: ColumnDef, f: LineForm): React.ReactNode {
    const amber = copied.has(col.key)
    const duplicate = duplicates.some((d) => d.key === col.key)
    const canCopy = sourceForm != null && isCopyable(col.key) && !isBlank(sourceForm[col.key] as string | number | null)
    return (
      <Table.Td
        key={col.key}
        className={[
          'tgg-draft-cell',
          amber ? 'tgg-cell-copied' : '',
          duplicate ? 'tgg-cell-duplicate' : '',
          isNeverCopy(col.key) ? 'tgg-cell-manual' : '',
        ].filter(Boolean).join(' ')}
        onFocusCapture={() => setFocusedKey(col.key)}
      >
        <div className="tgg-cell-inner">
          <div className="tgg-cell-control">{editCell(col, f)}</div>
          {amber ? (
            <Tooltip label="بررسی شد" withArrow>
              <ActionIcon
                size="xs" variant="subtle" color="yellow" tabIndex={-1}
                aria-label={`تأیید ${col.label}`}
                onClick={() => markReviewed(col.key)}
              >
                <Check size={13} />
              </ActionIcon>
            </Tooltip>
          ) : canCopy ? (
            <Tooltip label={`کپی «${String(sourceForm?.[col.key])}» از ردیف ${sourceRowNumber}`} withArrow>
              <ActionIcon
                className="tgg-copy-icon"
                size="xs" variant="subtle" color="gray" tabIndex={-1}
                aria-label={`کپی ${col.label} از ردیف بالا`}
                onClick={() => copyCell(col.key)}
              >
                <ArrowUp size={13} />
              </ActionIcon>
            </Tooltip>
          ) : null}
        </div>
      </Table.Td>
    )
  }

  // ── render ────────────────────────────────────────────────────────────────────────

  // table-layout is fixed, so this is the real width, not a floor
  const tableWidth = COLUMNS.reduce((sum, c) => sum + c.width, 0) + 44 + 96

  return (
    <Paper className="tally-detail-section tally-detail-goods-section" radius="xl">
      <div className="tally-detail-section-header">
        <div className="tally-detail-section-heading">
          <span className="tally-detail-section-icon" aria-hidden>
            <PackageOpen size={23} strokeWidth={1.8} />
          </span>
          <div>
            <Title order={3}>ردیف‌های کالا</Title>
            <Text>اطلاعات کالا، باسکول، محل نگهداری و حامل</Text>
          </div>
        </div>
        <Button
          className="tally-detail-add-button"
          leftSection={<Plus size={18} />}
          onClick={startAdd}
          disabled={tallyId == null || draft != null}
        >
          افزودن ردیف
        </Button>
      </div>
      <div className="tally-detail-section-rule" />

      {isLoading && (
        <Center className="tally-detail-state">
          <Loader size="sm" />
          <Text>در حال بارگذاری ردیف‌ها...</Text>
        </Center>
      )}
      {isError && (
        <Center className="tally-detail-state tally-detail-state-error">
          <Text>خطا در بارگذاری ردیف‌ها.</Text>
        </Center>
      )}

      {rows.length === 0 && draft == null && !isLoading && (
        <Center className="tally-detail-empty-state">
          <PackageOpen size={28} strokeWidth={1.6} aria-hidden />
          <Text fw={700}>هنوز ردیف کالایی ثبت نشده است.</Text>
          <Text size="sm">برای شروع، گزینه «افزودن ردیف» را انتخاب کنید.</Text>
        </Center>
      )}

      {(rows.length > 0 || draft != null) && (
        <div className="tgg-shell">
          <div className="tgg-scroll">
            <Table className="tgg-table" style={{ width: tableWidth }}>
              <colgroup>
                <col style={{ width: 44 }} />
                {COLUMNS.map((c) => <col key={c.key} style={{ width: c.width }} />)}
                <col style={{ width: 96 }} />
              </colgroup>
              <Table.Thead>
                <Table.Tr className="tgg-group-row">
                  <Table.Th className="tgg-sticky-num" />
                  {GROUPS.map((g) => {
                    const span = COLUMNS.filter((c) => c.group === g.key).length
                    return (
                      <Table.Th key={g.key} colSpan={span} className={`tgg-group tgg-group-${g.key}`}>
                        {g.label}
                      </Table.Th>
                    )
                  })}
                  <Table.Th className="tgg-sticky-actions" />
                </Table.Tr>
                <Table.Tr>
                  <Table.Th className="tgg-sticky-num">#</Table.Th>
                  {COLUMNS.map((c) => (
                    <Table.Th key={c.key} title={c.label}>
                      {c.label}
                    </Table.Th>
                  ))}
                  <Table.Th className="tgg-sticky-actions">عملیات</Table.Th>
                </Table.Tr>
              </Table.Thead>

              <Table.Tbody>
                {rows.map((row, i) => (
                  draft != null && editingId === row.id_tali_details ? (
                    <Table.Tr
                      key={row.id_tali_details}
                      ref={draftRowRef}
                      className="tgg-draft-row"
                      onKeyDown={onDraftKeyDown}
                    >
                      <Table.Td className="tgg-sticky-num">{i + 1}</Table.Td>
                      {COLUMNS.map((c) => renderDraftCell(c, draft))}
                      <Table.Td className="tgg-sticky-actions">
                        <Text size="xs" c="dimmed">در حال ویرایش</Text>
                      </Table.Td>
                    </Table.Tr>
                  ) : (
                    <Table.Tr key={row.id_tali_details}>
                      <Table.Td className="tgg-sticky-num">{i + 1}</Table.Td>
                      {COLUMNS.map((c) => {
                        const text = readCell(c, row)
                        return (
                          <Table.Td
                            key={c.key}
                            title={text}
                            className={c.key === 'description_kala' ? 'tgg-primary-cell' : undefined}
                          >
                            {text}
                          </Table.Td>
                        )
                      })}
                      <Table.Td className="tgg-sticky-actions">
                        <Group gap={4} justify="center" wrap="nowrap">
                          <Tooltip label="ویرایش" withArrow>
                            <ActionIcon
                              className="tally-detail-row-action"
                              variant="light" color="blue" radius="md" aria-label="ویرایش"
                              disabled={draft != null}
                              onClick={() => startEdit(row)}
                            >
                              <IconEdit size={18} />
                            </ActionIcon>
                          </Tooltip>
                          <Tooltip label="حذف" withArrow>
                            <ActionIcon
                              className="tally-detail-row-action"
                              variant="light" color="red" radius="md" aria-label="حذف"
                              disabled={draft != null}
                              onClick={() => confirm('حذف این ردیف؟') && deleteMutation.mutate(row.id_tali_details)}
                            >
                              <IconTrash size={18} />
                            </ActionIcon>
                          </Tooltip>
                        </Group>
                      </Table.Td>
                    </Table.Tr>
                  )
                ))}

                {draft != null && editingId == null && (
                  <Table.Tr ref={draftRowRef} className="tgg-draft-row" onKeyDown={onDraftKeyDown}>
                    <Table.Td className="tgg-sticky-num">{rows.length + 1}</Table.Td>
                    {COLUMNS.map((c) => renderDraftCell(c, draft))}
                    <Table.Td className="tgg-sticky-actions">
                      <Text size="xs" c="dimmed">ردیف جدید</Text>
                    </Table.Td>
                  </Table.Tr>
                )}
              </Table.Tbody>
            </Table>
          </div>

          {draft != null && (
            <div className="tgg-actionbar">
              <Group gap="sm" wrap="wrap">
                <Button
                  size="xs" variant="light"
                  leftSection={<ArrowUp size={15} />}
                  onClick={copyRow}
                  disabled={sourceForm == null}
                >
                  کپی از ردیف بالا
                </Button>
                <Button
                  size="xs"
                  className="tally-detail-save-button"
                  loading={saveMutation.isPending}
                  onClick={() => requestSave(true)}
                >
                  {editingId == null ? 'ذخیره و ردیف بعدی' : 'ذخیره تغییرات'}
                </Button>
                {editingId == null && (
                  <Button
                    size="xs" variant="default"
                    loading={saveMutation.isPending}
                    onClick={() => requestSave(false)}
                  >
                    ذخیره و بستن
                  </Button>
                )}
                <Button size="xs" variant="subtle" color="gray" leftSection={<X size={15} />} onClick={cancelDraft}>
                  انصراف
                </Button>
                <Text size="xs" c="dimmed" className="tgg-shortcuts">
                  Ctrl+D کپی سلول · Alt+C کپی ردیف · Ctrl+Enter ذخیره · Esc انصراف
                </Text>
              </Group>
            </div>
          )}

          {draft != null && copied.size > 0 && (
            <div className="tgg-banner tgg-banner-warn">
              <AlertTriangle size={16} aria-hidden />
              <span>
                {copied.size} فیلد از ردیف {sourceRowNumber} کپی شده و هنوز بررسی نشده:{' '}
                {[...copied].map((k) => LABELS[k]).join('، ')}
              </span>
              <Button size="compact-xs" variant="subtle" color="yellow" onClick={() => setCopied(new Set())}>
                همه بررسی شد
              </Button>
            </div>
          )}

          {draft != null && duplicates.length > 0 && (
            <div className="tgg-banner tgg-banner-dup">
              <AlertTriangle size={16} aria-hidden />
              <span>
                {duplicates.map((d) => `«${LABELS[d.key]}» قبلاً در ردیف ${d.rowNumber} ثبت شده`).join(' · ')}
              </span>
            </div>
          )}

          {insuranceDateInvalid && (
            <div className="tgg-banner tgg-banner-error">
              <AlertTriangle size={16} aria-hidden />
              <span>
                تاریخ اتمام بیمه نامعتبر است؛ تاریخ شمسی را به‌شکل «۱۴۰۵/۰۶/۱۲» یا
                «۱۲/۰۶/۱۴۰۵» وارد کنید.
              </span>
            </div>
          )}

          {saveMutation.isError && (
            <div className="tgg-banner tgg-banner-error">
              <span>ذخیره انجام نشد: {(saveMutation.error as Error).message}</span>
            </div>
          )}
        </div>
      )}

      <Modal
        opened={confirmOpen}
        onClose={() => setConfirmOpen(false)}
        title="تأیید مقادیر کپی‌شده"
        radius="lg"
        size="md"
        dir="rtl"
      >
        <Stack gap="sm">
          <Text size="sm">
            این مقادیر از ردیف {sourceRowNumber} کپی شده‌اند و هنوز بررسی نشده‌اند. قبل از ذخیره یک بار
            کنترلشان کنید:
          </Text>
          <Table withTableBorder withRowBorders className="tgg-confirm-table">
            <Table.Tbody>
              {[...copied].map((k) => (
                <Table.Tr key={k}>
                  <Table.Td className="tgg-confirm-label">{LABELS[k]}</Table.Td>
                  <Table.Td>
                    {k === 'code_groupe_kala'
                      ? groupLabel(draft?.code_groupe_kala ?? null)
                      : dash(draft?.[k] as string | null)}
                  </Table.Td>
                </Table.Tr>
              ))}
            </Table.Tbody>
          </Table>
          <Group gap="sm">
            <Button
              loading={saveMutation.isPending}
              onClick={() => draft != null && saveMutation.mutate(draft)}
            >
              تأیید و ذخیره
            </Button>
            <Button variant="default" onClick={() => setConfirmOpen(false)}>
              بازگشت و بررسی
            </Button>
          </Group>
        </Stack>
      </Modal>
    </Paper>
  )
}
