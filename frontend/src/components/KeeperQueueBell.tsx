import { useQuery } from '@tanstack/react-query'
import { ActionIcon, Indicator, Tooltip } from '@mantine/core'
import { useNavigate } from 'react-router-dom'
import { Bell } from 'lucide-react'
import { KEEPER_QUEUE_KEY, handoffApi } from '../api/handoff'
import { usePermissions } from '../auth/usePermissions'

const POLL_MS = 20_000

/** Queue badge for warehouse keepers. Sounds use the independent event feed. */
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
