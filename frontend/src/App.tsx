import { Link, Navigate, Route, Routes } from 'react-router-dom'

import { useAuth } from './auth/AuthProvider'
import { Spinner, secondaryButtonClass } from './components/ui'
import { DocumentForm } from './pages/DocumentForm'
import { Login } from './pages/Login'
import { SubcontractorDetail } from './pages/SubcontractorDetail'
import { SubcontractorForm } from './pages/SubcontractorForm'
import { SubcontractorsList } from './pages/SubcontractorsList'

const ROLE_LABELS = {
  ComplianceOfficer: 'Compliance officer',
  Subcontractor: 'Subcontractor',
  Unknown: 'No role assigned',
} as const

export default function App() {
  const { session, isLoading, signOut } = useAuth()

  if (isLoading) return <Spinner label="Checking your session…" />
  if (!session) return <Login />

  // A login with no group has been created but not granted anything. Say so
  // plainly rather than showing an app whose every request will 403.
  if (session.role === 'Unknown') {
    return (
      <NoticeScreen
        title="Your account has no role yet"
        body="A compliance officer needs to add you to a group before you can use the portal."
        onSignOut={signOut}
      />
    )
  }

  // The binding between a subcontractor login and its record lives in the JWT.
  // Without it there is nothing for them to open.
  if (session.role === 'Subcontractor' && !session.subcontractorId) {
    return (
      <NoticeScreen
        title="Your account is not linked to a subcontractor"
        body="A compliance officer needs to link this login to a subcontractor record."
        onSignOut={signOut}
      />
    )
  }

  const isOfficer = session.role === 'ComplianceOfficer'
  const home = isOfficer ? '/' : `/subcontractors/${session.subcontractorId}`

  return (
    <div className="min-h-screen bg-slate-50">
      <header className="border-b border-slate-200 bg-white">
        <div className="mx-auto flex max-w-5xl flex-wrap items-center justify-between gap-3 px-4 py-4 sm:px-6">
          <Link to={home} className="flex items-center gap-2.5">
            <span className="grid size-8 place-items-center rounded-lg bg-slate-900 text-sm font-bold text-white">
              QC
            </span>
            <span className="leading-tight">
              <span className="block text-sm font-semibold text-slate-900">
                Subcontractor Compliance
              </span>
              <span className="block text-xs text-slate-500">Queensland</span>
            </span>
          </Link>

          <div className="flex items-center gap-3">
            <span className="hidden text-right leading-tight sm:block">
              <span className="block text-sm text-slate-700">{session.email}</span>
              <span className="block text-xs text-slate-500">
                {ROLE_LABELS[session.role]}
              </span>
            </span>
            <button type="button" onClick={signOut} className={secondaryButtonClass}>
              Sign out
            </button>
          </div>
        </div>
      </header>

      <main className="mx-auto max-w-5xl px-4 py-8 sm:px-6">
        <Routes>
          {/* Only an officer has a list to look at; a subcontractor is sent
              straight to the one record they own. */}
          <Route
            path="/"
            element={
              isOfficer ? <SubcontractorsList /> : <Navigate to={home} replace />
            }
          />
          <Route
            path="/subcontractors/new"
            element={isOfficer ? <SubcontractorForm /> : <Navigate to={home} replace />}
          />
          <Route path="/subcontractors/:id" element={<SubcontractorDetail />} />
          <Route path="/subcontractors/:id/edit" element={<SubcontractorForm />} />
          <Route path="/subcontractors/:id/documents/new" element={<DocumentForm />} />
          <Route
            path="/subcontractors/:id/documents/:documentId/edit"
            element={<DocumentForm />}
          />
          <Route
            path="*"
            element={
              <div className="py-16 text-center">
                <p className="text-sm text-slate-500">Page not found.</p>
                <Link
                  to={home}
                  className="mt-2 inline-block text-sm text-slate-900 underline underline-offset-2"
                >
                  Back
                </Link>
              </div>
            }
          />
        </Routes>
      </main>
    </div>
  )
}

function NoticeScreen({
  title,
  body,
  onSignOut,
}: {
  title: string
  body: string
  onSignOut: () => void
}) {
  return (
    <div className="flex min-h-screen items-center justify-center bg-slate-50 px-4">
      <div className="max-w-sm rounded-xl border border-slate-200 bg-white p-6 text-center shadow-sm">
        <h1 className="text-base font-semibold text-slate-900">{title}</h1>
        <p className="mt-2 text-sm text-slate-500">{body}</p>
        <button
          type="button"
          onClick={onSignOut}
          className={secondaryButtonClass + ' mt-5'}
        >
          Sign out
        </button>
      </div>
    </div>
  )
}
