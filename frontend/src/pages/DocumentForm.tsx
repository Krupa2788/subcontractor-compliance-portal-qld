import { useState } from 'react'
import { Link, useNavigate, useParams } from 'react-router-dom'

import { useCreateDocument, useDocuments, useUpdateDocument } from '../api/hooks'
import type { ComplianceDocumentInput, DocType } from '../api/types'
import {
  DOC_TYPES,
  DOC_TYPE_LABELS,
  NON_EXPIRING_DOC_TYPES,
  REQUIRED_DOC_TYPES,
} from '../api/types'
import {
  ErrorNotice,
  Field,
  Spinner,
  inputClass,
  primaryButtonClass,
  secondaryButtonClass,
} from '../components/ui'

const EMPTY: ComplianceDocumentInput = {
  docType: 'QBCC_LICENCE',
  referenceNumber: '',
  issuer: '',
  coverAmount: null,
  issueDate: '',
  expirationDate: '',
  notes: null,
}

/** Insurance documents are the ones where a cover amount is meaningful. */
const COVER_AMOUNT_TYPES: DocType[] = [
  'PUBLIC_LIABILITY_INSURANCE',
  'WORKERS_COMPENSATION_INSURANCE',
  'PROFESSIONAL_INDEMNITY_INSURANCE',
]

export function DocumentForm() {
  const { id = '', documentId } = useParams()
  const isEdit = Boolean(documentId)
  const documents = useDocuments(id)

  if (isEdit && documents.isPending) return <Spinner label="Loading document…" />
  if (isEdit && documents.error) return <ErrorNotice error={documents.error} />

  const existing = documents.data?.find((d) => d.id === documentId)

  const initial: ComplianceDocumentInput = existing
    ? {
        docType: existing.docType,
        referenceNumber: existing.referenceNumber,
        issuer: existing.issuer,
        coverAmount: existing.coverAmount,
        issueDate: existing.issueDate,
        expirationDate: existing.expirationDate ?? '',
        notes: existing.notes,
      }
    : EMPTY

  return (
    <Form
      key={documentId ?? 'new'}
      subcontractorId={id}
      documentId={documentId}
      initial={initial}
      isEdit={isEdit}
    />
  )
}

function Form({
  subcontractorId,
  documentId,
  initial,
  isEdit,
}: {
  subcontractorId: string
  documentId?: string
  initial: ComplianceDocumentInput
  isEdit: boolean
}) {
  const navigate = useNavigate()
  const [values, setValues] = useState(initial)
  const create = useCreateDocument(subcontractorId)
  const update = useUpdateDocument(subcontractorId, documentId ?? '')
  const mutation = isEdit ? update : create

  // Mirrors the backend rule: a Queensland White Card never expires, so the
  // field is disabled rather than silently ignored on submit.
  const neverExpires = NON_EXPIRING_DOC_TYPES.includes(values.docType)
  const showsCover = COVER_AMOUNT_TYPES.includes(values.docType)

  function set<K extends keyof ComplianceDocumentInput>(
    key: K,
    value: ComplianceDocumentInput[K],
  ) {
    setValues((prev) => ({ ...prev, [key]: value }))
  }

  async function handleSubmit(event: React.FormEvent) {
    event.preventDefault()
    await mutation.mutateAsync({
      ...values,
      expirationDate: neverExpires ? null : values.expirationDate || null,
      coverAmount: showsCover ? values.coverAmount : null,
      notes: values.notes || null,
    })
    navigate('/subcontractors/' + subcontractorId)
  }

  const cancelTo = '/subcontractors/' + subcontractorId

  return (
    <div className="mx-auto max-w-2xl space-y-6">
      <div>
        <Link
          to={cancelTo}
          className="text-sm text-slate-500 underline-offset-2 hover:underline"
        >
          ← Back to subcontractor
        </Link>
        <h1 className="mt-2 text-2xl font-semibold tracking-tight text-slate-900">
          {isEdit ? 'Edit compliance document' : 'Add compliance document'}
        </h1>
      </div>

      {mutation.error && <ErrorNotice error={mutation.error} />}

      <form
        onSubmit={handleSubmit}
        className="space-y-5 rounded-xl border border-slate-200 bg-white p-6 shadow-sm"
      >
        <Field label="Document type">
          <select
            required
            className={inputClass}
            value={values.docType}
            onChange={(e) => set('docType', e.target.value as DocType)}
          >
            {DOC_TYPES.map((docType) => (
              <option key={docType} value={docType}>
                {DOC_TYPE_LABELS[docType]}
                {REQUIRED_DOC_TYPES.includes(docType) ? '' : ' (optional)'}
              </option>
            ))}
          </select>
        </Field>

        <div className="grid gap-5 sm:grid-cols-2">
          <Field label="Reference number" hint="Licence, policy or card number">
            <input
              required
              className={inputClass}
              value={values.referenceNumber}
              onChange={(e) => set('referenceNumber', e.target.value)}
            />
          </Field>

          <Field label="Issuer" hint="e.g. QBCC, WorkCover Queensland, insurer">
            <input
              required
              className={inputClass}
              value={values.issuer}
              onChange={(e) => set('issuer', e.target.value)}
            />
          </Field>
        </div>

        <div className="grid gap-5 sm:grid-cols-2">
          <Field label="Issue date">
            <input
              required
              type="date"
              className={inputClass}
              value={values.issueDate}
              onChange={(e) => set('issueDate', e.target.value)}
            />
          </Field>

          <Field
            label="Expiry date"
            hint={neverExpires ? 'A White Card does not expire once issued' : undefined}
          >
            <input
              type="date"
              required={!neverExpires}
              disabled={neverExpires}
              className={inputClass}
              value={neverExpires ? '' : (values.expirationDate ?? '')}
              onChange={(e) => set('expirationDate', e.target.value)}
            />
          </Field>
        </div>

        {showsCover && (
          <Field label="Cover amount (AUD)" hint="$20,000,000 is the industry standard">
            <input
              type="number"
              min="0"
              step="1000"
              className={inputClass}
              value={values.coverAmount ?? ''}
              onChange={(e) =>
                set('coverAmount', e.target.value === '' ? null : Number(e.target.value))
              }
            />
          </Field>
        )}

        <Field label="Notes">
          <textarea
            rows={3}
            className={inputClass}
            value={values.notes ?? ''}
            onChange={(e) => set('notes', e.target.value)}
          />
        </Field>

        <div className="flex justify-end gap-3 border-t border-slate-100 pt-5">
          <Link to={cancelTo} className={secondaryButtonClass}>
            Cancel
          </Link>
          <button
            type="submit"
            disabled={mutation.isPending}
            className={primaryButtonClass}
          >
            {mutation.isPending ? 'Saving…' : 'Save document'}
          </button>
        </div>
      </form>
    </div>
  )
}
