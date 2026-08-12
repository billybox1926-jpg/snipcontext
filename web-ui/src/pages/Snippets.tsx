import { useState, useEffect } from "react"
import { useSearchParams, useNavigate } from "react-router-dom"
import { useSnippets, useDeleteSnippet } from "../hooks/useSnippets"
import { useSearch } from "../hooks/useSearch"
import SearchBar from "../components/SearchBar"
import SnippetCard from "../components/SnippetCard"

const PAGE_SIZE = 20

type SearchMode = "semantic" | "hybrid" | "keyword"

function TagsFilter({ tags, selected, onToggle }: { tags: string[]; selected: string[]; onToggle: (tag: string) => void }) {
  if (tags.length === 0) return null
  return (
    <div className="flex flex-wrap gap-1.5">
      {tags.map((tag) => {
        const active = selected.includes(tag)
        return (
          <button
            key={tag}
            type="button"
            onClick={() => onToggle(tag)}
            className={`rounded-full border px-2.5 py-0.5 text-xs transition-colors ${
              active
                ? "border-gray-400 bg-gray-700 text-gray-100"
                : "border-gray-700 bg-gray-900/60 text-gray-300 hover:border-gray-500"
            }`}
          >
            {tag}
          </button>
        )
      })}
    </div>
  )
}

export default function Snippets() {
  const [searchParams] = useSearchParams()
  const queryFromUrl = searchParams.get("q") || ""
  const modeFromUrl = (searchParams.get("mode") as SearchMode) || "hybrid"

  const [query, setQuery] = useState(queryFromUrl)
  const [mode, setMode] = useState<SearchMode>(modeFromUrl)
  const [offset, setOffset] = useState(0)
  const [language, setLanguage] = useState("")
  const [tagFilter, setTagFilter] = useState<string[]>([])
  const navigate = useNavigate()
  const deleteMutation = useDeleteSnippet()

  // Keep local state in sync when URL changes (e.g. browser back/forward)
  useEffect(() => {
    setQuery(queryFromUrl)
    setMode(modeFromUrl)
    setOffset(0)
  }, [queryFromUrl, modeFromUrl])

  const browseData = useSnippets({
    offset,
    limit: PAGE_SIZE,
    language: language || undefined,
    tag: tagFilter[0] || undefined,
  })

  const searchData = useSearch(query, mode)

  // Derive available tags from the currently loaded items so we don't need a separate endpoint
  const allTags = [
    ...new Set(
      ((() => {
        const items: Array<{ tags?: string[] }> = []
        const bd = browseData.data
        const sd = searchData.data
        if (bd?.items) items.push(...bd.items as Array<{ tags?: string[] }>)
        if (sd?.items) items.push(...sd.items as Array<{ tags?: string[] }>)
        return items
      })() || []).map((s) => s.tags).flat().filter(Boolean),
    ),
  ].sort()

  const isSearching = query.trim().length > 0
  const items = isSearching ? searchData.data?.items ?? [] : browseData.data?.items ?? []
  const total = isSearching ? searchData.data?.total ?? 0 : browseData.data?.total ?? 0

  const activeTagCount = tagFilter.length

  function handleSearchChange(v: string) {
    setQuery(v)
    setOffset(0)
  }

  function handleModeChange(m: SearchMode) {
    setMode(m)
    setOffset(0)
  }

  function handleTagToggle(tag: string) {
    setTagFilter((prev) =>
      prev.includes(tag) ? prev.filter((t) => t !== tag) : [...prev, tag],
    )
  }

  function clearFilters() {
    setLanguage("")
    setTagFilter([])
  }

  const hasFilters = language || activeTagCount > 0

  return (
    <div className="space-y-5">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <h1 className="text-xl font-semibold">Snippets</h1>
          <button
            type="button"
            onClick={() => navigate("/snippets/new")}
            className="rounded border border-gray-700 px-3 py-1.5 text-sm text-gray-200 hover:border-gray-500"
          >
            + New snippet
          </button>
        </div>
      </div>

      {/* Search + mode */}
      <div className="space-y-3">
        <SearchBar
          value={query}
          onChange={handleSearchChange}
          mode={mode}
          onModeChange={handleModeChange}
        />
        {isSearching && (
          <div className="flex items-center gap-4 text-xs text-gray-400">
            <span>
              {searchData.isLoading
                ? "Searching…"
                : searchData.error
                ? "Search failed — try again"
                : `${searchData.data?.total ?? 0} results`}
            </span>
            {searchData.isFetching && <span className="animate-pulse">·</span>}
          </div>
        )}
      </div>

      {/* Filters */}
      <div className="flex flex-wrap items-center gap-3">
        {/* Language selector */}
        <select
          value={language}
          onChange={(e) => {
            setLanguage(e.target.value)
            setOffset(0)
          }}
          className="rounded border border-gray-700 bg-gray-900 px-2.5 py-1.5 text-xs text-gray-200 focus:border-gray-500 focus:outline-none"
        >
          <option value="">All languages</option>
          {[
            "bash",
            "python",
            "typescript",
            "javascript",
            "rust",
            "go",
            "java",
            "c",
            "cpp",
            "csharp",
            "yaml",
            "toml",
            "json",
            "markdown",
            "sql",
            "dockerfile",
            "html",
            "css",
            "scss",
            "jsx",
            "tsx",
            "unknown",
          ].map((lang) => (
            <option key={lang} value={lang}>
              {lang.charAt(0).toUpperCase() + lang.slice(1)}
            </option>
          ))}
        </select>

        <TagsFilter tags={allTags as string[]} selected={tagFilter} onToggle={handleTagToggle} />

        {hasFilters && (
          <button
            type="button"
            onClick={clearFilters}
            className="text-xs text-gray-400 underline hover:text-gray-200"
          >
            Clear filters
          </button>
        )}
      </div>

      {/* Results */}
      {isSearching && searchData.isError ? (
        <div className="rounded border border-red-900/40 bg-red-950/30 p-6 text-center text-sm text-red-300">
          Search failed. Please check your connection and try again.
        </div>
      ) : items.length === 0 ? (
        <div className="rounded border border-gray-800 bg-gray-900/40 p-8 text-center">
          <div className="text-base font-medium text-gray-300">
            {isSearching
              ? query.trim()
                ? "No snippets match your search"
                : "Enter a search to find snippets"
              : "No snippets yet"}
          </div>
          <p className="mt-1 text-sm text-gray-500">
            {isSearching
              ? "Try a different query or search mode"
              : "Add your first snippet to get started"}
          </p>
        </div>
      ) : (
        <>
          <div className="grid grid-cols-1 gap-3 md:grid-cols-2">
            {items.map((item) => (
              <div key={item.id} className="relative">
                <SnippetCard
                  item={item}
                  onClick={(id) => navigate(`/snippets/${id}`)}
                />
                {isSearching && (
                  <button
                    type="button"
                    onClick={(e) => {
                      e.stopPropagation()
                      const label = item.title?.trim() || "Untitled"
                      if (confirm(`Delete "${label}"? This cannot be undone.`)) {
                        deleteMutation.mutate(item.id, { onError: () => {} })
                      }
                    }}
                    className="absolute top-2 right-2 rounded border border-red-900/50 px-1.5 py-0.5 text-xs text-red-300 opacity-0 group-hover:opacity-100 transition-opacity hover:bg-red-950/40"
                    disabled={deleteMutation.isPending}
                  >
                    {deleteMutation.isPending ? "…" : "Del"}
                  </button>
                )}
              </div>
            ))}
          </div>

          {/* Pagination */}
          {!isSearching && total > items.length && (
            <div className="flex items-center justify-between text-sm">
              <button
                type="button"
                disabled={offset === 0}
                onClick={() => setOffset((o) => Math.max(0, o - PAGE_SIZE))}
                className="rounded border border-gray-700 px-3 py-1 text-gray-300 disabled:opacity-40 hover:border-gray-500"
              >
                Previous
              </button>
              <span className="text-gray-400">
                {offset + 1}–{Math.min(offset + PAGE_SIZE, total)} of {total}
              </span>
              <button
                type="button"
                disabled={offset + PAGE_SIZE >= total}
                onClick={() => setOffset((o) => o + PAGE_SIZE)}
                className="rounded border border-gray-700 px-3 py-1 text-gray-300 disabled:opacity-40 hover:border-gray-500"
              >
                Next
              </button>
            </div>
          )}
        </>
      )}
    </div>
  )
}
