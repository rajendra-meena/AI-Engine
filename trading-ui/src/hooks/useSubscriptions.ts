"use client"
/* eslint-disable @typescript-eslint/no-explicit-any */

import { useEffect } from "react"
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

  useEffect(() => {
    const ws = getWSManager()
    ws.subscribe(id, channels, symbols, (msg: any) => {
      useRealtimeStore.getState().recordEvent(msg.type || "unknown")
    })

    // Track streaming symbols
    const store = useRealtimeStore.getState()
    symbols.forEach((s) => store.addStreamingSymbol(s))

    return () => {
      ws.unsubscribe(id)
      // Clean up streaming symbols on unmount
      const s = useRealtimeStore.getState()
      symbols.forEach((sym) => s.removeStreamingSymbol(sym))
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [id, channels.join(","), symbols.join(",")])
}
