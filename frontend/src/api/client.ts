import type {
  ComplianceDocument,
  ComplianceDocumentInput,
  Subcontractor,
  SubcontractorInput,
} from './types'

const BASE_URL = import.meta.env.VITE_API_BASE_URL

if (!BASE_URL) {
  throw new Error('VITE_API_BASE_URL is not set — copy .env.example to .env')
}

export class ApiError extends Error {
  status: number

  constructor(message: string, status: number) {
    super(message)
    this.name = 'ApiError'
    this.status = status
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${BASE_URL}${path}`, {
    ...init,
    headers: { 'Content-Type': 'application/json', ...init?.headers },
  })

  if (!response.ok) {
    // The API returns {"message": "..."} for handled errors; fall back to the
    // status text if something upstream (e.g. API Gateway) fails first.
    let message = response.statusText
    try {
      const body = await response.json()
      if (body?.message) message = body.message
    } catch {
      // response had no JSON body
    }
    throw new ApiError(message, response.status)
  }

  return response.status === 204 ? (undefined as T) : response.json()
}

export const api = {
  listSubcontractors: () => request<Subcontractor[]>('/subcontractors'),

  getSubcontractor: (id: string) =>
    request<Subcontractor>(`/subcontractors/${id}`),

  createSubcontractor: (input: SubcontractorInput) =>
    request<Subcontractor>('/subcontractors', {
      method: 'POST',
      body: JSON.stringify(input),
    }),

  updateSubcontractor: (id: string, input: SubcontractorInput) =>
    request<Subcontractor>(`/subcontractors/${id}`, {
      method: 'PUT',
      body: JSON.stringify(input),
    }),

  deleteSubcontractor: (id: string) =>
    request<void>(`/subcontractors/${id}`, { method: 'DELETE' }),

  listDocuments: (subcontractorId: string) =>
    request<ComplianceDocument[]>(`/subcontractors/${subcontractorId}/documents`),

  getDocument: (id: string) => request<ComplianceDocument>(`/documents/${id}`),

  createDocument: (subcontractorId: string, input: ComplianceDocumentInput) =>
    request<ComplianceDocument>(`/subcontractors/${subcontractorId}/documents`, {
      method: 'POST',
      body: JSON.stringify(input),
    }),

  updateDocument: (id: string, input: ComplianceDocumentInput) =>
    request<ComplianceDocument>(`/documents/${id}`, {
      method: 'PUT',
      body: JSON.stringify(input),
    }),

  deleteDocument: (id: string) =>
    request<void>(`/documents/${id}`, { method: 'DELETE' }),
}
