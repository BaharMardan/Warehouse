import { useEffect, useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { Badge, Button, Group, Paper, Radio, Stack, Text, TextInput, Tooltip } from '@mantine/core'
import { Send, Undo2 } from 'lucide-react'
import { errorMessage } from '../api/client'
import { KEEPER_QUEUE_KEY, handoffApi, handoffKey, type HandoffState, type CargoTypeAnswer } from '../api/handoff'
import { usePermissions } from '../auth/usePermissions'

/**
 * The tally's handoff between the operator and the warehouse keeper.
 *
 * The operator sends a tally on once it has goods rows; the keeper answers
 * «آیا کالا حجمی است؟», fills the five service sections and sends it back, which
 * is what unlocks «صدور قبض انبار». The server enforces all of that; these
 * components only show each person the step that is theirs.
 */

const PERSIAN_DIGITS = '۰۱۲۳۴۵۶۷۸۹'
const faDigits = (value: string | number) =>
  String(value).replace(/\d/g, (digit) => PERSIAN_DIGITS[Number(digit)])
const latinDigits = (value: string) =>
  value.replace(/[۰-۹]/g, (d) => String(d.charCodeAt(0) - 0x06f0))
    .replace(/[٠-٩]/g, (d) => String(d.charCodeAt(0) - 0x0660))

/** The database already formats this value in the Persian calendar.
 * Keeping it as text avoids applying the operator's browser timezone. */
const serverMoment = (value: string | null | undefined) => value ? faDigits(value) : ''

export function useHandoff(tallyId: number | null | undefined) {
  return useQuery({
    queryKey: handoffKey(tallyId),
    queryFn: () => handoffApi.read(tallyId as number),
    enabled: tallyId != null,
  })
}

/** Every move updates this tally, the keeper's queue count and the worklist. */
function useHandoffAction<TInput>(
  tallyId: number | null | undefined,
  action: (input: TInput) => Promise<HandoffState>,
  failure: string,
) {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: action,
    onSuccess: (state) => {
      queryClient.setQueryData(handoffKey(tallyId), state)
      queryClient.invalidateQueries({ queryKey: KEEPER_QUEUE_KEY })
      queryClient.invalidateQueries({ queryKey: ['kartabl-list'] })
    },
    onError: (error) => alert(errorMessage(error, failure)),
  })
}

const TONE = {
  operator: { color: 'blue', title: 'در دست اپراتور' },
  keeper: { color: 'orange', title: 'در انتظار انباردار' },
  returned: { color: 'teal', title: 'تکمیل‌شده توسط انباردار' },
} as const

export function HandoffBanner({ state }: { state: HandoffState | undefined }) {
  // An unknown step means an older or newer server than this page: show nothing
  // rather than taking the whole tally page down with it.
  const tone = state ? TONE[state.step] : undefined
  if (!state || !tone) return null

  let detail = 'پس از ثبت ردیف‌های کالا، تالی را برای انباردار بفرستید.'
  if (state.step === 'keeper') {
    detail = `ارسال‌شده توسط ${state.sent_to_keeper_by ?? 'اپراتور'} در ${serverMoment(state.sent_to_keeper_at_display)}`
  } else if (state.step === 'returned') {
    detail = state.returned_at
      ? `برگردانده‌شده توسط ${state.returned_by ?? 'انباردار'} در ${serverMoment(state.returned_at_display)}`
      : 'پیش از راه‌اندازی این گردش کار تکمیل شده است.'
  }

  const answer = state.cargo_type === 'volumetric'
    ? `نوع بار: حجمی${state.volumetric_pallets ? `، ${faDigits(state.volumetric_pallets)} پالت` : ''}`
    : state.cargo_type === 'weight' ? 'نوع بار: وزنی'
      : state.cargo_type === 'container' ? 'نوع بار: کانتینری' : null

  return (
    <Paper withBorder radius="lg" p="sm" mb="md">
      <Group justify="space-between" wrap="wrap" gap="xs">
        <Group gap="sm" wrap="nowrap">
          <Badge color={tone.color} variant="light" radius="sm">{tone.title}</Badge>
          <Text size="sm" c="dimmed">{detail}</Text>
        </Group>
        {answer && <Text size="sm" fw={600}>{answer}</Text>}
      </Group>
    </Paper>
  )
}

/** Sits next to «افزودن ردیف»: the operator's last step before the keeper takes over. */
export function SendToKeeperButton({ tallyId, state }: { tallyId: number | null | undefined; state: HandoffState | undefined }) {
  const { can } = usePermissions()
  const send = useHandoffAction(tallyId, () => handoffApi.sendToKeeper(tallyId as number), 'ارسال به انباردار انجام نشد.')

  if (!can('tally.edit') || tallyId == null || state?.step !== 'operator') return null

  const ready = state.goods_rows > 0
  return (
    <Tooltip label="ابتدا دست‌کم یک ردیف کالا ثبت کنید" disabled={ready} withArrow>
      <span>
        <Button
          color="orange"
          leftSection={<Send size={18} />}
          disabled={!ready}
          loading={send.isPending}
          onClick={() => send.mutate(undefined as never)}
        >
          ارسال به انباردار
        </Button>
      </span>
    </Tooltip>
  )
}

// /** The keeper's first task, above the service sections. Each answer saves immediately. */
// export function VolumetricCard({ tallyId, state }: { tallyId: number | null | undefined; state: HandoffState | undefined }) {
//   const { can } = usePermissions()
//   const save = useHandoffAction(
//     tallyId,
//     (answer: VolumetricAnswer) => handoffApi.saveVolumetric(tallyId as number, answer),
//     'ثبت پاسخ انجام نشد.',
//   )
//   const [pallets, setPallets] = useState('')

//   const savedPallets = state?.volumetric_pallets ?? null
//   useEffect(() => {
//     setPallets(savedPallets == null ? '' : faDigits(savedPallets))
//   }, [savedPallets])

//   if (!can('tally.services') || tallyId == null || state?.step !== 'keeper') return null

//   const savePallets = () => {
//     const typed = latinDigits(pallets).trim()
//     const value = typed === '' ? null : Number(typed)
//     if (value !== null && (!Number.isInteger(value) || value < 1)) {
//       alert('تعداد پالت باید عددی صحیح و دست‌کم ۱ باشد')
//       return
//     }
//     if (value === savedPallets) return
//     save.mutate({ is_volumetric: 'yes', volumetric_pallets: value })
//   }

//   return (
//     <Paper withBorder radius="lg" p="md" mb="md">
//       <Group justify="space-between" wrap="wrap" gap="md">
//         <Stack gap={2}>
//           <Text fw={700}>آیا کالا حجمی است؟</Text>
//           <Text size="xs" c="dimmed">پاسخ بلافاصله ذخیره می‌شود و برای برگرداندن تالی لازم است.</Text>
//         </Stack>
//         <Group gap="lg" wrap="wrap">
//           <Radio.Group
//             value={state.is_volumetric ?? ''}
//             onChange={(value) => save.mutate(
//               value === 'yes'
//                 ? { is_volumetric: 'yes', volumetric_pallets: savedPallets }
//                 : { is_volumetric: 'no', volumetric_pallets: null },
//             )}
//           >
//             <Group gap="md">
//               <Radio value="yes" label="بله" disabled={save.isPending} />
//               <Radio value="no" label="خیر" disabled={save.isPending} />
//             </Group>
//           </Radio.Group>
//           {state.is_volumetric === 'yes' && (
//             <TextInput
//               label="تعداد پالت"
//               inputMode="numeric"
//               w={150}
//               value={pallets}
//               onChange={(event) => setPallets(event.currentTarget.value)}
//               onBlur={savePallets}
//               onKeyDown={(event) => {
//                 if (event.key === 'Enter') event.currentTarget.blur()
//               }}
//             />
//           )}
//           {save.isPending && <Text size="xs" c="dimmed">در حال ذخیره…</Text>}
//         </Group>
//       </Group>
//     </Paper>
//   )
// }

export function VolumetricCard({
  tallyId,
  state,
}: {
  tallyId: number | null | undefined
  state: HandoffState | undefined
}) {
  const { can } = usePermissions()

  const save = useHandoffAction(
    tallyId,
    (answer: CargoTypeAnswer) =>
      handoffApi.saveCargoType(tallyId as number, answer),
    'ثبت پاسخ انجام نشد.',
  )

  const [pallets, setPallets] = useState('')
  const savedPallets = state?.volumetric_pallets ?? null

  useEffect(() => {
    setPallets(savedPallets == null ? '' : faDigits(savedPallets))
  }, [savedPallets])

  if (
    !can('tally.services') ||
    tallyId == null ||
    state?.step !== 'keeper'
  ) {
    return null
  }

  const savePallets = () => {
    const typed = latinDigits(pallets).trim()
    const value = typed === '' ? null : Number(typed)

    if (
      value !== null &&
      (!Number.isInteger(value) || value < 1)
    ) {
      alert('تعداد پالت باید عددی صحیح و دست‌کم ۱ باشد')
      return
    }

    if (value === savedPallets) return

    save.mutate({
      cargo_type: 'volumetric',
      volumetric_pallets: value,
    })
  }

  return (
    <Paper
      className="tally-detail-section volumetric-card"
      radius="xl"
      dir="rtl"
    >
      <div className="tally-detail-section-header">
        <div className="volumetric-heading">
          <span
            className="tally-detail-section-icon"
            aria-hidden="true"
          >
            <svg
              width="24"
              height="24"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="1.8"
              strokeLinecap="round"
              strokeLinejoin="round"
            >
              <path d="m12 3 9 5-9 5-9-5 9-5Z" />
              <path d="M3 8v8l9 5 9-5V8" />
              <path d="M12 13v8" />
              <path d="m7.5 5.5 9 5" />
            </svg>
          </span>

          <div className="tally-detail-section-heading">
            <h3>نوع بار چیست؟</h3>
            
          </div>
        </div>

        <Badge
          color={state.cargo_type ? 'teal' : 'orange'}
          variant="light"
          radius="sm"
          role="status"
        >
          {save.isPending
            ? 'در حال ذخیره…'
            : state.cargo_type
              ? 'پاسخ ثبت شده'
              : 'نیاز به پاسخ'}
        </Badge>
      </div>

      <div className="tally-detail-section-rule" />

      <div className="volumetric-body">
        <Radio.Group
          name={`cargo-type-${tallyId}`}
          value={state.cargo_type ?? ''}
          onChange={(value) => {
            if (value === 'weight' || value === 'volumetric' || value === 'container') {
              save.mutate({ cargo_type: value, volumetric_pallets: value === 'volumetric' ? savedPallets : null })
            }
          }}
        >
          <div className="volumetric-options">
            <div
              className="volumetric-option"
              data-selected={state.cargo_type === 'weight'}
            >
              <Radio
                value="weight"
                label="وزنی"
                disabled={save.isPending}
                size="md"
                styles={{
                  body: { alignItems: 'center' },
                  labelWrapper: { flex: 1 },
                  label: {
                    cursor: 'pointer',
                    fontWeight: 600,
                    paddingBlock: 8,
                  },
                }}
              />
            </div>

            <div
              className="volumetric-option"
              data-selected={state.cargo_type === 'volumetric'}
            >
              <div className="volumetric-option-content">
                <Radio
                  value="volumetric"
                  label="حجمی"
                  disabled={save.isPending}
                  size="md"
                  styles={{
                    body: { alignItems: 'center' },
                    labelWrapper: { flex: 1 },
                    label: { cursor: 'pointer', fontWeight: 600, paddingBlock: 8 },
                  }}
                />
                {state.cargo_type === 'volumetric' && (
                  <div className="volumetric-pallets">
                    <TextInput
                      aria-label="تعداد پالت"
                      placeholder="تعداد پالت"
                      inputMode="numeric"
                      autoComplete="off"
                      size="sm"
                      value={pallets}
                      disabled={save.isPending}
                      onChange={(event) => setPallets(latinDigits(event.currentTarget.value).replace(/\D/g, ''))}
                      onBlur={savePallets}
                      onKeyDown={(event) => { if (event.key === 'Enter') event.currentTarget.blur() }}
                    />
                  </div>
                )}
              </div>
            </div>
            <div className="volumetric-option" data-selected={state.cargo_type === 'container'}>
              <Radio
                value="container"
                label="کانتینری"
                disabled={save.isPending}
                size="md"
              />
            </div>
          </div>
        </Radio.Group>

        {false && (
          <div className="volumetric-pallets">
            <TextInput label="تعداد پالت" />
          </div>
        )}

        <Text size="xs" c="dimmed">
          پاسخ شما به‌صورت خودکار ذخیره می‌شود.
        </Text>
      </div>
    </Paper>
  )
}

/** Bottom of the page: hands the tally back and unlocks «صدور قبض انبار». */
export function ReturnToOperatorButton({ tallyId, state }: { tallyId: number | null | undefined; state: HandoffState | undefined }) {
  const { can } = usePermissions()
  const back = useHandoffAction(tallyId, () => handoffApi.returnToOperator(tallyId as number), 'ارسال به اپراتور انجام نشد.')

  if (!can('tally.services') || tallyId == null || state?.step !== 'keeper') return null

  const blocked = state.cargo_type == null
    ? 'ابتدا نوع بار را انتخاب کنید'
    : state.cargo_type === 'volumetric' && !state.volumetric_pallets
      ? 'تعداد پالت را وارد کنید'
      : null

  return (
    <Paper withBorder radius="lg" p="md" mt="md">
      <Group justify="space-between" wrap="wrap" gap="sm">
        <Text size="sm" c="dimmed">
          پس از تکمیل بخش‌های خدمات، تالی را به اپراتور برگردانید تا قبض انبار صادر شود.
        </Text>
        <Tooltip label={blocked ?? ''} disabled={blocked == null} withArrow>
          <span>
            <Button
              color="teal"
              leftSection={<Undo2 size={18} />}
              disabled={blocked != null}
              loading={back.isPending}
              onClick={() => back.mutate(undefined as never)}
            >
              ارسال به صدور اسناد
            </Button>
          </span>
        </Tooltip>
      </Group>
    </Paper>
  )
}
