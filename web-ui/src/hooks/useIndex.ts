import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { get, post } from '../api/client'

export type IndexStatus = {
  index_type: string
  vector_count: number
  last_rebuild: string | null
  snippet_count: number
}

export function useIndexStatus() {
  return useQuery({
    queryKey: ['index', 'status'],
    queryFn: async () => get<IndexStatus>('/api/index/status'),
  })
}

export function useRebuildIndex() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: async () => post<{ ok: boolean }>('/api/index/rebuild', {}),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['index', 'status'] }),
  })
}
