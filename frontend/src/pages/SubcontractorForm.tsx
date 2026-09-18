import { useState } from 'react'
import { Link, useNavigate, useParams } from 'react-router-dom'

import {
  useCreateSubcontractor,
  useSubcontractor,
  useUpdateSubcontractor,
} from '../api/hooks'
import type { SubcontractorInput, Trade } from '../api/types'
import { TRADES, TRADE_LABELS } from '../api/types'
import {
  ErrorNotice,
  Field,
  Spinner,
  inputClass,
  primaryButtonClass,
  secondaryButtonClass,
} from '../components/ui'

const EMPTY: SubcontractorInput = {
  companyName: '',
  abn: '',
  trade: 'GENERAL',
  contactName: '',
  contactEmail: '',
  contactPhone: '',
}

export function SubcontractorForm() {
  const { id } = useParams()
  const isEdit = Boolean(id)
  const existing = useSubcontractor(id ?? '')

  if (isEdit && existing.isPending) return <Spinner label="Loading subcontractor…" />
  if (isEdit && existing.error) return <ErrorNotice error={existing.error} />

  const initial: SubcontractorInput = existing.data
    ? {
        companyName: existing.data.companyName,
        abn: existing.data.abn,
        trade: existing.data.trade,
        contactName: existing.data.contactName,
        contactEmail: existing.data.contactEmail,
        contactPhone: existing.data.contactPhone,
      }
    : EMPTY

  return <Form key={id ?? 'new'} id={id} initial={initial} isEdit={isEdit} />
}

function Form({
  id,
  initial,
  isEdit,
}: {
  id?: string
  initial: SubcontractorInput
  isEdit: boolean
}) {
  const navigate = useNavigate()
  const [values, setValues] = useState(initial)
  const create = useCreateSubcontractor()
  const update = useUpdateSubcontractor(id ?? '')
  const mutation = isEdit ? update : create

  function set<K extends keyof SubcontractorInput>(
    key: K,
    value: SubcontractorInput[K],
  ) {
    setValues((prev) => ({ ...prev, [key]: value }))
  }

  async function handleSubmit(event: React.FormEvent) {
    event.preventDefault()
    const saved = await mutation.mutateAsync({
      ...values,
      abn: values.abn.replace(/\s/g, ''),
    })
    navigate('/subcontractors/' + (id ?? saved.id))
  }

  const cancelTo = isEdit ? '/subcontractors/' + id : '/'

  return (
    <div className="mx-auto max-w-2xl space-y-6">
      <div>
        <Link
          to={cancelTo}
          className="text-sm text-slate-500 underline-offset-2 hover:underline"
        >
          ← Back
        </Link>
        <h1 className="mt-2 text-2xl font-semibold tracking-tight text-slate-900">
          {isEdit ? 'Edit subcontractor' : 'Add subcontractor'}
        </h1>
      </div>

      {mutation.error && <ErrorNotice error={mutation.error} />}

      <form
        onSubmit={handleSubmit}
        className="space-y-5 rounded-xl border border-slate-200 bg-white p-6 shadow-sm"
      >
        <Field label="Company name">
          <input
            required
            className={inputClass}
            value={values.companyName}
            onChange={(e) => set('companyName', e.target.value)}
          />
        </Field>

        <div className="grid gap-5 sm:grid-cols-2">
          <Field label="ABN" hint="11 digits, spaces are fine">
            <input
              required
              inputMode="numeric"
              placeholder="51 824 753 556"
              className={inputClass}
              value={values.abn}
              onChange={(e) => set('abn', e.target.value)}
            />
          </Field>

          <Field label="Trade" hint="Maps to QBCC licence classes">
            <select
              required
              className={inputClass}
              value={values.trade}
              onChange={(e) => set('trade', e.target.value as Trade)}
            >
              {TRADES.map((trade) => (
                <option key={trade} value={trade}>
                  {TRADE_LABELS[trade]}
                </option>
              ))}
            </select>
          </Field>
        </div>

        <Field label="Contact name">
          <input
            required
            className={inputClass}
            value={values.contactName}
            onChange={(e) => set('contactName', e.target.value)}
          />
        </Field>

        <div className="grid gap-5 sm:grid-cols-2">
          <Field label="Contact email">
            <input
              required
              type="email"
              className={inputClass}
              value={values.contactEmail}
              onChange={(e) => set('contactEmail', e.target.value)}
            />
          </Field>

          <Field label="Contact phone">
            <input
              required
              className={inputClass}
              value={values.contactPhone}
              onChange={(e) => set('contactPhone', e.target.value)}
            />
          </Field>
        </div>

        <div className="flex justify-end gap-3 border-t border-slate-100 pt-5">
          <Link to={cancelTo} className={secondaryButtonClass}>
            Cancel
          </Link>
          <button
            type="submit"
            disabled={mutation.isPending}
            className={primaryButtonClass}
          >
            {mutation.isPending ? 'Saving…' : 'Save subcontractor'}
          </button>
        </div>
      </form>
    </div>
  )
}
