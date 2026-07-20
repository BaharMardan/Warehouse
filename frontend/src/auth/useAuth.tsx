import { createContext, useContext, useState, type ReactNode } from 'react'
import { getToken, clearToken } from '../api/client'

interface AuthState {
  isAuthed: boolean
  signIn: () => void
  signOut: () => void
}

const AuthContext = createContext<AuthState | null>(null)

export function AuthProvider({ children }: { children: ReactNode }) {
  const [isAuthed, setIsAuthed] = useState<boolean>(!!getToken())

  const signIn = () => setIsAuthed(true)
  const signOut = () => {
    clearToken()
    setIsAuthed(false)
  }

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