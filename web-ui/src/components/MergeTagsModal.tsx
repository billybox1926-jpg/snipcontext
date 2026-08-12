import { useCallback, useEffect, useMemo, useState } from "react"

type MergeTagsModalProps = {
  open: boolean
  tags: { name: string; count: number }[]
  onSubmit: (sourceTags: string[], destinationTag: string) => void
  onClose: () => void
}

export default function MergeTagsModal({ open, tags, onSubmit, onClose }: MergeTagsModalProps) {
  const [source, setSource] = useState<string[]>([])
  const [destination, setDestination] = useState("")
  const [error, setError] = useState<string | null>(null)

  const sorted = useMemo(() => [...tags].sort((a, b) => a.name.localeCompare(b.name)), [tags])

  useEffect(() => {
    if (!open) return
    setSource([])
    setDestination("")
    setError(null)
  }, [open])

  const toggle = useCallback((name: string) => {
    setSource((prev) => (prev.includes(name) ? prev.filter((x) => x !== name) : [...prev, name]))
  }, [])

  function submit(e: React.FormEvent) {
    e.preventDefault()
    if (source.length === 0 || !destination.trim()) {
      setError("Select at least one source tag and a destination tag.")
      return
    }
    if (source.includes(destination.trim())) {
      setError("Destination tag cannot also be a source tag.")
      return
    }
    onSubmit(source, destination.trim())
  }

  if (!open) return null

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60">
      <div className="w-full max-w-lg rounded border border-gray-700 bg-gray-900 p-4">
        <div className="mb-3 flex items-center justify-between">
          <h2 className="text-lg font-semibold text-gray-100">Merge Tags</h2>
          <button type="button" onClick={onClose} className="text-sm text-gray-400 hover:text-gray-200">
            Close
          </button>
        </div>
        <form onSubmit={submit} className="space-y-3">
          <div>
            <div className="mb-1 text-xs uppercase tracking-wider text-gray-400">Source Tags</div>
            <div className="max-h-56 overflow-y-auto rounded border border-gray-800 bg-gray-950 p-2">
              {sorted.length === 0 && (
                <div className="p-3 text-sm text-gray-500">No tags available.</div>
              )}
              {sorted.map((tag) => (
                <label key={tag.name} className="flex cursor-pointer items-center gap-2 rounded px-2 py-1 hover:bg-gray-900">
                  <input
                    type="checkbox"
                    checked={source.includes(tag.name)}
                    onChange={() => toggle(tag.name)}
                  />
                  <span className="flex-1 text-sm text-gray-200">{tag.name}</span>
                  <span className="text-xs text-gray-500">{tag.count}</span>
                </label>
              ))}
            </div>
          </div>
          <div>
            <label className="mb-1 block text-xs uppercase tracking-wider text-gray-400">Destination Tag</label>
            <input
              type="text"
              value={destination}
              onChange={(e) => setDestination(e.target.value)}
              placeholder="Enter destination tag name"
              className="w-full rounded border border-gray-700 bg-gray-800 px-3 py-2 text-sm text-gray-100 placeholder-gray-500 focus:border-gray-400 focus:outline-none"
            />
          </div>
          {error && <div className="text-sm text-red-300">{error}</div>}
          <div className="flex items-center justify-end gap-2">
            <button type="button" onClick={onClose} className="rounded border border-gray-700 px-3 py-1.5 text-sm text-gray-300 hover:border-gray-500">
              Cancel
            </button>
            <button type="submit" className="rounded border border-gray-600 bg-gray-800 px-3 py-1.5 text-sm text-gray-100 hover:border-gray-400">
              Confirm Merge
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}
