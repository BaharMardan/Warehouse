import { useEffect, useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { Badge, Button, Group, Paper, Radio, Stack, Text, TextInput, Tooltip } from '@mantine/core'
import { toJalaali } from 'jalaali-js'
import { Send, Undo2 } from 'lucide-react'
import { errorMessage } from '../api/client'
import { KEEPER_QUEUE_KEY, handoffApi, handoffKey, type HandoffState, type VolumetricAnswer } from '../api/handoff'
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

function jalaliMoment(iso: string | null): string {
  if (!iso) return ''
  const moment = new Date(iso)
  if (Number.isNaN(moment.getTime())) return ''
  const { jy, jm, jd } = toJalaali(moment)
  const pad = (value: number) => String(value).padStart(2, '0')
  return faDigits(`${jy}/${pad(jm)}/${pad(jd)} ساعت ${pad(moment.getHours())}:${pad(moment.getMinutes())}`)
}

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
    detail = `ارسال‌شده توسط ${state.sent_to_keeper_by ?? 'اپراتور'} در ${jalaliMoment(state.sent_to_keeper_at)}`
  } else if (state.step === 'returned') {
    detail = state.returned_at
      ? `برگردانده‌شده توسط ${state.returned_by ?? 'انباردار'} در ${jalaliMoment(state.returned_at)}`
      : 'پیش از راه‌اندازی این گردش کار تکمیل شده است.'
  }

  const answer = state.is_volumetric === 'yes'
    ? `کالای حجمی: بله${state.volumetric_pallets ? `، ${faDigits(state.volumetric_pallets)} پالت` : ''}`
    : state.is_volumetric === 'no' ? 'کالای حجمی: خیر' : null

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

/** The keeper's first task, above the service sections. Each answer saves immediately. */
export function VolumetricCard({ tallyId, state }: { tallyId: number | null | undefined; state: HandoffState | undefined }) {
  const { can } = usePermissions()
  const save = useHandoffAction(
    tallyId,
    (answer: VolumetricAnswer) => handoffApi.saveVolumetric(tallyId as number, answer),
    'ثبت پاسخ انجام نشد.',
  )
  const [pallets, setPallets] = useState('')

  const savedPallets = state?.volumetric_pallets ?? null
  useEffect(() => {
    setPallets(savedPallets == null ? '' : faDigits(savedPallets))
  }, [savedPallets])

  if (!can('tally.services') || tallyId == null || state?.step !== 'keeper') return null

  const savePallets = () => {
    const typed = latinDigits(pallets).trim()
    const value = typed === '' ? null : Number(typed)
    if (value !== null && (!Number.isInteger(value) || value < 1)) {
      alert('تعداد پالت باید عددی صحیح و دست‌کم ۱ باشد')
      return
    }
    if (value === savedPallets) return
    save.mutate({ is_volumetric: 'yes', volumetric_pallets: value })
  }

  return (
    <Paper withBorder radius="lg" p="md" mb="md">
      <Group justify="space-between" wrap="wrap" gap="md">
        <Stack gap={2}>
          <Text fw={700}>آیا کالا حجمی است؟</Text>
          <Text size="xs" c="dimmed">پاسخ بلافاصله ذخیره می‌شود و برای برگرداندن تالی لازم است.</Text>
        </Stack>
        <Group gap="lg" wrap="wrap">
          <Radio.Group
            value={state.is_volumetric ?? ''}
            onChange={(value) => save.mutate(
              value === 'yes'
                ? { is_volumetric: 'yes', volumetric_pallets: savedPallets }
                : { is_volumetric: 'no', volumetric_pallets: null },
            )}
          >
            <Group gap="md">
              <Radio value="yes" label="بله" disabled={save.isPending} />
              <Radio value="no" label="خیر" disabled={save.isPending} />
            </Group>
          </Radio.Group>
          {state.is_volumetric === 'yes' && (
            <TextInput
              label="تعداد پالت"
              inputMode="numeric"
              w={150}
              value={pallets}
              onChange={(event) => setPallets(event.currentTarget.value)}
              onBlur={savePallets}
              onKeyDown={(event) => {
                if (event.key === 'Enter') event.currentTarget.blur()
              }}
            />
          )}
          {save.isPending && <Text size="xs" c="dimmed">در حال ذخیره…</Text>}
        </Group>
      </Group>
    </Paper>
  )
}

/** Bottom of the page: hands the tally back and unlocks «صدور قبض انبار». */
export function ReturnToOperatorButton({ tallyId, state }: { tallyId: number | null | undefined; state: HandoffState | undefined }) {
  const { can } = usePermissions()
  const back = useHandoffAction(tallyId, () => handoffApi.returnToOperator(tallyId as number), 'ارسال به اپراتور انجام نشد.')

  if (!can('tally.services') || tallyId == null || state?.step !== 'keeper') return null

  const blocked = state.is_volumetric == null
    ? 'ابتدا به پرسش «آیا کالا حجمی است؟» پاسخ دهید'
    : state.is_volumetric === 'yes' && !state.volumetric_pallets
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
              ارسال به اپراتور
            </Button>
          </span>
        </Tooltip>
      </Group>
    </Paper>
  )
}
