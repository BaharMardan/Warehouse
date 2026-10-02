import { useQuery } from '@tanstack/react-query'
import { apiGet } from './client'
import { usePermissions } from '../auth/usePermissions'

export type AgingItem = {
  id: number; tally_number: string; unloaded_at: string; age_days: number
  owner_name: string | null; stage: 'abandoned' | 'warning'
  days_remaining: number; token: string; unseen: boolean
}
export type AgingData = {
  items: AgingItem[]; total: number; abandoned_count: number; warning_count: number; has_unseen: boolean
}
export function useAbandoned() {
  const { can, user } = usePermissions()
  return useQuery({
    queryKey: ['abandoned', user?.id],
    queryFn: () => apiGet<AgingData>('/abandoned'),
    enabled: can('abandoned.view'),
    refetchInterval: 30000,
  })
}
