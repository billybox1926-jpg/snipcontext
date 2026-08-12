import { useCreateSnippet } from "../hooks/useSnippets"
import { useNavigate } from "react-router-dom"
import { useState } from "react"
import SnippetForm from "../components/SnippetForm"

type Values = {
  title: string
  content: string
  description: string
  tags: string[]
  language: string
}

export default function NewSnippet() {
  const navigate = useNavigate()
  const createMutation = useCreateSnippet()
  const [saving, setSaving] = useState(false)

  function handleSave(values: Values) {
    if (!values.title.trim()) return
    setSaving(true)
    createMutation
      .mutateAsync({
        title: values.title,
        content: values.content,
        language: values.language || undefined,
        tags: values.tags,
      })
      .then((snippet) => {
        setSaving(false)
        navigate(`/snippets/${snippet.id}`)
      })
      .catch(() => {
        setSaving(false)
      })
  }

  return (
    <div className="space-y-5">
      <div className="flex items-center justify-between">
        <h1 className="text-xl font-semibold">New snippet</h1>
        <button
          type="button"
          onClick={() => navigate("/snippets")}
          className="rounded border border-gray-700 px-3 py-1.5 text-sm text-gray-300 hover:border-gray-500"
        >
          Cancel
        </button>
      </div>

      <div className="rounded border border-gray-800 bg-gray-900/60 p-5">
        <SnippetForm
          initial={{
            title: "",
            content: "",
            description: "",
            tags: [],
            language: "",
          }}
          onSave={handleSave}
          saving={saving}
        />
      </div>
    </div>
  )
}
