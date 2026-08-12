import { SnippetItem } from "../hooks/useSnippets"

type Props = {
  item: SnippetItem
  onClick?: () => void
}

export default function SnippetCard({ item, onClick }: Props) {
  return (
    <div
      onClick={onClick}
      className={`group rounded border border-gray-800 bg-gray-900/60 p-3 transition-colors cursor-default ${
        onClick ? "hover:border-gray-600 hover:bg-gray-900" : ""
      }`}
    >
      <div className="flex items-center justify-between gap-3">
        <div className="min-w-0">
          <div className="truncate font-semibold text-gray-100">
            {item.title || "Untitled"}
          </div>
          <div className="mt-1 flex items-center gap-2 text-xs text-gray-400">
            <span className="capitalize">{item.language || "text"}</span>
            {item.updated_at ? (
              <>
                <span>·</span>
                <time>{item.updated_at}</time>
              </>
            ) : null}
          </div>
        </div>
        <div className="shrink-0 text-xs tabular-nums text-gray-500">
          {item.id.slice(0, 8)}
        </div>
      </div>
      <div className="mt-2 flex flex-wrap gap-1">
        {(item.tags || []).map((tag) => (
          <span
            key={tag}
            className="rounded-full border border-gray-700 bg-gray-800 px-2 py-0.5 text-xs text-gray-200 transition-colors group-hover:border-gray-500"
          >
            {tag}
          </span>
        ))}
        {(!item.tags || item.tags.length === 0) && (
          <span className="rounded-full border border-dashed border-gray-700 px-2 py-0.5 text-xs text-gray-500">
            no tags
          </span>
        )}
      </div>
    </div>
  )
}
