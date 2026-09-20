import { createContext, useContext } from 'react'

import type { Session } from './cognito'

export interface AuthState {
  session: Session | null
  /** True until the stored session has been checked on first load, so the app
   *  does not flash the login screen at an already-signed-in user. */
  isLoading: boolean
  signIn: (email: string, password: string) => Promise<void>
  signOut: () => void
}

// Kept apart from the provider component: a module that exports both a
// component and a hook breaks React Fast Refresh.
export const AuthContext = createContext<AuthState | null>(null)

export function useAuth() {
  const context = useContext(AuthContext)
  if (!context) throw new Error('useAuth must be used inside AuthProvider')
  return context
}
