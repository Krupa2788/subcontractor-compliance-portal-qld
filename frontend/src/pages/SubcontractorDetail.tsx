import { Link, useNavigate, useParams } from 'react-router-dom'

import {
  useDeleteDocument,
  useDeleteSubcontractor,
  useDocuments,
  useSubcontractor,
} from '../api/hooks'
import type { ComplianceDocument, DocType } from '../api/types'
import { DOC_TYPE_LABELS, REQUIRED_DOC_TYPES, TRADE_LABELS } from '../api/types'
import { StatusBadge } from '../components/StatusBadge'
import {
  ErrorNotice,
  Spinner,
  dangerButtonClass,
  primaryButtonClass,
  secondaryButtonClass,
} from '../components/ui'
import { formatAbn, formatCurrency, formatDate } from '../lib/format'

export function SubcontractorDetail() {
  const { id = '' } = useParams()
  const navigate = useNavigate()
  const subcontractor = useSubcontractor(id)
  const documents = useDocuments(id)
  const deleteDocument = useDeleteDocument(id)
  const deleteSubcontractor = useDeleteSubcontractor()

  if (subcontractor.isPending) return <Spinner label="Loading subcontractor…" />
  if (subcontractor.error) return <ErrorNotice error={subcontractor.error} />

  const s = subcontractor.data
  const docs = documents.data ?? []
  const heldTypes = new Set(docs.map((d) => d.docType))
  const missingTypes = REQUIRED_DOC_TYPES.filter((t) => !heldTypes.has(t))

  async function handleDeleteSubcontractor() {
    const confirmed = confirm(
      'Delete ' +
        s.companyName +
        '? This also removes all of their compliance documents.',
    )
    if (!confirmed) return
    await deleteSubcontractor.mutateAsync(id)
    navigate('/')
  }

  return (
    <div className="space-y-6">
      <div>
        <Link
          to="/"
          className="text-sm text-slate-500 underline-offset-2 hover:underline"
        >
          ← All subcontractors
        </Link>
      </div>

      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <div className="flex flex-wrap items-center gap-3">
            <h1 className="text-2xl font-semibold tracking-tight text-slate-900">
              {s.companyName}
            </h1>
            <StatusBadge status={s.complianceStatus} />
          </div>
          <p className="mt-1 text-sm text-slate-500">
            {TRADE_LABELS[s.trade]} · ABN {formatAbn(s.abn)}
          </p>
        </div>
        <div className="flex gap-2">
          <Link
            to={'/subcontractors/' + id + '/edit'}
            aria-label={'Edit ' + s.companyName}
            className={secondaryButtonClass}
          >
            Edit
          </Link>
          <button
            type="button"
            onClick={handleDeleteSubcontractor}
            disabled={deleteSubcontractor.isPending}
            aria-label={'Delete ' + s.companyName}
            className={dangerButtonClass}
          >
            Delete
          </button>
        </div>
      </div>

      {deleteSubcontractor.error && (
        <ErrorNotice error={deleteSubcontractor.error} />
      )}

      <dl className="grid gap-4 rounded-xl border border-slate-200 bg-white p-5 shadow-sm sm:grid-cols-3">
        <div>
          <dt className="text-xs font-medium tracking-wide text-slate-500 uppercase">
            Contact
          </dt>
          <dd className="mt-1 text-sm text-slate-900">{s.contactName}</dd>
        </div>
        <div>
          <dt className="text-xs font-medium tracking-wide text-slate-500 uppercase">
            Email
          </dt>
          <dd className="mt-1 text-sm text-slate-900">{s.contactEmail}</dd>
        </div>
        <div>
          <dt className="text-xs font-medium tracking-wide text-slate-500 uppercase">
            Phone
          </dt>
          <dd className="mt-1 text-sm text-slate-900">{s.contactPhone}</dd>
        </div>
      </dl>

      {missingTypes.length > 0 && (
        <div
          role="alert"
          className="rounded-xl border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-900"
        >
          <span className="font-medium">Missing required documents: </span>
          {missingTypes.map((t: DocType) => DOC_TYPE_LABELS[t]).join(', ')}
        </div>
      )}

      <div className="flex flex-wrap items-end justify-between gap-4">
        <h2 className="text-lg font-semibold text-slate-900">
          Compliance documents
          <span className="ml-2 text-sm font-normal text-slate-500">
            {docs.length}
          </span>
        </h2>
        <Link
          to={'/subcontractors/' + id + '/documents/new'}
          className={primaryButtonClass}
        >
          Add document
        </Link>
      </div>

      {documents.isPending ? (
        <Spinner label="Loading documents…" />
      ) : documents.error ? (
        <ErrorNotice error={documents.error} />
      ) : docs.length === 0 ? (
        <p className="rounded-xl border border-dashed border-slate-300 bg-white px-6 py-12 text-center text-sm text-slate-500">
          No documents on file yet.
        </p>
      ) : (
        <ul className="space-y-3">
          {[...docs]
            .sort((a, b) => a.docType.localeCompare(b.docType))
            .map((doc: ComplianceDocument) => (
              <li
                key={doc.id}
                className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm"
              >
                <div className="flex flex-wrap items-start justify-between gap-3">
                  <div>
                    <div className="flex flex-wrap items-center gap-2">
                      <h3 className="font-medium text-slate-900">
                        {DOC_TYPE_LABELS[doc.docType]}
                      </h3>
                      <StatusBadge status={doc.status} />
                      {!REQUIRED_DOC_TYPES.includes(doc.docType) && (
                        <span className="rounded bg-slate-100 px-1.5 py-0.5 text-xs text-slate-500">
                          Optional
                        </span>
                      )}
                    </div>
                    <p className="mt-1 text-sm text-slate-500">
                      {doc.referenceNumber} · {doc.issuer}
                    </p>
                  </div>
                  <div className="flex gap-2">
                    <Link
                      to={
                        '/subcontractors/' +
                        id +
                        '/documents/' +
                        doc.id +
                        '/edit'
                      }
                      aria-label={'Edit ' + DOC_TYPE_LABELS[doc.docType]}
                      className={secondaryButtonClass}
                    >
                      Edit
                    </Link>
                    <button
                      type="button"
                      onClick={() => {
                        const label = DOC_TYPE_LABELS[doc.docType]
                        if (confirm('Delete this ' + label + '?')) {
                          deleteDocument.mutate(doc.id)
                        }
                      }}
                      disabled={deleteDocument.isPending}
                      aria-label={'Delete ' + DOC_TYPE_LABELS[doc.docType]}
                      className={dangerButtonClass}
                    >
                      Delete
                    </button>
                  </div>
                </div>

                <dl className="mt-3 grid gap-3 border-t border-slate-100 pt-3 text-sm sm:grid-cols-3">
                  <div>
                    <dt className="text-xs text-slate-500">Issued</dt>
                    <dd className="text-slate-900">{formatDate(doc.issueDate)}</dd>
                  </div>
                  <div>
                    <dt className="text-xs text-slate-500">Expires</dt>
                    <dd className="text-slate-900">
                      {doc.expirationDate ? (
                        formatDate(doc.expirationDate)
                      ) : (
                        <span className="text-slate-500">Does not expire</span>
                      )}
                    </dd>
                  </div>
                  <div>
                    <dt className="text-xs text-slate-500">Cover</dt>
                    <dd className="text-slate-900">
                      {formatCurrency(doc.coverAmount)}
                    </dd>
                  </div>
                </dl>

                {doc.notes && (
                  <p className="mt-3 border-t border-slate-100 pt-3 text-sm text-slate-600">
                    {doc.notes}
                  </p>
                )}
              </li>
            ))}
        </ul>
      )}

      {deleteDocument.error && <ErrorNotice error={deleteDocument.error} />}
    </div>
  )
}
