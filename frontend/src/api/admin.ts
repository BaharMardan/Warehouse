import { apiGet, apiSend } from './client'
import type { PermissionCode } from '../auth/permissions'

/** Calls behind «مدیریت کاربران». Every endpoint is admin-only on the server. */

export type YesNo = 'yes' | 'no'

export interface PermissionInfo {
  code: PermissionCode
  label: string
  module: string // key of the owning module in modules.tsx
  implies: PermissionCode[]
}

export interface RoleRow {
  id: number
  title: string
  description: string | null
  permissions: PermissionCode[]
  user_count: number
}

export interface RoleInput {
  title: string
  description: string | null
  permissions: PermissionCode[]
}

export interface UserRow {
  id: number
  username: string
  full_name: string | null
  is_admin: YesNo
  is_active: YesNo
  roles: { id: number; title: string }[]
}

export interface UserUpdateInput {
  full_name: string | null
  is_admin: YesNo
  is_active: YesNo
  role_ids: number[]
}

export interface UserCreateInput extends UserUpdateInput {
  username: string
  password: string
}

export const adminKeys = {
  permissions: ['admin-permissions'],
  roles: ['admin-roles'],
  users: ['admin-users'],
} as const

export const adminApi = {
  permissions: () => apiGet<PermissionInfo[]>('/admin/permissions'),
  roles: () => apiGet<RoleRow[]>('/admin/roles'),
  createRole: (body: RoleInput) => apiSend<RoleRow>('/admin/roles', 'POST', body),
  updateRole: (id: number, body: RoleInput) => apiSend<RoleRow>(`/admin/roles/${id}`, 'PUT', body),
  deleteRole: (id: number) => apiSend<void>(`/admin/roles/${id}`, 'DELETE'),
  users: () => apiGet<UserRow[]>('/admin/users'),
  createUser: (body: UserCreateInput) => apiSend<UserRow>('/admin/users', 'POST', body),
  updateUser: (id: number, body: UserUpdateInput) => apiSend<UserRow>(`/admin/users/${id}`, 'PUT', body),
  setPassword: (id: number, password: string) =>
    apiSend<void>(`/admin/users/${id}/password`, 'PUT', { password }),
}

/** The server's Persian `detail`, which apiSend embeds as JSON at the end of its message. */
export { errorMessage } from './client'
