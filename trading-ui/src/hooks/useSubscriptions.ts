"use client"
/* eslint-disable @typescript-eslint/no-explicit-any */

import { useEffect, useRef } from "react"
import { getWSManager } from "@/services/websocketManager"
import { useRealtimeStore } from "@/store/useRealtimeStore"

/**
 * useSubscriptions — manages channel/symbol subscriptions for a component.
 *
 * Usage:
 *   useSubscriptions("my-component", ["market_data"], ["NIFTY 50"])
 */
export function useSubscriptions(
  id: string,
  channels: string[],
  symbols: string[]
) {
  const initialized = useRef(false)

  useEffect(() => {
    const ws = getWSManager()
    ws.subscribe(id, channels, symbols, (msg: any) => {
      useRealtimeStore.getState().recordEvent(msg.type || "unknown")
    })

    // Track streaming symbols
    symbols.forEach((s) => useRealtimeStore.getState().addStreamingSymbol(s))

    return () => {
      ws.unsubscribe(id)
    }
  }, [id, channels.join(","), symbols.join(",")])
}
