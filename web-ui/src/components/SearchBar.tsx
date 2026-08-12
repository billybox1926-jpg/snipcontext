import { useState } from 'react'

type Props = {
  value: string
  onChange: (value: string) => void
}

export default function SearchBar({ value, onChange }: Props) {
  return (
    <input
      value={value}
      onChange={(e) => onChange(e.target.value)}
      placeholder="Search snippets..."
      className="w-full rounded border border-gray-700 bg-gray-900 p-2 text-gray-100"
    />
  )
}
