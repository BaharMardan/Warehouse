import { useRef } from 'react'
import { useQuery } from '@tanstack/react-query'
import { ActionIcon, Tooltip } from '@mantine/core'
import { VolumeX } from 'lucide-react'
import { apiGet } from '../api/client'
import { usePermissions } from '../auth/usePermissions'
import { useHandoffSound } from './useHandoffSound'

interface Deliveries {
  cursor: string
  keeper: number
  operator: number
}

export function HandoffSoundNotifications() {
  const { user, can } = usePermissions()
  const eligible = can('tally.services') || can('tally.edit') || can('ghabz.issue')
  // Remount on account/permission change to reset both cursor and queued sounds.
  if (!user || !eligible || user.must_change_password) return null
  return <Listener key={JSON.stringify([user.id, user.permissions])} userId={user.id} />
}

function Listener({ userId }: { userId: number }) {
  const cursor = useRef<string | null>(null)
  const sound = useHandoffSound(true)
  const enqueue = useRef(sound.enqueue)
  enqueue.current = sound.enqueue

  useQuery({
    queryKey: ['handoff-sound', userId],
    queryFn: async () => {
      const after = cursor.current
      const result = await apiGet<Deliveries>(
        '/kartabl/handoff-events' + (after === null ? '' : `?after=${after}`),
      )
      // Initial load establishes a baseline; existing documents do not ring.
      if (after !== null) enqueue.current(result.keeper + result.operator)
      cursor.current = result.cursor
      return result.cursor
    },
    staleTime: 0,
    refetchOnMount: 'always',
    refetchInterval: 5_000,
    refetchIntervalInBackground: true,
  })

  if (sound.ready) return null
  return <Tooltip label="برای شنیدن صدای اسناد دریافتی کلیک کنید" withArrow>
    <ActionIcon variant="light" color="orange" size="lg"
      aria-label="فعال‌کردن صدای اعلان‌ها" onClick={() => void sound.enable()}>
      <VolumeX size={20} />
    </ActionIcon>
  </Tooltip>
}
