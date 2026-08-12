import { useMutation, useQueryClient } from '@tanstack/react-query'
import { post } from '../api/client'

export type ExportRequest = {
  provider: string
  ids?: string[]
  query?: string
  top_k?: number
}

export type ExportResponse = {
  format: string
  content: string
  snippet_count: number
}

export function useExport() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: async (body: ExportRequest) =>
      post<ExportResponse>('/api/export', body),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['snippets'] })
      qc.invalidateQueries({ queryKey: ['search'] })
    },
  })
}
