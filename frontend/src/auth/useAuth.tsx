import { createContext, useContext, useEffect, useState, type ReactNode } from 'react'
import { useQueryClient } from '@tanstack/react-query'
import { getToken, clearToken, UNAUTHORIZED_EVENT } from '../api/client'

interface AuthState {
  isAuthed: boolean
  signIn: () => void
  signOut: () => void
}

const AuthContext = createContext<AuthState | null>(null)

export function AuthProvider({ children }: { children: ReactNode }) {
  const queryClient = useQueryClient()
  const [isAuthed, setIsAuthed] = useState<boolean>(!!getToken())

  const signIn = () => {
    // Nothing cached for a previous user may carry into this session.
    queryClient.clear()
    // The router mounts after sign-in; start every new session at the launcher.
    window.history.replaceState(null, '', '/')
    setIsAuthed(true)
  }
  const signOut = () => {
    clearToken()
    setIsAuthed(false)
  }

  // Once logged out, drop every cached response, /auth/me included.
  useEffect(() => {
    if (!isAuthed) queryClient.clear()
  }, [isAuthed, queryClient])

  // Any 401 (expired token, deactivated user) ends the session everywhere.
  useEffect(() => {
    const onUnauthorized = () => setIsAuthed(false)
    window.addEventListener(UNAUTHORIZED_EVENT, onUnauthorized)
    return () => window.removeEventListener(UNAUTHORIZED_EVENT, onUnauthorized)
  }, [])

  return (
    <AuthContext.Provider value={{ isAuthed, signIn, signOut }}>
      {children}
    </AuthContext.Provider>
  )
}

export function useAuth(): AuthState {
  const ctx = useContext(AuthContext)
  if (!ctx) throw new Error('useAuth must be used inside AuthProvider')
  return ctx
}