import { useState } from "react"

type Props = {
  value: string
  onChange: (value: string) => void
  mode: "semantic" | "hybrid" | "keyword"
  onModeChange: (mode: "semantic" | "hybrid" | "keyword") => void
  disabled?: boolean
}

const MODES: { value: "semantic" | "hybrid" | "keyword"; label: string }[] = [
  { value: "hybrid", label: "Hybrid" },
  { value: "semantic", label: "Semantic" },
  { value: "keyword", label: "Keyword" },
]

export default function SearchBar({ value, onChange, mode, onModeChange, disabled }: Props) {
  return (
    <div className="flex gap-2">
      <input
        value={value}
        onChange={(e) => onChange(e.target.value)}
        placeholder="Search snippets…"
        disabled={disabled}
        className="flex-1 rounded border border-gray-700 bg-gray-900 p-2 text-gray-100 placeholder-gray-500 focus:border-gray-500 focus:outline-none"
      />
      <div className="shrink-0 flex rounded border border-gray-700 bg-gray-900 p-0.5">
        {MODES.map((m) => (
          <button
            key={m.value}
            type="button"
            disabled={disabled}
            onClick={() => onModeChange(m.value)}
            className={`rounded px-2.5 py-1.5 text-xs font-medium transition-colors ${
              mode === m.value
                ? "bg-gray-700 text-white"
                : "text-gray-400 hover:text-gray-200"
            }`}
          >
            {m.label}
          </button>
        ))}
      </div>
    </div>
  )
}
