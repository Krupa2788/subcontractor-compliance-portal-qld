// Mirrors the schemas in openapi.yaml. In a larger project these would be
// generated from the spec rather than hand-written.

export const TRADES = [
  'BUILDER',
  'ELECTRICAL',
  'PLUMBING',
  'CARPENTRY',
  'PAINTING',
  'ROOFING',
  'TILING',
  'PLASTERING',
  'CONCRETING',
  'GENERAL',
] as const
export type Trade = (typeof TRADES)[number]

export const DOC_TYPES = [
  'QBCC_LICENCE',
  'PUBLIC_LIABILITY_INSURANCE',
  'WORKERS_COMPENSATION_INSURANCE',
  'WHITE_CARD',
  'PROFESSIONAL_INDEMNITY_INSURANCE',
] as const
export type DocType = (typeof DOC_TYPES)[number]

/** Document types every subcontractor must hold, regardless of trade. */
export const REQUIRED_DOC_TYPES: DocType[] = [
  'QBCC_LICENCE',
  'PUBLIC_LIABILITY_INSURANCE',
  'WORKERS_COMPENSATION_INSURANCE',
  'WHITE_CARD',
]

/** A Queensland White Card does not expire once issued. */
export const NON_EXPIRING_DOC_TYPES: DocType[] = ['WHITE_CARD']

export type ComplianceStatus =
  | 'VALID'
  | 'EXPIRING_SOON'
  | 'EXPIRED'
  | 'MISSING_DOCS'

export type DocumentStatus = 'VALID' | 'EXPIRING_SOON' | 'EXPIRED'

export interface SubcontractorInput {
  companyName: string
  abn: string
  trade: Trade
  contactName: string
  contactEmail: string
  contactPhone: string
}

export interface Subcontractor extends SubcontractorInput {
  id: string
  complianceStatus: ComplianceStatus
  createdAt: string
  updatedAt: string
}

export interface ComplianceDocumentInput {
  docType: DocType
  referenceNumber: string
  issuer: string
  coverAmount: number | null
  issueDate: string
  expirationDate: string | null
  notes: string | null
}

export interface ComplianceDocument extends ComplianceDocumentInput {
  id: string
  subcontractorId: string
  status: DocumentStatus
  createdAt: string
  updatedAt: string
}

export const TRADE_LABELS: Record<Trade, string> = {
  BUILDER: 'Builder',
  ELECTRICAL: 'Electrical',
  PLUMBING: 'Plumbing',
  CARPENTRY: 'Carpentry',
  PAINTING: 'Painting',
  ROOFING: 'Roofing',
  TILING: 'Tiling',
  PLASTERING: 'Plastering',
  CONCRETING: 'Concreting',
  GENERAL: 'General',
}

export const DOC_TYPE_LABELS: Record<DocType, string> = {
  QBCC_LICENCE: 'QBCC Licence',
  PUBLIC_LIABILITY_INSURANCE: 'Public Liability Insurance',
  WORKERS_COMPENSATION_INSURANCE: "Workers' Compensation Insurance",
  WHITE_CARD: 'White Card',
  PROFESSIONAL_INDEMNITY_INSURANCE: 'Professional Indemnity Insurance',
}

export const STATUS_LABELS: Record<ComplianceStatus, string> = {
  VALID: 'Compliant',
  EXPIRING_SOON: 'Expiring soon',
  EXPIRED: 'Expired',
  MISSING_DOCS: 'Missing documents',
}
