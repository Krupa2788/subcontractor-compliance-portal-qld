import { useCallback, useEffect, useState } from 'react'
import type { ReactNode } from 'react'

import type { Session } from './cognito'
import {
  getSession,
  signIn as cognitoSignIn,
  signOut as cognitoSignOut,
} from './cognito'
import { AuthContext } from './context'

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
