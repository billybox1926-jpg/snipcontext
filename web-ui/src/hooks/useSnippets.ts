import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { get, post, put, del } from '../api/client'

export type SnippetItem = {
  id: string
  title: string
  language: string
  tags: string[]
  updated_at: string
  created_at: string
}

export type SnippetDetail = {
  id: string
  title: string
  content: string
  language: string
  tags: string[]
  description: string
  created_at: string
  updated_at: string
  deleted: boolean
  metadata: Record<string, unknown>
}

export function useSnippets(params: { offset?: number; limit?: number; language?: string; tag?: string }) {
  return useQuery({
    queryKey: ['snippets', params],
    queryFn: async () => get<{ items: SnippetItem[]; total: number }>(`/api/snippets?${new URLSearchParams(params as Record<string, string>).toString()}`),
  })
}

export function useSnippet(id: string) {
  return useQuery({
    queryKey: ['snippet', id],
    queryFn: async () => get<SnippetDetail>(`/api/snippets/${encodeURIComponent(id)}`),
    enabled: !!id,
  })
}

export function useCreateSnippet() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: async (body: { title: string; content: string; language?: string; tags?: string[] }) =>
      post<SnippetDetail>('/api/snippets', body),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['snippets'] }),
  })
}

export function useUpdateSnippet(id: string) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: async (body: { title?: string; content?: string; language?: string; tags?: string[] }) =>
      put<SnippetDetail>(`/api/snippets/${encodeURIComponent(id)}`, body),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['snippet', id] }),
  })
}

export function useDeleteSnippet() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: async (id: string) => del<{ ok: boolean }>(`/api/snippets/${encodeURIComponent(id)}`),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['snippets'] }),
  })
}
