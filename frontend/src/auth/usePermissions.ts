import { useCallback, useMemo } from 'react'
import { useQuery } from '@tanstack/react-query'
import { apiGet } from '../api/client'
import type { PermissionCode } from './permissions'

/** GET /auth/me. The backend has already added implied permissions to the list. */
export interface CurrentUser {
  id: number
  username: string
  full_name: string | null
  is_admin: string // 'yes' | 'no'
  permissions: string[]
}

/**
 * The logged-in user. Cached under ['current-user'], the key the print pages
 * already use, so the whole app shares one request. Considered fresh for a
 * minute; after that it refreshes when the window regains focus.
 */
export function useCurrentUser() {
  return useQuery({
    queryKey: ['current-user'],
    queryFn: () => apiGet<CurrentUser>('/auth/me'),
    staleTime: 60_000,
  })
}

/**
 * can('tally.edit') decides what to render. It is a convenience for the user,
 * not a lock: the backend checks the same code on every request.
 */
export function usePermissions() {
  const { data: user } = useCurrentUser()
  const granted = useMemo(() => new Set(user?.permissions ?? []), [user])
  const can = useCallback((code: PermissionCode) => granted.has(code), [granted])
  // Admins already hold every code; this flag gates what no code grants: user management.
  const isAdmin = user?.is_admin === 'yes'
  return { user, can, isAdmin }
}
