"use client"
/* eslint-disable @typescript-eslint/no-explicit-any */

import { useEffect, useRef, useCallback } from "react"
import { useChartStore } from "@/store/useChartStore"

type MessageHandler = (data: any) => void

const WS_URL = process.env.NEXT_PUBLIC_WS_URL || "ws://localhost:8000/ws"

export function useWebSocket() {
  const wsRef = useRef<WebSocket | null>(null)
  const reconnectRef = useRef<number>(0)
  const handlersRef = useRef<Map<string, MessageHandler>>(new Map())
  const setConnected = useChartStore((s) => s.setConnected)

  const connect = useCallback(() => {
    try {
      const ws = new WebSocket(WS_URL)
      wsRef.current = ws

      ws.onopen = () => {
        setConnected(true)
        reconnectRef.current = 0
        ws.send(JSON.stringify({ type: "subscribe", payload: { channels: ["market_data"], symbols: ["NIFTY 50"] } }))
      }

      ws.onmessage = (event) => {
        try {
          const msg = JSON.parse(event.data)
          const handler = handlersRef.current.get(msg.type)
          if (handler) handler(msg)
        } catch { /* ignore parse errors */ }
      }

      ws.onclose = () => {
        setConnected(false)
        const delay = Math.min(1000 * 2 ** reconnectRef.current, 30000)
        reconnectRef.current++
        // eslint-disable-next-line react-hooks/immutability
        setTimeout(connect, delay)
      }

      ws.onerror = () => { ws.close() }
    } catch { /* ignore connect errors */ }
  }, [setConnected])

  useEffect(() => {
    connect()
    return () => { wsRef.current?.close() }
  }, [connect])

  const on = useCallback((type: string, handler: MessageHandler) => {
    handlersRef.current.set(type, handler)
  }, [])

  const off = useCallback((type: string) => {
    handlersRef.current.delete(type)
  }, [])

  const send = useCallback((data: object) => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify(data))
    }
  }, [])

  return { on, off, send }
}
