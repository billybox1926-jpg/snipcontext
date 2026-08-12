import { useState } from "react"
import { useNavigate } from "react-router-dom"
import { useTags, useRenameTag, useDeleteTag, useMergeTags, type TagItem } from "../hooks/useTags"
import MergeTagsModal from "../components/MergeTagsModal"

export default function TagsPage() {
  const { data, isLoading, error } = useTags()
  const renameTag = useRenameTag()
  const deleteTag = useDeleteTag()
  const mergeTags = useMergeTags()
  const navigate = useNavigate()

  const [search, setSearch] = useState("")
  const [editing, setEditing] = useState<string | null>(null)
  const [renameValue, setRenameValue] = useState("")
  const [deleting, setDeleting] = useState<string | null>(null)
  const [mergeOpen, setMergeOpen] = useState(false)

  const tags: TagItem[] = data?.items ?? []
  const query = search.trim().toLowerCase()
  const filtered = query
    ? tags.filter((t) => t.name.toLowerCase().includes(query))
    : tags

  function startRename(tag: TagItem) {
    setEditing(tag.name)
    setRenameValue(tag.name)
  }

  function cancelRename() {
    setEditing(null)
    setRenameValue("")
  }

  async function handleRename(oldName: string) {
    if (!renameValue.trim() || renameValue.trim() === oldName) {
      cancelRename()
      return
    }
    try {
      await renameTag.mutateAsync({ tagName: oldName, newName: renameValue.trim() })
    } catch {
      // error handled by mutation
    }
    cancelRename()
  }

  async function handleDelete(tag: TagItem) {
    if (!window.confirm(`Delete tag "${tag.name}" from all ${tag.count} snippet(s)? This cannot be undone.`)) {
      return
    }
    setDeleting(tag.name)
    try {
      await deleteTag.mutateAsync(tag.name)
    } finally {
      setDeleting(null)
    }
  }

  async function handleMerge(sourceTags: string[], destinationTag: string) {
    try {
      await mergeTags.mutateAsync({ sourceTags, destinationTag })
    } finally {
      setMergeOpen(false)
    }
  }

  return (
    <div className="space-y-5">
      <div className="flex items-center justify-between">
        <h1 className="text-xl font-semibold">Tags</h1>
        <span className="text-xs text-gray-400">{tags.length} tags</span>
      </div>

      <div className="flex items-center justify-between">
        <div className="relative">
          <input
            type="text"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Filter tags…"
            className="w-full max-w-xs rounded border border-gray-700 bg-gray-900 px-3 py-2 text-sm text-gray-100 placeholder-gray-500 focus:border-gray-500 focus:outline-none"
          />
        </div>
        <button
          type="button"
          onClick={() => setMergeOpen(true)}
          disabled={mergeTags.isPending}
          className="rounded border border-gray-700 px-3 py-1.5 text-sm text-gray-200 hover:border-gray-500 disabled:opacity-50"
        >
          Merge Tags
        </button>
      </div>

      {error && (
        <div className="rounded border border-red-900/40 bg-red-950/30 p-4 text-sm text-red-300">
          Failed to load tags. Please try again.
        </div>
      )}

      {isLoading && tags.length === 0 && (
        <div className="rounded border border-gray-800 bg-gray-900/40 p-8 text-center text-sm text-gray-400">
          Loading tags…
        </div>
      )}

      {!isLoading && tags.length > 0 && (
        <div className="overflow-x-auto">
          <table className="min-w-full divide-y divide-gray-800">
            <thead className="bg-gray-900/60">
              <tr>
                <th className="px-4 py-2 text-left text-xs font-medium uppercase tracking-wider text-gray-400">Tag</th>
                <th className="px-4 py-2 text-left text-xs font-medium uppercase tracking-wider text-gray-400">Snippets</th>
                <th className="px-4 py-2 text-right text-xs font-medium uppercase tracking-wider text-gray-400">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-800 bg-gray-900/40">
              {filtered.map((tag) => (
                <tr
                  key={tag.name}
                  className="hover:bg-gray-900/80"
                  onClick={() => navigate(`/snippets?tag=${encodeURIComponent(tag.name)}`)}
                >
                  <td className="whitespace-nowrap px-4 py-2">
                    {editing === tag.name ? (
                      <div className="flex items-center gap-2">
                        <input
                          type="text"
                          value={renameValue}
                          onChange={(e) => setRenameValue(e.target.value)}
                          onKeyDown={(e) => {
                            if (e.key === "Enter") handleRename(tag.name)
                            if (e.key === "Escape") cancelRename()
                          }}
                          onBlur={handleRename.bind(null, tag.name)}
                          autoFocus
                          className="w-40 rounded border border-gray-600 bg-gray-800 px-2 py-1 text-sm text-gray-100 focus:border-gray-400 focus:outline-none"
                        />
                        <button
                          type="button"
                          onClick={() => cancelRename()}
                          className="text-xs text-gray-400 hover:text-gray-200"
                        >
                          Cancel
                        </button>
                      </div>
                    ) : (
                      <span className="text-sm text-gray-200">{tag.name}</span>
                    )}
                  </td>
                  <td className="whitespace-nowrap px-4 py-2 text-sm text-gray-400">{tag.count}</td>
                  <td className="whitespace-nowrap px-4 py-2 text-right text-sm">
                    <div className="flex items-center justify-end gap-2">
                      <button
                        type="button"
                        onClick={(e) => {
                          e.stopPropagation()
                          startRename(tag)
                        }}
                        disabled={renameTag.isPending}
                        className="rounded border border-gray-700 px-2 py-1 text-xs text-gray-300 hover:border-gray-500 disabled:opacity-50"
                      >
                        Rename
                      </button>
                      <button
                        type="button"
                        onClick={(e) => {
                          e.stopPropagation()
                          handleDelete(tag)
                        }}
                        disabled={deleting === tag.name || deleteTag.isPending}
                        className="rounded border border-red-900/40 px-2 py-1 text-xs text-red-300 hover:border-red-700 disabled:opacity-50"
                      >
                        {deleting === tag.name ? "…" : "Delete"}
                      </button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      <MergeTagsModal
        open={mergeOpen}
        tags={tags}
        onSubmit={handleMerge}
        onClose={() => setMergeOpen(false)}
      />

      {!isLoading && tags.length === 0 && (
        <div className="rounded border border-gray-800 bg-gray-900/40 p-8 text-center">
          <div className="text-base font-medium text-gray-300">No tags yet</div>
          <p className="mt-1 text-sm text-gray-500">Add tags to your snippets to see them here.</p>
        </div>
      )}

      {!isLoading && query && filtered.length === 0 && (
        <div className="rounded border border-gray-800 bg-gray-900/40 p-8 text-center">
          <div className="text-base font-medium text-gray-300">No tags match "{search}"</div>
          <p className="mt-1 text-sm text-gray-500">Try a different search term.</p>
        </div>
      )}
    </div>
  )
}
