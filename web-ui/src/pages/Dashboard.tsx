import { useIndexStatus, useSnippets } from '../hooks/useSnippets'
import SearchBar from '../components/SearchBar'
import SnippetCard from '../components/SnippetCard'

export default function Dashboard() {
  const { data: index } = useIndexStatus()
  const { data: snippets } = useSnippets({ limit: 10 })

  return (
    <div className="space-y-6">
      <h1 className="text-xl font-semibold">Dashboard</h1>
      <div className="grid grid-cols-1 gap-4 md:grid-cols-3">
        <div className="rounded border border-gray-800 bg-gray-900/60 p-4">
          <div className="text-xs text-gray-400">Index</div>
          <div className="text-lg font-semibold">{index?.index_type ?? '--'}</div>
        </div>
        <div className="rounded border border-gray-800 bg-gray-900/60 p-4">
          <div className="text-xs text-gray-400">Vectors</div>
          <div className="text-lg font-semibold">{index?.vector_count ?? '--'}</div>
        </div>
        <div className="rounded border border-gray-800 bg-gray-900/60 p-4">
          <div className="text-xs text-gray-400">Snippets</div>
          <div className="text-lg font-semibold">{index?.snippet_count ?? '--'}</div>
        </div>
      </div>
      <div className="space-y-3">
        <h2 className="text-lg font-semibold">Recent</h2>
        <SearchBar value="" onChange={() => {}} />
        <div className="grid grid-cols-1 gap-3 md:grid-cols-2">
          {(snippets?.items ?? []).slice(0, 8).map((item) => (
            <SnippetCard key={item.id} item={item} />
          ))}
        </div>
      </div>
    </div>
  )
}
