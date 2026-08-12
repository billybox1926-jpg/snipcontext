import { useState } from "react"

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

function LanguageSelect({
  value,
  onChange,
  readonly,
}: {
  value: string
  onChange: (v: string) => void
  readonly: boolean
}) {
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

type Values = {
  title: string
  content: string
  description: string
  tags: string[]
  language: string
}

type Props = {
  initial: Values
  readonly?: boolean
  onSave: (values: Values) => void
  saving?: boolean
  onCancel?: () => void
}

export default function SnippetForm({ initial, readonly, onSave, saving, onCancel }: Props) {
  const [title, setTitle] = useState(initial.title)
  const [content, setContent] = useState(initial.content)
  const [description, setDescription] = useState(initial.description)
  const [tags, setTags] = useState<string[]>(initial.tags)
  const [language, setLanguage] = useState(initial.language)

  function handleSave() {
    onSave({
      title: title.trim(),
      content,
      description: description.trim(),
      tags,
      language,
    })
  }

  return (
    <div className="space-y-4">
      {/* Title + language row */}
      <div className="flex items-center gap-3">
        <div className="flex-1">
          {readonly ? (
            <h1 className="text-lg font-semibold text-gray-100">
              {title || "Untitled"}
            </h1>
          ) : (
            <input
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              placeholder="Snippet title"
              className="w-full rounded border border-gray-700 bg-gray-900 px-2 py-1.5 text-lg font-semibold text-gray-100 placeholder-gray-500 focus:border-gray-500 focus:outline-none"
            />
          )}
        </div>
        <div className="shrink-0">
          <LanguageSelect value={language} onChange={setLanguage} readonly={readonly} />
        </div>
      </div>

      {/* Description */}
      <div>
        {readonly ? (
          <p className="text-sm text-gray-300">
            {description || <span className="italic text-gray-500">No description</span>}
          </p>
        ) : (
          <textarea
            value={description}
            onChange={(e) => setDescription(e.target.value)}
            placeholder="What does this snippet do? When should you use it?"
            rows={2}
            className="w-full resize-none rounded border border-gray-700 bg-gray-900 p-2 text-sm text-gray-200 placeholder-gray-500 focus:border-gray-500 focus:outline-none"
          />
        )}
      </div>

      {/* Tags */}
      <div>
        <div className="text-xs text-gray-500">Tags</div>
        {readonly ? (
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
        ) : (
          <TagInput tags={tags} onChange={setTags} />
        )}
      </div>

      {/* Content */}
      <div>
        <div className="text-xs text-gray-500">Content</div>
        <textarea
          value={content}
          onChange={(e) => setContent(e.target.value)}
          disabled={readonly}
          rows={16}
          placeholder="Paste your code here…"
          className={`w-full resize-y rounded border font-mono text-sm leading-relaxed ${
            readonly
              ? "border-transparent bg-gray-900/40 p-3 text-gray-200"
              : "border-gray-700 bg-gray-900 p-3 text-gray-100 placeholder-gray-600 focus:border-gray-500 focus:outline-none"
          }`}
        />
      </div>

      {/* Actions */}
      {onCancel && (
        <div className="flex items-center justify-end gap-2 pt-2">
          <button
            type="button"
            onClick={onCancel}
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
        </div>
      )}
    </div>
  )
}
