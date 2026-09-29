const API_BASE = import.meta.env.VITE_API_URL

const TOKEN_KEY = 'auth_token'

export function getToken(): string | null {
  return localStorage.getItem(TOKEN_KEY)
}

export function setToken(token: string) {
  localStorage.setItem(TOKEN_KEY, token)
}

export function clearToken() {
  localStorage.removeItem(TOKEN_KEY)
}

function authHeaders(): HeadersInit {
  const token = getToken()
  return token ? { Authorization: `Bearer ${token}` } : {}
}

/** 401: the session is over (expired token, or the user was deactivated). */
export class UnauthorizedError extends Error {
  constructor() {
    super('Unauthorized')
    this.name = 'UnauthorizedError'
  }
}

/** 403: logged in, but no role grants the permission. `message` is the server's Persian text. */
export class ForbiddenError extends Error {
  constructor(message: string) {
    super(message)
    this.name = 'ForbiddenError'
  }
}

/** Both answer the same on every retry. */
export function isAuthError(error: unknown): boolean {
  return error instanceof UnauthorizedError || error instanceof ForbiddenError
}

/** The server's Persian `detail`, however apiSend wrapped it. */
export function errorMessage(error: unknown, fallback: string): string {
  if (error instanceof ForbiddenError) return error.message
  const raw = error instanceof Error ? error.message : ''
  const json = raw.match(/\{[\s\S]*\}$/)
  if (json) {
    try {
      const detail = (JSON.parse(json[0]) as { detail?: unknown }).detail
      if (typeof detail === 'string' && detail.trim() !== '') return detail
    } catch {
      // not JSON: fall back to the generic message
    }
  }
  return fallback
}

/** Fired on every 401; AuthProvider listens and returns the user to the login page. */
export const UNAUTHORIZED_EVENT = 'auth:unauthorized'

async function forbiddenError(res: Response): Promise<ForbiddenError> {
  const fallback = 'دسترسی لازم برای این کار را ندارید'
  const body = (await res.json().catch(() => null)) as { detail?: unknown } | null
  return new ForbiddenError(typeof body?.detail === 'string' ? body.detail : fallback)
}

export async function apiGet<T>(path: string): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    headers: { ...authHeaders() },
  })
  if (res.status === 401) {
    clearToken()
    window.dispatchEvent(new Event(UNAUTHORIZED_EVENT))
    throw new UnauthorizedError()
  }
  if (res.status === 403) throw await forbiddenError(res)
  if (!res.ok) throw new Error(`GET ${path} failed: ${res.status}`)
  return res.json() as Promise<T>
}

// Login sends a form (not JSON) because that's what OAuth2PasswordRequestForm expects.
export async function login(username: string, password: string): Promise<void> {
  const body = new URLSearchParams({ username, password })
  const res = await fetch(`${API_BASE}/auth/login`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
    body,
  })
  if (!res.ok) throw new Error('نام کاربری یا رمز عبور اشتباه است')
  const data = (await res.json()) as { access_token: string }
  setToken(data.access_token)
}

// Multipart upload (e.g. the commodity-catalog Excel). No Content-Type header — the
// browser sets multipart/form-data with the correct boundary itself.
export async function apiUpload<T>(path: string, file: File): Promise<T> {
  const form = new FormData()
  form.append('file', file)
  const res = await fetch(`${API_BASE}${path}`, {
    method: 'POST',
    headers: { ...authHeaders() },
    body: form,
  })
  if (res.status === 401) {
    clearToken()
    window.dispatchEvent(new Event(UNAUTHORIZED_EVENT))
    throw new UnauthorizedError()
  }
  if (res.status === 403) throw await forbiddenError(res)
  if (!res.ok) {
    const detail = await res.text().catch(() => '')
    throw new Error(`Upload ${path} failed: ${res.status} ${detail}`)
  }
  return res.json() as Promise<T>
}

export async function apiSend<T>(
  path: string,
  method: 'POST' | 'PUT' | 'DELETE',
  body?: unknown,
): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    method,
    headers: { 'Content-Type': 'application/json', ...authHeaders() },
    body: body ? JSON.stringify(body) : undefined,
  })
  if (res.status === 401) {
    clearToken()
    window.dispatchEvent(new Event(UNAUTHORIZED_EVENT))
    throw new UnauthorizedError()
  }
  if (res.status === 403) throw await forbiddenError(res)
  if (!res.ok) {
    const detail = await res.text().catch(() => '')
    throw new Error(`${method} ${path} failed: ${res.status} ${detail}`)
  }
  if (res.status === 204) return undefined as T // DELETE returns no body
  return res.json() as Promise<T>
}
/** Download an authenticated attachment without exposing the token in its URL. */
export async function apiDownload(path: string, filename: string): Promise<void> {
  const res = await fetch(`${API_BASE}${path}`, { headers: authHeaders() })
  if (res.status === 401) {
    clearToken()
    window.dispatchEvent(new Event(UNAUTHORIZED_EVENT))
    throw new UnauthorizedError()
  }
  if (res.status === 403) throw await forbiddenError(res)
  if (!res.ok) throw new Error('دریافت فیش ناموفق بود')
  const url = URL.createObjectURL(await res.blob())
  const link = document.createElement('a')
  link.href = url
  link.download = filename
  document.body.appendChild(link)
  link.click()
  link.remove()
  setTimeout(() => URL.revokeObjectURL(url), 1000)
}
