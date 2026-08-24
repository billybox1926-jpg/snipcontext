import { useEffect, useRef } from 'react'
import { useQueryClient } from '@tanstack/react-query'
import { ws } from '../api/client'

type EventHandler = (data: Record<string, unknown>) => void

export function useWebSocket(url = '/api/ws') {
  const qc = useQueryClient()
  const wsRef = useRef<WebSocket | null>(null)
  const handlersRef = useRef<Map<string, EventHandler>>(new Map())

  const register = useRef(<K extends string>(event: K, handler: EventHandler) => {
    handlersRef.current.set(event, handler as EventHandler)
  }).current

  const unregister = useRef((event: string) => {
    handlersRef.current.delete(event)
  }).current

  useEffect(() => {
    let reconnectTimer: ReturnType<typeof setTimeout> | undefined
    let reconnectDelay = 500

    function connect() {
      if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) return
      const socket = ws(url)
      wsRef.current = socket

      socket.onopen = () => {
        reconnectDelay = 500
      }

      socket.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data) as Record<string, unknown>
          const type = String(data.type ?? '')
          const handler = handlersRef.current.get(type)
          if (handler) handler(data)
        } catch {
          // ignore malformed messages
        }
      }

      socket.onclose = () => {
        reconnectTimer = setTimeout(() => {
          reconnectDelay = Math.min(reconnectDelay * 2, 15000)
          connect()
        }, reconnectDelay)
      }

      socket.onerror = () => {
        socket.close()
      }
    }

    connect()
    return () => {
      if (reconnectTimer) clearTimeout(reconnectTimer)
      wsRef.current?.close()
      wsRef.current = null
    }
  }, [url])

  useEffect(() => {
    const refreshTags = () => qc.invalidateQueries({ queryKey: ['tags'] })
    const refreshSnippets = () => qc.invalidateQueries({ queryKey: ['snippets'] })
    const refreshIndex = () => qc.invalidateQueries({ queryKey: ['index', 'status'] })

    register('snippet_created', refreshSnippets)
    register('snippet_updated', () => {
      refreshSnippets()
      refreshTags()
    })
    register('snippet_deleted', () => {
      refreshSnippets()
      refreshTags()
    })
    register('tags_updated', refreshTags)
    register('index_rebuild_started', refreshIndex)
    register('index_rebuild_completed', refreshIndex)
    register('index_rebuild_failed', refreshIndex)

    return () => {
      unregister('snippet_created')
      unregister('snippet_updated')
      unregister('snippet_deleted')
      unregister('tags_updated')
      unregister('index_rebuild_started')
      unregister('index_rebuild_completed')
      unregister('index_rebuild_failed')
    }
  }, [qc, register, unregister])

  return { on: register, off: unregister }
}
