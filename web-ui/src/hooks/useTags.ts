import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { get, put, del } from '../api/client'

export type TagItem = { name: string; count: number }

export function useTags() {
  return useQuery({
    queryKey: ['tags'],
    queryFn: async () => get<{ items: TagItem[] }>('/api/tags'),
  })
}

export function useRenameTag() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: async ({ tagName, newName }: { tagName: string; newName: string }) =>
      put<{ ok: boolean; updated: number }>(`/api/tags/${encodeURIComponent(tagName)}`, { new_name: newName }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['tags'] }),
  })
}

export function useDeleteTag() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: async (tagName: string) =>
      del<{ ok: boolean; updated: number }>(`/api/tags/${encodeURIComponent(tagName)}`),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['tags'] }),
  })
}

export function useMergeTags() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: async ({ sourceTags, destinationTag }: { sourceTags: string[]; destinationTag: string }) =>
      post<{ ok: boolean; updated: number }>('/api/tags/merge', { source_tags: sourceTags, destination_tag: destinationTag }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['tags'] }),
  })
}
