import { useState } from 'react'
import { useSnippets } from '../hooks/useSnippets'
import SnippetCard from '../components/SnippetCard'

export default function Snippets() {
  const [offset, setOffset] = useState(0)
  const limit = 20
  const { data } = useSnippets({ offset, limit })

  return (
    <div className="space-y-4">
      <h1 className="text-xl font-semibold">Snippets</h1>
      <div className="grid grid-cols-1 gap-3 md:grid-cols-2">
        {(data?.items ?? []).map((item) => (
          <SnippetCard key={item.id} item={item} />
        ))}
      </div>
      <div className="flex items-center justify-between text-sm text-gray-300">
        <button className="rounded border border-gray-700 px-3 py-1" onClick={() => setOffset((o) => Math.max(0, o - limit))}>Prev</button>
        <div>{offset + 1}-{(offset + limit)} of {data?.total ?? 0}</div>
        <button className="rounded border border-gray-700 px-3 py-1" onClick={() => setOffset((o) => o + limit)}>Next</button>
      </div>
    </div>
  )
}
