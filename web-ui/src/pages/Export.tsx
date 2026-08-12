import { useState } from "react"
import { useSnippets } from "../hooks/useSnippets"
import { useExport, type ExportRequest } from "../hooks/useExport"
import { PROVIDERS, type ProviderValue } from "./providers"

type SelectionMode = "all" | "ids" | "query"

export default function ExportPage() {
  const { data: snippetsData } = useSnippets({ limit: 200 })
  const exportMutation = useExport()

  const [mode, setMode] = useState<SelectionMode>("all")
  const [provider, setProvider] = useState<ProviderValue>("generic")
  const [selectedIds, setSelectedIds] = useState<Set<string>>(new Set())
  const [query, setQuery] = useState("")
  const [topK, setTopK] = useState(10)
  const [exporting, setExporting] = useState(false)
  const [result, setResult] = useState<{ content: string; count: number; format: string } | null>(null)
  const [error, setError] = useState<string | null>(null)

  const allItems = snippetsData?.items ?? []

  function toggleId(id: string) {
    setSelectedIds((prev) => {
      const next = new Set(prev)
      if (next.has(id)) next.delete(id)
      else next.add(id)
      return next
    })
  }

  function selectAll() {
    setSelectedIds(new Set(allItems.map((s) => s.id)))
  }

  function clearSelection() {
    setSelectedIds(new Set())
  }

  async function handleExport() {
    setExporting(true)
    setError(null)
    setResult(null)
    try {
      const body: ExportRequest = { provider }
      if (mode === "ids") {
        body.ids = [...selectedIds]
      } else if (mode === "query") {
        body.query = query.trim()
        body.top_k = topK
      }
      const res = await exportMutation.mutateAsync(body)
      setResult({ content: res.content, count: res.snippet_count, format: res.format })
    } catch (err) {
      setError(err instanceof Error ? err.message : "Export failed")
    } finally {
      setExporting(false)
    }
  }

  function copyContent() {
    if (!result) return
    navigator.clipboard.writeText(result.content).catch(() => {})
  }

  function downloadContent() {
    if (!result) return
    const ext = provider === "claude" ? "xml" : provider === "openai" || provider === "ollama" ? "txt" : "md"
    const blob = new Blob([result.content], { type: "text/plain" })
    const url = URL.createObjectURL(blob)
    const a = document.createElement("a")
    a.href = url
    a.download = `snippets.${ext}`
    a.click()
    URL.revokeObjectURL(url)
  }

  const providerDef = PROVIDERS.find((p) => p.value === provider)

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-xl font-semibold">Export</h1>
        <div className="text-xs text-gray-400">
          {allItems.length} snippets available
        </div>
      </div>

      {/* Provider picker */}
      <section className="space-y-2">
        <h2 className="text-sm font-medium text-gray-300">Provider</h2>
        <div className="grid grid-cols-1 gap-2 sm:grid-cols-2 lg:grid-cols-3">
          {PROVIDERS.map((p) => (
            <label
              key={p.value}
              className={`flex cursor-pointer flex-col gap-1 rounded border p-3 transition-colors ${
                provider === p.value
                  ? "border-gray-400 bg-gray-800/60"
                  : "border-gray-800 bg-gray-900/40 hover:border-gray-600"
              }`}
            >
              <div className="flex items-center gap-2">
                <input
                  type="radio"
                  name="provider"
                  value={p.value}
                  checked={provider === p.value}
                  onChange={() => setProvider(p.value)}
                  className="h-4 w-4 border-gray-600 text-gray-100 focus:ring-gray-400"
                />
                <span className="font-medium text-gray-100">{p.label}</span>
              </div>
              <p className="text-xs text-gray-400">{p.description}</p>
              <span className="text-[10px] uppercase tracking-wider text-gray-500">
                {p.format}
              </span>
            </label>
          ))}
        </div>
      </section>

      {/* Selection mode */}
      <section className="space-y-3">
        <h2 className="text-sm font-medium text-gray-300">Snippets to export</h2>
        <div className="flex flex-wrap gap-2">
          {(["all", "ids", "query"] as const).map((m) => (
            <button
              key={m}
              type="button"
              onClick={() => setMode(m)}
              className={`rounded border px-3 py-1.5 text-xs font-medium transition-colors ${
                mode === m
                  ? "border-gray-400 bg-gray-700 text-gray-100"
                  : "border-gray-800 text-gray-400 hover:border-gray-600 hover:text-gray-200"
              }`}
            >
              {m === "all" ? "All snippets" : m === "ids" ? "Specific snippets" : "Search query"}
            </button>
          ))}
        </div>

        {mode === "all" && (
          <div className="rounded border border-gray-800 bg-gray-900/40 p-3 text-sm text-gray-300">
            Exporting all {allItems.length} snippets with the {providerDef?.label} provider.
          </div>
        )}

        {mode === "ids" && (
          <div className="space-y-2">
            <div className="flex items-center justify-between">
              <div className="text-xs text-gray-400">
                {selectedIds.size} selected
                {selectedIds.size > 0 ? ` of ${allItems.length}` : ""}
              </div>
              <div className="flex gap-2">
                <button
                  type="button"
                  onClick={selectAll}
                  className="text-xs text-gray-400 hover:text-gray-200"
                >
                  Select all
                </button>
                <button
                  type="button"
                  onClick={clearSelection}
                  className="text-xs text-gray-400 hover:text-gray-200"
                >
                  Clear
                </button>
              </div>
            </div>
            <div className="max-h-60 overflow-y-auto space-y-1">
              {allItems.map((item) => (
                <label
                  key={item.id}
                  className="flex items-center gap-2 rounded border border-gray-800 px-2 py-1.5 text-xs hover:bg-gray-900/60"
                >
                  <input
                    type="checkbox"
                    checked={selectedIds.has(item.id)}
                    onChange={() => toggleId(item.id)}
                    className="h-3.5 w-3.5 border-gray-600 text-gray-100"
                  />
                  <span className="truncate text-gray-200">{item.title || "Untitled"}</span>
                  <span className="ml-auto shrink-0 text-gray-500">{item.language}</span>
                </label>
              ))}
              {allItems.length === 0 && (
                <div className="text-xs text-gray-500">No snippets available. Add some first.</div>
              )}
            </div>
          </div>
        )}

        {mode === "query" && (
          <div className="space-y-2">
            <input
              type="text"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder="e.g. authentication, retry logic, FastAPI"
              className="w-full rounded border border-gray-700 bg-gray-900 px-3 py-2 text-sm text-gray-100 placeholder-gray-500 focus:border-gray-500 focus:outline-none"
            />
            <div className="flex items-center gap-3">
              <label className="flex items-center gap-1.5 text-xs text-gray-400">
                <span>Top K</span>
                <input
                  type="number"
                  min={1}
                  max={50}
                  value={topK}
                  onChange={(e) => setTopK(Math.min(50, Math.max(1, parseInt(e.target.value) || 10)))}
                  className="rounded border border-gray-700 bg-gray-900 w-16 px-2 py-1 text-xs text-gray-100 focus:border-gray-500 focus:outline-none"
                />
              </label>
              <span className="text-xs text-gray-500">
                Results will be limited to the top {topK} matches.
              </span>
            </div>
          </div>
        )}
      </section>

      {/* Export button */}
      <div className="flex items-center gap-3">
        <button
          type="button"
          onClick={handleExport}
          disabled={exporting || (mode === "ids" && selectedIds.size === 0)}
          className="rounded border border-gray-600 bg-gray-700 px-4 py-2 text-sm font-medium text-gray-100 disabled:opacity-50 hover:bg-gray-600"
        >
          {exporting ? "Exporting…" : "Export"}
        </button>
        {mode === "ids" && selectedIds.size === 0 && (
          <span className="text-xs text-gray-500">Select at least one snippet</span>
        )}
      </div>

      {/* Error */}
      {error && (
        <div className="rounded border border-red-900/40 bg-red-950/30 p-4 text-sm text-red-300">
          {error}
        </div>
      )}

      {/* Result */}
      {result && (
        <section className="space-y-3">
          <div className="flex items-center justify-between">
            <div className="text-sm text-gray-300">
              <strong>{result.count}</strong> snippets exported as{" "}
              <span className="capitalize">{result.format}</span>
            </div>
            <div className="flex gap-2">
              <button
                type="button"
                onClick={copyContent}
                className="rounded border border-gray-700 px-2.5 py-1 text-xs text-gray-300 hover:border-gray-500"
              >
                Copy
              </button>
              <button
                type="button"
                onClick={downloadContent}
                className="rounded border border-gray-700 px-2.5 py-1 text-xs text-gray-300 hover:border-gray-500"
              >
                Download
              </button>
            </div>
          </div>
          <pre className="max-h-96 overflow-auto rounded border border-gray-800 bg-gray-900/60 p-4 text-xs leading-relaxed text-gray-200 font-mono">
            <code>{result.content}</code>
          </pre>
        </section>
      )}
    </div>
  )
}
