import { useSnippet, useUpdateSnippet, useDeleteSnippet } from "../hooks/useSnippets"
import { useParams, useNavigate, Link } from "react-router-dom"
import { useState, useEffect, useRef } from "react"

function LanguageSelect({
  value,
  onChange,
  readonly,
}: {
  value: string
  onChange: (v: string) => void
  readonly: boolean
}) {
  const LANGUAGES = [
    "python",
    "javascript",
    "typescript",
    "jsx",
    "tsx",
    "html",
    "css",
    "scss",
    "java",
    "kotlin",
    "go",
    "rust",
    "cpp",
    "c",
    "csharp",
    "php",
    "ruby",
    "swift",
    "sql",
    "shell",
    "bash",
    "powershell",
    "yaml",
    "json",
    "toml",
    "markdown",
    "dockerfile",
    "terraform",
    "unknown",
  ]

  return (
    <select
      value={value}
      onChange={(e) => onChange(e.target.value)}
      disabled={readonly}
      className="rounded border border-gray-700 bg-gray-900 px-2 py-1.5 text-sm text-gray-200 disabled:opacity-50 disabled:cursor-not-allowed focus:border-gray-500 focus:outline-none"
    >
      {LANGUAGES.map((lang) => (
        <option key={lang} value={lang}>
          {lang.charAt(0).toUpperCase() + lang.slice(1)}
        </option>
      ))}
    </select>
  )
}

function TagInput({
  tags,
  onChange,
}: {
  tags: string[]
  onChange: (tags: string[]) => void
}) {
  const [input, setInput] = useState("")

  function addTag() {
    const t = input.trim().toLowerCase()
    if (t && !tags.includes(t)) {
      onChange([...tags, t].sort())
    }
    setInput("")
  }

  function removeTag(tag: string) {
    onChange(tags.filter((t) => t !== tag))
  }

  return (
    <div className="flex flex-wrap gap-1.5">
      {tags.map((tag) => (
        <span
          key={tag}
          className="inline-flex items-center gap-1 rounded-full border border-gray-600 bg-gray-800 px-2 py-0.5 text-xs text-gray-200"
        >
          {tag}
          <button
            type="button"
            onClick={() => removeTag(tag)}
            className="ml-0.5 text-gray-400 hover:text-gray-200"
            aria-label={`Remove tag ${tag}`}
          >
            ×
          </button>
        </span>
      ))}
      <input
        value={input}
        onChange={(e) => setInput(e.target.value)}
        onKeyDown={(e) => {
          if (e.key === "Enter" || e.key === ",") {
            e.preventDefault()
            addTag()
          }
        }}
        placeholder={tags.length === 0 ? "Add a tag…" : ""}
        className="min-w-[8rem] max-w-[14rem] rounded border border-gray-700 bg-gray-900 px-2 py-0.5 text-xs text-gray-200 placeholder-gray-500 focus:border-gray-500 focus:outline-none"
      />
    </div>
  )
}

export default function SnippetDetail() {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()
  const { data: snippet, isLoading, error } = useSnippet(id ?? "")
  const updateMutation = useUpdateSnippet(id ?? "")
  const deleteMutation = useDeleteSnippet()

  const [editing, setEditing] = useState(false)
  const [title, setTitle] = useState("")
  const [content, setContent] = useState("")
  const [description, setDescription] = useState("")
  const [tags, setTags] = useState<string[]>([])
  const [language, setLanguage] = useState("")
  const [saving, setSaving] = useState(false)
  const [deleteConfirm, setDeleteConfirm] = useState(false)
  const contentRef = useRef<HTMLTextAreaElement>(null)

  // Sync local form state when snippet loads or changes
  useEffect(() => {
    if (snippet) {
      setTitle(snippet.title ?? "")
      setContent(snippet.content ?? "")
      setDescription(snippet.description ?? "")
      setTags(snippet.tags ?? [])
      setLanguage(snippet.language ?? "")
    }
  }, [snippet?.id, snippet])

  if (isLoading) {
    return (
      <div className="space-y-4">
        <Link
          to="/snippets"
          className="text-sm text-gray-400 hover:text-gray-200"
        >
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

  const isNew = !id || id === "new"

  async function handleSave() {
    if (!title.trim()) return
    setSaving(true)
    try {
      const updated = await updateMutation.mutateAsync({
        title: title.trim(),
        content: content,
        description: description.trim(),
        tags: tags,
      })
      setEditing(false)
      // Snapshot the updated values so the view reflects server state
      if (updated) {
        setTitle(updated.title ?? title)
        setContent(updated.content ?? content)
        setDescription(updated.description ?? description)
        setTags(updated.tags ?? tags)
      }
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

  function handleCancel() {
    // reload from server to discard edits
    setEditing(false)
  }

  return (
    <div className="space-y-5">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <Link
            to="/snippets"
            className="text-sm text-gray-400 hover:text-gray-200"
          >
            ← Back to snippets
          </Link>
          {editing ? (
            <span className="text-xs text-gray-400">Editing</span>
          ) : (
            <span className="text-xs text-gray-500">Viewing</span>
          )}
        </div>
        <div className="flex items-center gap-2">
          {editing ? (
            <>
              <button
                type="button"
                onClick={handleCancel}
                className="rounded border border-gray-700 px-3 py-1.5 text-sm text-gray-300 hover:border-gray-500"
              >
                Cancel
              </button>
              <button
                type="button"
                onClick={handleSave}
                disabled={saving || !title.trim()}
                className="rounded border border-gray-600 bg-gray-700 px-3 py-1.5 text-sm text-gray-100 disabled:opacity-50 hover:bg-gray-600"
              >
                {saving ? "Saving…" : "Save"}
              </button>
            </>
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
          <div className="text-sm font-medium text-red-300">
            Delete this snippet?
          </div>
          <p className="mt-1 text-xs text-red-400/80">
            This cannot be undone. The snippet and its version history will be
            removed.
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

      {/* Content */}
      <div className="rounded border border-gray-800 bg-gray-900/60 p-5 space-y-4">
        {/* Title + language row */}
        <div className="flex items-center gap-3">
          <div className="flex-1">
            {editing ? (
              <input
                value={title}
                onChange={(e) => setTitle(e.target.value)}
                placeholder="Snippet title"
                className="w-full rounded border border-gray-700 bg-gray-900 px-2 py-1.5 text-lg font-semibold text-gray-100 placeholder-gray-500 focus:border-gray-500 focus:outline-none"
              />
            ) : (
              <h1 className="text-lg font-semibold text-gray-100">
                {title || "Untitled"}
              </h1>
            )}
          </div>
          <div className="shrink-0">
            <LanguageSelect
              value={language}
              onChange={setLanguage}
              readonly={!editing}
            />
          </div>
        </div>

        {/* Description */}
        <div>
          {editing ? (
            <textarea
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              placeholder="What does this snippet do? When should you use it?"
              rows={2}
              className="w-full resize-none rounded border border-gray-700 bg-gray-900 p-2 text-sm text-gray-200 placeholder-gray-500 focus:border-gray-500 focus:outline-none"
            />
          ) : (
            <p className="text-sm text-gray-300">
              {description || <span className="italic text-gray-500">No description</span>}
            </p>
          )}
        </div>

        {/* Tags */}
        <div>
          <div className="text-xs text-gray-500">Tags</div>
          {editing ? (
            <TagInput tags={tags} onChange={setTags} />
          ) : (
            <div className="mt-1 flex flex-wrap gap-1.5">
              {tags.length > 0 ? (
                tags.map((tag) => (
                  <span
                    key={tag}
                    className="rounded-full border border-gray-700 bg-gray-800 px-2 py-0.5 text-xs text-gray-200"
                  >
                    {tag}
                  </span>
                ))
              ) : (
                <span className="text-xs text-gray-500">No tags</span>
              )}
            </div>
          )}
        </div>

        {/* Content editor/preview */}
        <div>
          <div className="text-xs text-gray-500">
            {editing ? "Content" : "Content"}
          </div>
          <textarea
            ref={contentRef}
            value={content}
            onChange={(e) => setContent(e.target.value)}
            disabled={!editing}
            rows={16}
            placeholder="Paste your code here…"
            className={`w-full resize-y rounded border font-mono text-sm leading-relaxed ${
              editing
                ? "border-gray-700 bg-gray-900 p-3 text-gray-100 placeholder-gray-600 focus:border-gray-500 focus:outline-none"
                : "border-transparent bg-gray-900/40 p-3 text-gray-200"
            }`}
          />
        </div>

        {/* Timestamps */}
        <div className="flex gap-4 text-xs text-gray-500">
          <div>Created {snippet.created_at ? new Date(snippet.created_at).toLocaleString() : "—"}</div>
          <div>Updated {snippet.updated_at ? new Date(snippet.updated_at).toLocaleString() : "—"}</div>
        </div>
      </div>
    </div>
  )
}
