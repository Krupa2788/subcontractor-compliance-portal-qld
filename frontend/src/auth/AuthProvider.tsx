import { createContext, useCallback, useContext, useEffect, useState } from 'react'
import type { ReactNode } from 'react'

import type { Session } from './cognito'
import { getSession, signIn as cognitoSignIn, signOut as cognitoSignOut } from './cognito'

interface AuthState {
  session: Session | null
  /** True until the stored session has been checked on first load, so the app
   *  does not flash the login screen at an already-signed-in user. */
  isLoading: boolean
  signIn: (email: string, password: string) => Promise<void>
  signOut: () => void
}

const AuthContext = createContext<AuthState | null>(null)

export function AuthProvider({ children }: { children: ReactNode }) {
  const [session, setSession] = useState<Session | null>(null)
  const [isLoading, setIsLoading] = useState(true)

  useEffect(() => {
    getSession()
      .then(setSession)
      .finally(() => setIsLoading(false))
  }, [])

  const signIn = useCallback(async (email: string, password: string) => {
    setSession(await cognitoSignIn(email, password))
  }, [])

  const signOut = useCallback(() => {
    cognitoSignOut()
    setSession(null)
  }, [])

  return (
    <AuthContext.Provider value={{ session, isLoading, signIn, signOut }}>
      {children}
    </AuthContext.Provider>
  )
}

export function useAuth() {
  const context = useContext(AuthContext)
  if (!context) throw new Error('useAuth must be used inside AuthProvider')
  return context
}
