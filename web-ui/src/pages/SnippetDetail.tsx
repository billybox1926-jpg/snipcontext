import { useSnippet, useUpdateSnippet, useDeleteSnippet } from "../hooks/useSnippets"
import { useParams, useNavigate, Link } from "react-router-dom"
import { useState } from "react"
import SnippetForm from "../components/SnippetForm"

type Values = {
  title: string
  content: string
  description: string
  tags: string[]
  language: string
}

export default function SnippetDetail() {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()
  const { data: snippet, isLoading, error } = useSnippet(id ?? "")
  const updateMutation = useUpdateSnippet(id ?? "")
  const deleteMutation = useDeleteSnippet()

  const [editing, setEditing] = useState(false)
  const [saving, setSaving] = useState(false)
  const [deleteConfirm, setDeleteConfirm] = useState(false)

  // Recreate form when entering edit mode by toggling key
  // (SnippetForm resets its internal state when key changes)

  if (isLoading) {
    return (
      <div className="space-y-4">
        <Link to="/snippets" className="text-sm text-gray-400 hover:text-gray-200">
          ← Back to snippets
        </Link>
        <div className="flex justify-center py-20">
          <div className="h-6 w-6 animate-spin rounded-full border-2 border-gray-700 border-t-gray-400" />
        </div>
      </div>
    )
  }

  if (error || !snippet) {
    return (
      <div className="space-y-4">
        <Link to="/snippets" className="text-sm text-gray-400 hover:text-gray-200">
          ← Back to snippets
        </Link>
        <div className="rounded border border-red-900/40 bg-red-950/30 p-6 text-center">
          <div className="text-base font-medium text-red-300">Snippet not found</div>
          <p className="mt-1 text-sm text-red-400/80">
            This snippet may have been deleted or the ID is incorrect.
          </p>
          <button
            type="button"
            onClick={() => navigate("/snippets")}
            className="mt-4 rounded border border-gray-700 px-3 py-1.5 text-sm text-gray-200 hover:border-gray-500"
          >
            Back to snippets
          </button>
        </div>
      </div>
    )
  }

  async function handleSave(values: Values) {
    if (!values.title.trim()) return
    setSaving(true)
    try {
      await updateMutation.mutateAsync({
        title: values.title,
        content: values.content,
        tags: values.tags,
      })
      setEditing(false)
    } catch {
      // keep editing so user can retry
    } finally {
      setSaving(false)
    }
  }

  async function handleDelete() {
    if (!id) return
    setSaving(true)
    try {
      await deleteMutation.mutateAsync(id)
      navigate("/snippets")
    } catch {
      setSaving(false)
    }
  }

  return (
    <div className="space-y-5">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <Link to="/snippets" className="text-sm text-gray-400 hover:text-gray-200">
            ← Back to snippets
          </Link>
          <span className="text-xs text-gray-500">{editing ? "Editing" : "Viewing"}</span>
        </div>
        <div className="flex items-center gap-2">
          {editing ? (
            <button
              type="button"
              onClick={() => {
                setEditing(false)
              }}
              className="rounded border border-gray-700 px-3 py-1.5 text-sm text-gray-300 hover:border-gray-500"
            >
              Done
            </button>
          ) : (
            <>
              <button
                type="button"
                onClick={() => setEditing(true)}
                className="rounded border border-gray-700 px-3 py-1.5 text-sm text-gray-300 hover:border-gray-500"
              >
                Edit
              </button>
              <button
                type="button"
                onClick={() => setDeleteConfirm(true)}
                className="rounded border border-red-900/50 px-3 py-1.5 text-sm text-red-300 hover:bg-red-950/30"
              >
                Delete
              </button>
            </>
          )}
        </div>
      </div>

      {/* Delete confirmation */}
      {deleteConfirm && (
        <div className="rounded border border-red-900/40 bg-red-950/30 p-4">
          <div className="text-sm font-medium text-red-300">Delete this snippet?</div>
          <p className="mt-1 text-xs text-red-400/80">
            This cannot be undone. The snippet and its version history will be removed.
          </p>
          <div className="mt-3 flex gap-2">
            <button
              type="button"
              onClick={() => setDeleteConfirm(false)}
              className="rounded border border-gray-700 px-3 py-1 text-xs text-gray-300 hover:border-gray-500"
            >
              Cancel
            </button>
            <button
              type="button"
              onClick={handleDelete}
              disabled={saving}
              className="rounded border border-red-700 bg-red-950/50 px-3 py-1 text-xs text-red-200 disabled:opacity-50 hover:bg-red-950"
            >
              {saving ? "Deleting…" : "Delete permanently"}
            </button>
          </div>
        </div>
      )}

      {/* Form */}
      <div className="rounded border border-gray-800 bg-gray-900/60 p-5">
        <SnippetForm
          key={editing ? "edit" : "view"}
          initial={{
            title: snippet.title ?? "",
            content: snippet.content ?? "",
            description: snippet.description ?? "",
            tags: snippet.tags ?? [],
            language: snippet.language ?? "",
          }}
          readonly={!editing}
          onSave={handleSave}
          saving={saving}
          onCancel={editing ? () => setEditing(false) : undefined}
        />

        {/* Timestamps */}
        <div className="mt-4 flex gap-4 text-xs text-gray-500">
          <div>Created {snippet.created_at ? new Date(snippet.created_at).toLocaleString() : "—"}</div>
          <div>Updated {snippet.updated_at ? new Date(snippet.updated_at).toLocaleString() : "—"}</div>
        </div>

        {/* Tags (clickable from view mode) */}
        {snippet.tags && snippet.tags.length > 0 && (
          <div className="mt-4 flex flex-wrap gap-1.5">
            {snippet.tags.map((tag) => (
              <button
                key={tag}
                type="button"
                onClick={() => navigate(`/snippets?tag=${encodeURIComponent(tag)}`)}
                className="rounded-full border border-gray-700 bg-gray-800 px-2.5 py-0.5 text-xs text-gray-200 transition-colors hover:border-gray-400"
              >
                {tag}
              </button>
            ))}
          </div>
        )}
      </div>
    </div>
  )
}
