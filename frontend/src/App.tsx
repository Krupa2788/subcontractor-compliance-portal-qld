import { Link, Route, Routes } from 'react-router-dom'

import { DocumentForm } from './pages/DocumentForm'
import { SubcontractorDetail } from './pages/SubcontractorDetail'
import { SubcontractorForm } from './pages/SubcontractorForm'
import { SubcontractorsList } from './pages/SubcontractorsList'

export default function App() {
  return (
    <div className="min-h-screen bg-slate-50">
      <header className="border-b border-slate-200 bg-white">
        <div className="mx-auto flex max-w-5xl items-center justify-between px-4 py-4 sm:px-6">
          <Link to="/" className="flex items-center gap-2.5">
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
        </div>
      </header>

      <main className="mx-auto max-w-5xl px-4 py-8 sm:px-6">
        <Routes>
          <Route path="/" element={<SubcontractorsList />} />
          <Route path="/subcontractors/new" element={<SubcontractorForm />} />
          <Route path="/subcontractors/:id" element={<SubcontractorDetail />} />
          <Route path="/subcontractors/:id/edit" element={<SubcontractorForm />} />
          <Route
            path="/subcontractors/:id/documents/new"
            element={<DocumentForm />}
          />
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
                  to="/"
                  className="mt-2 inline-block text-sm text-slate-900 underline underline-offset-2"
                >
                  Back to subcontractors
                </Link>
              </div>
            }
          />
        </Routes>
      </main>
    </div>
  )
}
