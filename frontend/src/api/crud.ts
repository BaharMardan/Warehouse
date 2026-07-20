import { apiGet, apiSend } from './client'

// Build the 4 CRUD calls for any resource path.
export function makeCrudApi<T>(path: string) {
  return {
    list: () => apiGet<T[]>(path),
    create: (data: Record<string, unknown>) => apiSend<T>(path, 'POST', data),
    update: (id: number, data: Record<string, unknown>) => apiSend<T>(`${path}/${id}`, 'PUT', data),
    remove: (id: number) => apiSend<void>(`${path}/${id}`, 'DELETE'),
  }
}
