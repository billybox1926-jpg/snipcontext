import { SnippetItem } from '../hooks/useSnippets'

export default function SnippetCard({ item }: { item: SnippetItem }) {
  return (
    <div className="rounded border border-gray-800 bg-gray-900/60 p-3">
      <div className="flex items-center justify-between gap-3">
        <div className="min-w-0">
          <div className="truncate font-semibold text-gray-100">{item.title || 'Untitled'}</div>
          <div className="mt-1 text-xs text-gray-400">
            {item.language || ''} {item.updated_at ? `• ${item.updated_at}` : ''}
          </div>
        </div>
        <div className="shrink-0 text-xs text-gray-400">{item.id.slice(0, 8)}</div>
      </div>
      <div className="mt-2 flex flex-wrap gap-1">
        {(item.tags || []).map((tag) => (
          <span key={tag} className="rounded-full border border-gray-700 bg-gray-800 px-2 py-0.5 text-xs text-gray-200">
            {tag}
          </span>
        ))}
      </div>
    </div>
  )
}
