import type { ComplianceStatus, DocumentStatus } from '../api/types'
import { STATUS_LABELS } from '../api/types'

const STYLES: Record<ComplianceStatus, string> = {
  VALID: 'bg-emerald-50 text-emerald-800 ring-emerald-600/20',
  EXPIRING_SOON: 'bg-amber-50 text-amber-900 ring-amber-600/30',
  EXPIRED: 'bg-red-50 text-red-800 ring-red-600/20',
  MISSING_DOCS: 'bg-slate-100 text-slate-700 ring-slate-500/20',
}

const DOTS: Record<ComplianceStatus, string> = {
  VALID: 'bg-emerald-600',
  EXPIRING_SOON: 'bg-amber-500',
  EXPIRED: 'bg-red-600',
  MISSING_DOCS: 'bg-slate-400',
}

interface Props {
  status: ComplianceStatus | DocumentStatus
}

export function StatusBadge({ status }: Props) {
  return (
    <span
      className={`inline-flex items-center gap-1.5 rounded-full px-2.5 py-1 text-xs font-medium ring-1 ring-inset ${STYLES[status]}`}
    >
      {/* Colour alone should never carry the meaning, so the label is always
          spelled out for screen readers and colour-blind users. */}
      <span className={`size-1.5 rounded-full ${DOTS[status]}`} aria-hidden />
      {STATUS_LABELS[status]}
    </span>
  )
}
