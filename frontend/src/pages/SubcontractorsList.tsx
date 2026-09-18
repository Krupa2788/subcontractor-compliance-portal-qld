import { useMemo, useState } from 'react'
import { Link } from 'react-router-dom'

import { useSubcontractors } from '../api/hooks'
import type { ComplianceStatus, Subcontractor } from '../api/types'
import { STATUS_LABELS, TRADE_LABELS } from '../api/types'
import { StatusBadge } from '../components/StatusBadge'
import {
  EmptyState,
  ErrorNotice,
  Spinner,
  primaryButtonClass,
} from '../components/ui'
import { formatAbn } from '../lib/format'

const FILTERS: Array<{ value: ComplianceStatus | 'ALL'; label: string }> = [
  { value: 'ALL', label: 'All' },
  { value: 'EXPIRED', label: STATUS_LABELS.EXPIRED },
  { value: 'EXPIRING_SOON', label: STATUS_LABELS.EXPIRING_SOON },
  { value: 'MISSING_DOCS', label: STATUS_LABELS.MISSING_DOCS },
  { value: 'VALID', label: STATUS_LABELS.VALID },
]

export function SubcontractorsList() {
  const { data, isPending, error } = useSubcontractors()
  const [filter, setFilter] = useState<ComplianceStatus | 'ALL'>('ALL')

  const counts = useMemo(() => {
    const tally = { EXPIRED: 0, EXPIRING_SOON: 0, MISSING_DOCS: 0, VALID: 0 }
    for (const item of data ?? []) tally[item.complianceStatus] += 1
    return tally
  }, [data])

  const visible = useMemo(
    () =>
      (data ?? [])
        .filter((s) => filter === 'ALL' || s.complianceStatus === filter)
        .sort((a, b) => a.companyName.localeCompare(b.companyName)),
    [data, filter],
  )

  if (isPending) return <Spinner label="Loading subcontractors…" />
  if (error) return <ErrorNotice error={error} />

  const needingAttention = counts.EXPIRED + counts.MISSING_DOCS

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight text-slate-900">
            Subcontractors
          </h1>
          <p className="mt-1 text-sm text-slate-500">
            {data.length} registered
            {needingAttention > 0 && (
              <>
                {' · '}
                <span className="font-medium text-red-700">
                  {needingAttention} needing attention
                </span>
              </>
            )}
          </p>
        </div>
        <Link to="/subcontractors/new" className={primaryButtonClass}>
          Add subcontractor
        </Link>
      </div>

      {data.length === 0 ? (
        <EmptyState
          title="No subcontractors yet"
          description="Add your first subcontractor to start tracking their QBCC licence, insurances and White Card."
          action={
            <Link to="/subcontractors/new" className={primaryButtonClass}>
              Add subcontractor
            </Link>
          }
        />
      ) : (
        <>
          <div className="flex flex-wrap gap-2">
            {FILTERS.map(({ value, label }) => {
              const count =
                value === 'ALL' ? data.length : counts[value as ComplianceStatus]
              const active = filter === value
              return (
                <button
                  key={value}
                  type="button"
                  onClick={() => setFilter(value)}
                  aria-pressed={active}
                  className={`rounded-full px-3 py-1.5 text-sm font-medium transition ${
                    active
                      ? 'bg-slate-900 text-white'
                      : 'bg-white text-slate-600 ring-1 ring-inset ring-slate-200 hover:bg-slate-50'
                  }`}
                >
                  {label}
                  <span
                    className={
                      active ? 'ml-1.5 text-slate-300' : 'ml-1.5 text-slate-400'
                    }
                  >
                    {count}
                  </span>
                </button>
              )
            })}
          </div>

          {visible.length === 0 ? (
            <p className="rounded-xl border border-dashed border-slate-300 bg-white px-4 py-10 text-center text-sm text-slate-500">
              No subcontractors with this status.
            </p>
          ) : (
            <>
              {/* Phones get cards rather than a table: in a table the status
                  column — the whole point of this screen — ends up off the
                  right edge behind a horizontal scroll. */}
              <ul className="space-y-3 sm:hidden">
                {visible.map((s) => (
                  <li key={s.id}>
                    <Link
                      to={'/subcontractors/' + s.id}
                      className="block rounded-xl border border-slate-200 bg-white p-4 shadow-sm"
                    >
                      <div className="flex items-start justify-between gap-3">
                        <span className="font-medium text-slate-900">
                          {s.companyName}
                        </span>
                        <StatusBadge status={s.complianceStatus} />
                      </div>
                      <p className="mt-1 text-sm text-slate-500">
                        {TRADE_LABELS[s.trade]} · ABN {formatAbn(s.abn)}
                      </p>
                      <p className="mt-2 text-sm text-slate-600">
                        {s.contactName}
                        <span className="block text-xs text-slate-400">
                          {s.contactEmail}
                        </span>
                      </p>
                    </Link>
                  </li>
                ))}
              </ul>

              <div className="hidden overflow-hidden rounded-xl border border-slate-200 bg-white shadow-sm sm:block">
                <table className="min-w-full divide-y divide-slate-200 text-sm">
                  <thead className="bg-slate-50">
                    <tr className="text-left text-xs font-semibold tracking-wide text-slate-500 uppercase">
                      <th scope="col" className="px-4 py-3">Company</th>
                      <th scope="col" className="px-4 py-3">Trade</th>
                      <th scope="col" className="px-4 py-3">ABN</th>
                      <th scope="col" className="px-4 py-3">Contact</th>
                      <th scope="col" className="px-4 py-3">Status</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-100">
                    {visible.map((s: Subcontractor) => (
                      <tr key={s.id} className="hover:bg-slate-50">
                        <td className="px-4 py-3">
                          <Link
                            to={'/subcontractors/' + s.id}
                            className="font-medium text-slate-900 underline-offset-2 hover:underline"
                          >
                            {s.companyName}
                          </Link>
                        </td>
                        <td className="px-4 py-3 text-slate-600">
                          {TRADE_LABELS[s.trade]}
                        </td>
                        <td className="px-4 py-3 font-mono text-xs whitespace-nowrap text-slate-500">
                          {formatAbn(s.abn)}
                        </td>
                        <td className="px-4 py-3 text-slate-600">
                          <div>{s.contactName}</div>
                          <div className="text-xs text-slate-400">
                            {s.contactEmail}
                          </div>
                        </td>
                        <td className="px-4 py-3">
                          <StatusBadge status={s.complianceStatus} />
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </>
          )}
        </>
      )}
    </div>
  )
}
