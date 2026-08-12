import { useEffect, useRef, useState } from 'react'

type Message = Record<string, unknown>

export function useWebSocket(path = '/ws') {
  const wsRef = useRef<WebSocket | null>(null)
  const [lastMessage, setLastMessage] = useState<Message | null>(null)

  useEffect(() => {
    const ws = wsRef.current = new WebSocket(
      `${location.protocol === 'https:' ? 'wss' : 'ws'}://${location.host}${path}`
    )
    ws.addEventListener('message', (event) => {
      const data = typeof event.data === 'string' ? JSON.parse(event.data) : event.data
      setLastMessage(data as Message)
    })
    return () => ws.close()
  }, [path])

  return { lastMessage }
}
