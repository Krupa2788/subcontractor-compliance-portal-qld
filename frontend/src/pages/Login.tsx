import { useState } from 'react'

import { useAuth } from '../auth/AuthProvider'
import { ErrorNotice, Field, inputClass, primaryButtonClass } from '../components/ui'

export function Login() {
  const { signIn } = useAuth()
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState<Error | null>(null)
  const [isSubmitting, setIsSubmitting] = useState(false)

  async function handleSubmit(event: React.FormEvent) {
    event.preventDefault()
    setError(null)
    setIsSubmitting(true)
    try {
      await signIn(email, password)
    } catch (err) {
      setError(err instanceof Error ? err : new Error('Could not sign in'))
    } finally {
      setIsSubmitting(false)
    }
  }

  return (
    <div className="flex min-h-screen items-center justify-center bg-slate-50 px-4 py-12">
      <div className="w-full max-w-sm space-y-6">
        <div className="text-center">
          <span className="mx-auto grid size-11 place-items-center rounded-xl bg-slate-900 text-sm font-bold text-white">
            QC
          </span>
          <h1 className="mt-4 text-xl font-semibold tracking-tight text-slate-900">
            Subcontractor Compliance
          </h1>
          <p className="mt-1 text-sm text-slate-500">
            Queensland · sign in to continue
          </p>
        </div>

        {error && <ErrorNotice error={error} />}

        <form
          onSubmit={handleSubmit}
          className="space-y-5 rounded-xl border border-slate-200 bg-white p-6 shadow-sm"
        >
          <Field label="Email">
            <input
              required
              autoFocus
              type="email"
              autoComplete="username"
              className={inputClass}
              value={email}
              onChange={(e) => setEmail(e.target.value)}
            />
          </Field>

          <Field label="Password">
            <input
              required
              type="password"
              autoComplete="current-password"
              className={inputClass}
              value={password}
              onChange={(e) => setPassword(e.target.value)}
            />
          </Field>

          <button
            type="submit"
            disabled={isSubmitting}
            className={primaryButtonClass + ' w-full'}
          >
            {isSubmitting ? 'Signing in…' : 'Sign in'}
          </button>
        </form>

        <p className="text-center text-xs text-slate-400">
          Accounts are issued by a compliance officer.
        </p>
      </div>
    </div>
  )
}
