const BASE = import.meta.env.VITE_API_BASE || '/api'
const WS_BASE = import.meta.env.VITE_WS_BASE || ''

function buildUrl(path: string) {
  return `${BASE}${path}`
}

export async function get<T>(path: string): Promise<T> {
  const res = await fetch(buildUrl(path), { headers: { accept: 'application/json' } })
  if (!res.ok) throw new Error(`GET ${path} failed: ${res.status}`)
  return (await res.json()) as T
}

export async function put<T>(path: string, body: unknown): Promise<T> {
  const res = await fetch(buildUrl(path), {
    method: 'PUT',
    headers: { 'content-type': 'application/json', accept: 'application/json' },
    body: JSON.stringify(body),
  })
  if (!res.ok) throw new Error(`PUT ${path} failed: ${res.status}`)
  return (await res.json()) as T
}

export async function del<T>(path: string): Promise<T> {
  const res = await fetch(buildUrl(path), { method: 'DELETE' })
  if (!res.ok) throw new Error(`DELETE ${path} failed: ${res.status}`)
  return (await res.json()) as T
}

export async function post<T>(path: string, body: unknown): Promise<T> {
  const res = await fetch(buildUrl(path), {
    method: 'POST',
    headers: { 'content-type': 'application/json', accept: 'application/json' },
    body: JSON.stringify(body),
  })
  if (!res.ok) throw new Error(`POST ${path} failed: ${res.status}`)
  return (await res.json()) as T
}

export function ws(path: string) {
  const url = WS_BASE ? `${WS_BASE}${path}` : `${location.protocol === 'https:' ? 'wss' : 'ws'}://${location.host}${path}`
  return new WebSocket(url)
}
