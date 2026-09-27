import { useEffect, useRef } from 'react'
import { useQuery } from '@tanstack/react-query'
import { ActionIcon, Indicator, Tooltip } from '@mantine/core'
import { useNavigate } from 'react-router-dom'
import { Bell } from 'lucide-react'
import { KEEPER_QUEUE_KEY, handoffApi } from '../api/handoff'
import { usePermissions } from '../auth/usePermissions'

const POLL_MS = 20_000

/**
 * A short two-note chime, built in the browser so no audio file ships with the app.
 * Browsers refuse to play sound until the person has clicked or typed on the page,
 * which the login does; after a plain refresh the first chime waits for any click.
 */
function playChime() {
  try {
    const Audio = window.AudioContext ?? (window as unknown as { webkitAudioContext?: typeof AudioContext }).webkitAudioContext
    if (!Audio) return
    const context = new Audio()
    void context.resume()
    const start = context.currentTime
    for (const [index, frequency] of [880, 1174.7].entries()) {
      const at = start + index * 0.18
      const oscillator = context.createOscillator()
      const volume = context.createGain()
      oscillator.type = 'sine'
      oscillator.frequency.value = frequency
      volume.gain.setValueAtTime(0.0001, at)
      volume.gain.exponentialRampToValueAtTime(0.18, at + 0.02)
      volume.gain.exponentialRampToValueAtTime(0.0001, at + 0.3)
      oscillator.connect(volume)
      volume.connect(context.destination)
      oscillator.start(at)
      oscillator.stop(at + 0.32)
    }
    window.setTimeout(() => void context.close(), 1200)
  } catch {
    // A browser that will not play a sound is not an error worth showing.
  }
}

/**
 * Header bell for whoever completes tallies: how many are waiting, refreshed
 * every 20 seconds, with a chime when that number goes up. Everyone else sees
 * nothing, and the count itself comes from a permission-guarded endpoint.
 */
export function KeeperQueueBell() {
  const { can } = usePermissions()
  const navigate = useNavigate()
  const enabled = can('tally.services')

  const { data } = useQuery({
    queryKey: KEEPER_QUEUE_KEY,
    queryFn: handoffApi.keeperQueue,
    enabled,
    refetchInterval: POLL_MS,
    refetchIntervalInBackground: true,
  })

  const waiting = data?.waiting ?? 0
  const previous = useRef<number | null>(null)
  useEffect(() => {
    if (!enabled || data == null) return
    if (previous.current != null && waiting > previous.current) playChime()
    previous.current = waiting
  }, [enabled, data, waiting])

  if (!enabled) return null

  return (
    <Tooltip
      label={waiting > 0
        ? `${waiting.toLocaleString('fa-IR')} سند در انتظار تکمیل`
        : 'سند در انتظار تکمیل ندارید'}
      withArrow
    >
      <Indicator
        label={waiting.toLocaleString('fa-IR')}
        size={18}
        color="orange"
        disabled={waiting === 0}
        offset={4}
      >
        <ActionIcon
          variant="subtle"
          radius="md"
          size="lg"
          aria-label="اسناد در انتظار انباردار"
          onClick={() => navigate('/kartabl?waiting=1')}
        >
          <Bell size={20} />
        </ActionIcon>
      </Indicator>
    </Tooltip>
  )
}
