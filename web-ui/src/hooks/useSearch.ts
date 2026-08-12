import { useQuery } from '@tanstack/react-query'
import { get } from '../api/client'

export type SearchResultItem = {
  id: string
  title: string
  language: string
  tags: string[]
  updated_at: string
  created_at: string
  score: number
}

export function useSearch(q: string, mode = 'hybrid') {
  return useQuery({
    queryKey: ['search', q, mode],
    queryFn: async () => get<{ items: SearchResultItem[]; total: number; query: string; mode: string }>(`/api/search?q=${encodeURIComponent(q)}&mode=${encodeURIComponent(mode)}`),
    enabled: q.trim().length > 0,
  })
}
