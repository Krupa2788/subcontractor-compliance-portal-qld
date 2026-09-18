import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'

import { api } from './client'
import type { ComplianceDocumentInput, SubcontractorInput } from './types'

export const queryKeys = {
  subcontractors: ['subcontractors'] as const,
  subcontractor: (id: string) => ['subcontractors', id] as const,
  documents: (subcontractorId: string) =>
    ['subcontractors', subcontractorId, 'documents'] as const,
}

export function useSubcontractors() {
  return useQuery({
    queryKey: queryKeys.subcontractors,
    queryFn: api.listSubcontractors,
  })
}

export function useSubcontractor(id: string) {
  return useQuery({
    queryKey: queryKeys.subcontractor(id),
    queryFn: () => api.getSubcontractor(id),
    enabled: Boolean(id),
  })
}

export function useDocuments(subcontractorId: string) {
  return useQuery({
    queryKey: queryKeys.documents(subcontractorId),
    queryFn: () => api.listDocuments(subcontractorId),
    enabled: Boolean(subcontractorId),
  })
}

export function useCreateSubcontractor() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (input: SubcontractorInput) => api.createSubcontractor(input),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: queryKeys.subcontractors })
    },
  })
}

export function useUpdateSubcontractor(id: string) {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (input: SubcontractorInput) => api.updateSubcontractor(id, input),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: queryKeys.subcontractors })
    },
  })
}

export function useDeleteSubcontractor() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (id: string) => api.deleteSubcontractor(id),
    onSuccess: () => {
      // Only the list, and only exactly: the detail page is still mounted at
      // this point, so touching its queries — invalidating or removing them —
      // makes its observers refetch a record that no longer exists, firing a
      // guaranteed 404 on the way out. Left alone, they simply unmount.
      queryClient.invalidateQueries({
        queryKey: queryKeys.subcontractors,
        exact: true,
      })
    },
  })
}

/** Writing a document re-derives the subcontractor's stored complianceStatus
 *  server-side, so the subcontractor queries are stale too — not just the
 *  document list. Invalidating the shared ['subcontractors'] prefix covers
 *  the list, the detail record, and the documents beneath it. */
function useDocumentMutation<TInput>(
  subcontractorId: string,
  mutationFn: (input: TInput) => Promise<unknown>,
) {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: queryKeys.subcontractors })
      queryClient.invalidateQueries({
        queryKey: queryKeys.documents(subcontractorId),
      })
    },
  })
}

export function useCreateDocument(subcontractorId: string) {
  return useDocumentMutation<ComplianceDocumentInput>(
    subcontractorId,
    (input) => api.createDocument(subcontractorId, input),
  )
}

export function useUpdateDocument(subcontractorId: string, documentId: string) {
  return useDocumentMutation<ComplianceDocumentInput>(
    subcontractorId,
    (input) => api.updateDocument(documentId, input),
  )
}

export function useDeleteDocument(subcontractorId: string) {
  return useDocumentMutation<string>(subcontractorId, (documentId) =>
    api.deleteDocument(documentId),
  )
}
