import { useTags } from '../hooks/useTags'

export default function Tags() {
  const { data } = useTags()
  return (
    <div className="space-y-4">
      <h1 className="text-xl font-semibold">Tags</h1>
      <div className="flex flex-wrap gap-2">
        {(data?.items ?? []).map((tag) => (
          <span key={tag.name} className="rounded-full border border-gray-700 bg-gray-900 px-3 py-1 text-sm text-gray-200">
            {tag.name} ({tag.count})
          </span>
        ))}
      </div>
    </div>
  )
}
