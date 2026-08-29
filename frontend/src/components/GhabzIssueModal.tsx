// import { useEffect, useMemo, useState } from 'react'
// import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
// import {
//   Alert, Badge, Button, Center, Checkbox, Group, Loader, Modal,
//   NumberInput, ScrollArea, Table, Text, Tooltip,
// } from '@mantine/core'
// import { apiGet, apiSend } from '../api/client'

// /**
//  * صدور قبض انبار — draw quantities against the tally, per goods code.
//  *
//  * The database decides the shape of this screen. FA_ghabz_anbar_DETAILES carries
//  * UNIQUE (ID_GHABZ_ANBAR_HEADAR, code_kala), and TRG_CHK_GHABZ_TALI_LIMIT caps
//  * the sum of every receipt of a tally at the tally's own totals for each
//  * CODE_GROUPE_KALA. So a receipt holds one line per code, and issuing means
//  * choosing how much of each code's remaining allotment to take — not which
//  * tally rows to copy.
//  *
//  * Amounts default to the full remainder, which is the common case: one receipt
//  * for the whole tally. Editing them down is what makes a split delivery work.
//  */

// type Allotment = {
//   code_kala: number | null
//   description_kala: string | null
//   hscode: string | null
//   type_bastem: string | null
//   anbar_name: string | null
//   tagh_name: string | null
//   tally_line_count: number
//   tally_number_kala: number
//   tally_weighte: number
//   tally_weighte_baskol: number
//   issued_number_kala: number
//   issued_weighte_asnad: number
//   issued_weighte_baskol: number
//   remaining_number_kala: number
//   remaining_weighte_asnad: number
//   remaining_weighte_baskol: number
//   has_allotment: boolean
//   drawable: boolean
// }

// type Draw = {
//   number_kala: number | ''
//   weighte_asnad: number | ''
//   weighte_baskol: number | ''
// }

// type IssueResult = {
//   id_ghabz: number
//   ghabz_number: string
//   ghabz_seq: number
//   line_count: number
// }

// const EMPTY = '—'

// function show(value: unknown): string {
//   return value == null || String(value).trim() === '' ? EMPTY : String(value)
// }

// function num(value: number | null | undefined): string {
//   if (value == null) return EMPTY
//   return new Intl.NumberFormat('en-US', { maximumFractionDigits: 3 }).format(value)
// }

// /** apiSend throws `POST /path failed: 400 {"detail":"..."}`; surface just the detail. */
// function persianError(error: unknown, fallback: string): string {
//   const raw = error instanceof Error ? error.message : String(error ?? '')
//   const match = raw.match(/\{[\s\S]*\}$/)
//   if (match) {
//     try {
//       const parsed = JSON.parse(match[0]) as { detail?: unknown }
//       if (typeof parsed.detail === 'string' && parsed.detail.trim() !== '') {
//         return parsed.detail
//       }
//     } catch {
//       // fall through to the generic message
//     }
//   }
//   return fallback
// }

// function blockedReason(row: Allotment): string {
//   if (row.code_kala == null) return 'کد گروه کالا ندارد'
//   if (!row.has_allotment) return 'مقدار مجاز در تالی صفر است'
//   return 'تمام مقدار صادر شده'
// }

// export function GhabzIssueModal({
//   opened,
//   onClose,
//   tallyId,
//   tallyNumber,
//   onIssued,
// }: {
//   opened: boolean
//   onClose: () => void
//   tallyId: number | undefined
//   tallyNumber?: string | null
//   onIssued: (result: IssueResult) => void
// }) {
//   const queryClient = useQueryClient()
//   const [selected, setSelected] = useState<number[]>([])
//   const [draws, setDraws] = useState<Record<number, Draw>>({})
//   const [error, setError] = useState<string | null>(null)

//   const { data, isLoading, isError } = useQuery({
//     queryKey: ['ghabz-allotments', tallyId],
//     queryFn: () => apiGet<Allotment[]>(`/ghabz/from-tally/${tallyId}/allotments`),
//     enabled: opened && tallyId != null,
//   })

//   const rows = useMemo(() => data ?? [], [data])
//   const available = useMemo(() => rows.filter((row) => row.drawable), [rows])

//   useEffect(() => {
//     if (!opened) return
//     setSelected(available.map((row) => row.code_kala as number))
//     setDraws(Object.fromEntries(available.map((row) => [
//       row.code_kala as number,
//       {
//         number_kala: row.remaining_number_kala,
//         weighte_asnad: row.remaining_weighte_asnad,
//         weighte_baskol: row.remaining_weighte_baskol,
//       },
//     ])))
//     setError(null)
//   }, [opened, available])

//   const issue = useMutation({
//     mutationFn: () =>
//       apiSend<IssueResult>(`/ghabz/from-tally/${tallyId}`, 'POST', {
//         lines: selected.map((code) => ({
//           code_kala: code,
//           number_kala: draws[code]?.number_kala === '' ? 0 : draws[code]?.number_kala,
//           weighte_asnad: draws[code]?.weighte_asnad === '' ? 0 : draws[code]?.weighte_asnad,
//           weighte_baskol: draws[code]?.weighte_baskol === '' ? 0 : draws[code]?.weighte_baskol,
//         })),
//       }),
//     onSuccess: (result) => {
//       queryClient.invalidateQueries({ queryKey: ['ghabz-list'] })
//       queryClient.invalidateQueries({ queryKey: ['ghabz-allotments', tallyId] })
//       onIssued(result)
//     },
//     onError: (mutationError) => {
//       setError(persianError(mutationError, 'صدور قبض انبار ناموفق بود.'))
//     },
//   })

//   const toggle = (code: number) => {
//     setSelected((current) =>
//       current.includes(code) ? current.filter((value) => value !== code) : [...current, code],
//     )
//   }

//   const setDraw = (code: number, key: keyof Draw, value: number | '') => {
//     setDraws((current) => ({
//       ...current,
//       [code]: { ...current[code], [key]: value },
//     }))
//   }

//   const allSelected = available.length > 0 && selected.length === available.length
//   const someSelected = selected.length > 0 && !allSelected
//   const nothingLeft = rows.length > 0 && available.length === 0

//   return (
//     <Modal
//       opened={opened}
//       onClose={onClose}
//       size="90%"
//       title={
//         <Group gap="xs">
//           <Text fw={600}>صدور قبض انبار</Text>
//           {tallyNumber && (
//             <Text c="dimmed" size="sm">
//               تالی <bdi dir="ltr">{tallyNumber}</bdi>
//             </Text>
//           )}
//         </Group>
//       }
//     >
//       <div dir="rtl">
//         {isLoading && <Center py="xl"><Loader /></Center>}

//         {isError && (
//           <Alert color="red" variant="light">
//             بارگذاری مقادیر تالی ناموفق بود.
//           </Alert>
//         )}

//         {rows.length === 0 && !isLoading && !isError && (
//           <Center py="xl">
//             <Text c="dimmed">این تالی هیچ ردیف کالایی ندارد.</Text>
//           </Center>
//         )}

//         {nothingLeft && (
//           <Alert color="yellow" variant="light" mb="sm">
//             مقدار باقی‌مانده‌ای برای صدور قبض انبار در این تالی وجود ندارد.
//           </Alert>
//         )}

//         {rows.length > 0 && (
//           <>
//             <Text size="sm" c="dimmed" mb="xs">
//               مقدار هر کد کالا به‌صورت پیش‌فرض برابر باقی‌مانده تالی است. برای صدور
//               قبض جزئی، مقدار را کمتر کنید؛ مابقی در قبض‌های بعدی قابل صدور است.
//             </Text>

//             <Group justify="space-between" mb="xs">
//               <Text size="sm" c="dimmed">
//                 {selected.length} کد کالا از {available.length} کد قابل صدور انتخاب شده است
//               </Text>
//               <Group gap="xs">
//                 <Button
//                   size="xs"
//                   variant="subtle"
//                   disabled={available.length === 0}
//                   onClick={() => setSelected(available.map((row) => row.code_kala as number))}
//                 >
//                   انتخاب همه
//                 </Button>
//                 <Button
//                   size="xs"
//                   variant="subtle"
//                   disabled={selected.length === 0}
//                   onClick={() => setSelected([])}
//                 >
//                   حذف انتخاب‌ها
//                 </Button>
//               </Group>
//             </Group>

//             <ScrollArea.Autosize mah={420}>
//               <Table striped highlightOnHover withTableBorder>
//                 <Table.Thead>
//                   <Table.Tr>
//                     <Table.Th w={44}>
//                       <Checkbox
//                         aria-label="انتخاب همه کدها"
//                         checked={allSelected}
//                         indeterminate={someSelected}
//                         disabled={available.length === 0}
//                         onChange={(event) =>
//                           setSelected(
//                             event.currentTarget.checked
//                               ? available.map((row) => row.code_kala as number)
//                               : [],
//                           )
//                         }
//                       />
//                     </Table.Th>
//                     <Table.Th>کد گروه کالا</Table.Th>
//                     <Table.Th>شرح کالا</Table.Th>
//                     <Table.Th>باقی‌مانده تالی</Table.Th>
//                     <Table.Th>تعداد</Table.Th>
//                     <Table.Th>وزن اسناد</Table.Th>
//                     <Table.Th>وزن باسکول</Table.Th>
//                   </Table.Tr>
//                 </Table.Thead>
//                 <Table.Tbody>
//                   {rows.map((row, index) => {
//                     const code = row.code_kala
//                     const blocked = !row.drawable
//                     const key = code ?? `blocked-${index}`
//                     const checked = code != null && selected.includes(code)
//                     const draw = code != null ? draws[code] : undefined

//                     return (
//                       <Table.Tr key={key} opacity={blocked ? 0.55 : 1}>
//                         <Table.Td>
//                           <Checkbox
//                             aria-label={`انتخاب کد ${show(code)}`}
//                             checked={checked}
//                             disabled={blocked}
//                             onChange={() => { if (code != null) toggle(code) }}
//                           />
//                         </Table.Td>
//                         <Table.Td><bdi dir="ltr">{show(code)}</bdi></Table.Td>
//                         <Table.Td>
//                           {show(row.description_kala)}
//                           {row.tally_line_count > 1 && (
//                             <Tooltip label={`${row.tally_line_count} ردیف تالی با این کد`}>
//                               <Badge ml="xs" size="xs" variant="light" color="blue">
//                                 {row.tally_line_count} ردیف
//                               </Badge>
//                             </Tooltip>
//                           )}
//                         </Table.Td>
//                         <Table.Td>
//                           {blocked ? (
//                             <Badge color="gray" variant="light" size="sm">
//                               {blockedReason(row)}
//                             </Badge>
//                           ) : (
//                             <Text size="xs" c="dimmed">
//                               <bdi dir="ltr">
//                                 {num(row.remaining_number_kala)} / {num(row.remaining_weighte_asnad)} / {num(row.remaining_weighte_baskol)}
//                               </bdi>
//                             </Text>
//                           )}
//                         </Table.Td>
//                         {(['number_kala', 'weighte_asnad', 'weighte_baskol'] as const).map(
//                           (measure) => {
//                             const max =
//                               measure === 'number_kala' ? row.remaining_number_kala
//                               : measure === 'weighte_asnad' ? row.remaining_weighte_asnad
//                               : row.remaining_weighte_baskol
//                             return (
//                               <Table.Td key={measure}>
//                                 <NumberInput
//                                   size="xs"
//                                   w={120}
//                                   min={0}
//                                   max={max}
//                                   clampBehavior="strict"
//                                   disabled={blocked || !checked}
//                                   value={draw?.[measure] ?? ''}
//                                   onChange={(value) => {
//                                     if (code == null) return
//                                     setDraw(
//                                       code,
//                                       measure,
//                                       value === '' ? '' : Number(value),
//                                     )
//                                   }}
//                                 />
//                               </Table.Td>
//                             )
//                           },
//                         )}
//                       </Table.Tr>
//                     )
//                   })}
//                 </Table.Tbody>
//               </Table>
//             </ScrollArea.Autosize>
//           </>
//         )}

//         {error && <Alert color="red" variant="light" mt="sm">{error}</Alert>}

//         <Group justify="flex-start" mt="lg">
//           <Button
//             color="teal"
//             loading={issue.isPending}
//             disabled={selected.length === 0 || tallyId == null}
//             onClick={() => { setError(null); issue.mutate() }}
//           >
//             صدور قبض انبار
//           </Button>
//           <Button variant="subtle" onClick={onClose}>انصراف</Button>
//         </Group>
//       </div>
//     </Modal>
//   )
// }


import { useEffect, useMemo, useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import {
  Alert, Badge, Button, Center, Checkbox, Group, Loader, Modal,
  NumberInput, ScrollArea, Table, Text, Tooltip,
} from '@mantine/core'
import { apiGet, apiSend } from '../api/client'

/**
 * صدور قبض انبار — draw quantities against the tally, per goods code.
 *
 * The database decides the shape of this screen. FA_ghabz_anbar_DETAILES carries
 * UNIQUE (ID_GHABZ_ANBAR_HEADAR, code_kala), and TRG_CHK_GHABZ_TALI_LIMIT caps
 * the sum of every receipt of a tally at the tally's own totals for each
 * CODE_GROUPE_KALA. So a receipt holds one line per code, and issuing means
 * choosing how much of each code's remaining allotment to take — not which
 * tally rows to copy.
 *
 * Amounts default to the full remainder, which is the common case: one receipt
 * for the whole tally. Editing them down is what makes a split delivery work.
 */

type Allotment = {
  code_kala: number | null
  description_kala: string | null
  hscode: string | null
  type_bastem: string | null
  anbar_name: string | null
  tagh_name: string | null
  tally_line_count: number
  tally_number_kala: number
  tally_weighte: number
  tally_weighte_baskol: number
  issued_number_kala: number
  issued_weighte_asnad: number
  issued_weighte_baskol: number
  remaining_number_kala: number
  remaining_weighte_asnad: number
  remaining_weighte_baskol: number
  has_allotment: boolean
  over_issued: boolean
  drawable: boolean
}

type Draw = {
  number_kala: number | ''
  weighte_asnad: number | ''
  weighte_baskol: number | ''
}

type IssueResult = {
  id_ghabz: number
  ghabz_number: string
  ghabz_seq: number
  line_count: number
}

const EMPTY = '—'

function show(value: unknown): string {
  return value == null || String(value).trim() === '' ? EMPTY : String(value)
}

function num(value: number | null | undefined): string {
  if (value == null) return EMPTY
  return new Intl.NumberFormat('en-US', { maximumFractionDigits: 3 }).format(value)
}

/** apiSend throws `POST /path failed: 400 {"detail":"..."}`; surface just the detail. */
function persianError(error: unknown, fallback: string): string {
  const raw = error instanceof Error ? error.message : String(error ?? '')
  const match = raw.match(/\{[\s\S]*\}$/)
  if (match) {
    try {
      const parsed = JSON.parse(match[0]) as { detail?: unknown }
      if (typeof parsed.detail === 'string' && parsed.detail.trim() !== '') {
        return parsed.detail
      }
    } catch {
      // fall through to the generic message
    }
  }
  return fallback
}

function blockedReason(row: Allotment): string {
  if (row.code_kala == null) return 'کد گروه کالا ندارد'
  if (!row.has_allotment) return 'مقدار مجاز در تالی صفر است'
  return 'تمام مقدار صادر شده'
}

export function GhabzIssueModal({
  opened,
  onClose,
  tallyId,
  tallyNumber,
  onIssued,
}: {
  opened: boolean
  onClose: () => void
  tallyId: number | undefined
  tallyNumber?: string | null
  onIssued: (result: IssueResult) => void
}) {
  const queryClient = useQueryClient()
  const [selected, setSelected] = useState<number[]>([])
  const [draws, setDraws] = useState<Record<number, Draw>>({})
  const [error, setError] = useState<string | null>(null)

  const { data, isLoading, isError } = useQuery({
    queryKey: ['ghabz-allotments', tallyId],
    queryFn: () => apiGet<Allotment[]>(`/ghabz/from-tally/${tallyId}/allotments`),
    enabled: opened && tallyId != null,
  })

  const rows = useMemo(() => data ?? [], [data])
  const available = useMemo(() => rows.filter((row) => row.drawable), [rows])

  useEffect(() => {
    if (!opened) return
    setSelected(available.map((row) => row.code_kala as number))
    setDraws(Object.fromEntries(available.map((row) => [
      row.code_kala as number,
      {
        number_kala: Math.max(row.remaining_number_kala, 0),
        weighte_asnad: Math.max(row.remaining_weighte_asnad, 0),
        weighte_baskol: Math.max(row.remaining_weighte_baskol, 0),
      },
    ])))
    setError(null)
  }, [opened, available])

  const issue = useMutation({
    mutationFn: () =>
      apiSend<IssueResult>(`/ghabz/from-tally/${tallyId}`, 'POST', {
        lines: selected.map((code) => ({
          code_kala: code,
          number_kala: draws[code]?.number_kala === '' ? 0 : draws[code]?.number_kala,
          weighte_asnad: draws[code]?.weighte_asnad === '' ? 0 : draws[code]?.weighte_asnad,
          weighte_baskol: draws[code]?.weighte_baskol === '' ? 0 : draws[code]?.weighte_baskol,
        })),
      }),
    onSuccess: (result) => {
      queryClient.invalidateQueries({ queryKey: ['ghabz-list'] })
      queryClient.invalidateQueries({ queryKey: ['ghabz-allotments', tallyId] })
      onIssued(result)
    },
    onError: (mutationError) => {
      setError(persianError(mutationError, 'صدور قبض انبار ناموفق بود.'))
    },
  })

  const toggle = (code: number) => {
    setSelected((current) =>
      current.includes(code) ? current.filter((value) => value !== code) : [...current, code],
    )
  }

  const setDraw = (code: number, key: keyof Draw, value: number | '') => {
    setDraws((current) => ({
      ...current,
      [code]: { ...current[code], [key]: value },
    }))
  }

  const allSelected = available.length > 0 && selected.length === available.length
  const someSelected = selected.length > 0 && !allSelected
  const nothingLeft = rows.length > 0 && available.length === 0

  return (
    <Modal
      opened={opened}
      onClose={onClose}
      size="90%"
      title={
        <Group gap="xs">
          <Text fw={600}>صدور قبض انبار</Text>
          {tallyNumber && (
            <Text c="dimmed" size="sm">
              تالی <bdi dir="ltr">{tallyNumber}</bdi>
            </Text>
          )}
        </Group>
      }
    >
      <div dir="rtl">
        {isLoading && <Center py="xl"><Loader /></Center>}

        {isError && (
          <Alert color="red" variant="light">
            بارگذاری مقادیر تالی ناموفق بود.
          </Alert>
        )}

        {rows.length === 0 && !isLoading && !isError && (
          <Center py="xl">
            <Text c="dimmed">این تالی هیچ ردیف کالایی ندارد.</Text>
          </Center>
        )}

        {nothingLeft && (
          <Alert color="yellow" variant="light" mb="sm">
            مقدار باقی‌مانده‌ای برای صدور قبض انبار در این تالی وجود ندارد.
          </Alert>
        )}

        {rows.length > 0 && (
          <>
            <Text size="sm" c="dimmed" mb="xs">
              مقدار هر کد کالا به‌صورت پیش‌فرض برابر باقی‌مانده تالی است. برای صدور
              قبض جزئی، مقدار را کمتر کنید؛ مابقی در قبض‌های بعدی قابل صدور است.
            </Text>

            <Group justify="space-between" mb="xs">
              <Text size="sm" c="dimmed">
                {selected.length} کد کالا از {available.length} کد قابل صدور انتخاب شده است
              </Text>
              <Group gap="xs">
                <Button
                  size="xs"
                  variant="subtle"
                  disabled={available.length === 0}
                  onClick={() => setSelected(available.map((row) => row.code_kala as number))}
                >
                  انتخاب همه
                </Button>
                <Button
                  size="xs"
                  variant="subtle"
                  disabled={selected.length === 0}
                  onClick={() => setSelected([])}
                >
                  حذف انتخاب‌ها
                </Button>
              </Group>
            </Group>

            <ScrollArea.Autosize mah={420}>
              <Table striped highlightOnHover withTableBorder>
                <Table.Thead>
                  <Table.Tr>
                    <Table.Th w={44}>
                      <Checkbox
                        aria-label="انتخاب همه کدها"
                        checked={allSelected}
                        indeterminate={someSelected}
                        disabled={available.length === 0}
                        onChange={(event) =>
                          setSelected(
                            event.currentTarget.checked
                              ? available.map((row) => row.code_kala as number)
                              : [],
                          )
                        }
                      />
                    </Table.Th>
                    <Table.Th>کد گروه کالا</Table.Th>
                    <Table.Th>شرح کالا</Table.Th>
                    <Table.Th>باقی‌مانده تالی</Table.Th>
                    <Table.Th>تعداد</Table.Th>
                    <Table.Th>وزن اسناد</Table.Th>
                    <Table.Th>وزن باسکول</Table.Th>
                  </Table.Tr>
                </Table.Thead>
                <Table.Tbody>
                  {rows.map((row, index) => {
                    const code = row.code_kala
                    const blocked = !row.drawable
                    const key = code ?? `blocked-${index}`
                    const checked = code != null && selected.includes(code)
                    const draw = code != null ? draws[code] : undefined

                    return (
                      <Table.Tr key={key} opacity={blocked ? 0.55 : 1}>
                        <Table.Td>
                          <Checkbox
                            aria-label={`انتخاب کد ${show(code)}`}
                            checked={checked}
                            disabled={blocked}
                            onChange={() => { if (code != null) toggle(code) }}
                          />
                        </Table.Td>
                        <Table.Td><bdi dir="ltr">{show(code)}</bdi></Table.Td>
                        <Table.Td>
                          {show(row.description_kala)}
                          {row.tally_line_count > 1 && (
                            <Tooltip label={`${row.tally_line_count} ردیف تالی با این کد`}>
                              <Badge ml="xs" size="xs" variant="light" color="blue">
                                {row.tally_line_count} ردیف
                              </Badge>
                            </Tooltip>
                          )}
                        </Table.Td>
                        <Table.Td>
                          {blocked ? (
                            <Badge color="gray" variant="light" size="sm">
                              {blockedReason(row)}
                            </Badge>
                          ) : (
                            <>
                              <Text size="xs" c="dimmed">
                                <bdi dir="ltr">
                                  {num(row.remaining_number_kala)} / {num(row.remaining_weighte_asnad)} / {num(row.remaining_weighte_baskol)}
                                </bdi>
                              </Text>
                              {row.over_issued && (
                                <Tooltip
                                  multiline
                                  w={260}
                                  label="مقدار صادرشده در قبض‌ها از مقدار فعلی تالی بیشتر است؛ احتمالاً ردیفی از تالی پس از صدور قبض حذف شده. مقدار قابل صدور صفر در نظر گرفته شد."
                                >
                                  <Badge color="orange" variant="light" size="xs" mt={4}>
                                    مغایرت با تالی
                                  </Badge>
                                </Tooltip>
                              )}
                            </>
                          )}
                        </Table.Td>
                        {(['number_kala', 'weighte_asnad', 'weighte_baskol'] as const).map(
                          (measure) => {
                            // remaining_* is already clamped at zero server-side;
                            // guard again so max can never fall below min.
                            const max = Math.max(
                              measure === 'number_kala' ? row.remaining_number_kala
                              : measure === 'weighte_asnad' ? row.remaining_weighte_asnad
                              : row.remaining_weighte_baskol,
                              0,
                            )
                            return (
                              <Table.Td key={measure}>
                                <NumberInput
                                  size="xs"
                                  w={120}
                                  min={0}
                                  max={max}
                                  clampBehavior="strict"
                                  disabled={blocked || !checked}
                                  value={draw?.[measure] ?? ''}
                                  onChange={(value) => {
                                    if (code == null) return
                                    setDraw(
                                      code,
                                      measure,
                                      value === '' ? '' : Number(value),
                                    )
                                  }}
                                />
                              </Table.Td>
                            )
                          },
                        )}
                      </Table.Tr>
                    )
                  })}
                </Table.Tbody>
              </Table>
            </ScrollArea.Autosize>
          </>
        )}

        {error && <Alert color="red" variant="light" mt="sm">{error}</Alert>}

        <Group justify="flex-start" mt="lg">
          <Button
            color="teal"
            loading={issue.isPending}
            disabled={selected.length === 0 || tallyId == null}
            onClick={() => { setError(null); issue.mutate() }}
          >
            صدور قبض انبار
          </Button>
          <Button variant="subtle" onClick={onClose}>انصراف</Button>
        </Group>
      </div>
    </Modal>
  )
}
