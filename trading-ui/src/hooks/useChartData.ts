"use client"
/* eslint-disable @typescript-eslint/no-explicit-any */

import { useEffect, useCallback } from "react"
import { useQuery } from "@tanstack/react-query"
import { useChartStore } from "@/store/useChartStore"
import { chartService } from "@/services/chartService"
import { useWebSocket } from "./useWebSocket"

export function useChartData() {
  const { symbol, interval, setCandles, setLoading, setError } = useChartStore()
  const ws = useWebSocket()

  const { isLoading, error } = useQuery({
    queryKey: ["candles", symbol, interval],
    queryFn: async () => {
      setLoading(true)
      const data = await chartService.fetchCandles(symbol, interval, 5)
      setCandles(data.candles || [])
      setLoading(false)
      return data
    },
    staleTime: 30_000,
    refetchInterval: 60_000,
  })

  useEffect(() => {
    if (error) setError(error.message)
  }, [error, setError])

  useEffect(() => {
    const handler = (msg: any) => {
      const payload = msg.payload || msg
      if (payload.symbol === symbol) {
        useChartStore.getState().updateLastCandle({
          close: payload.close ?? payload.price,
          high: payload.high ?? payload.price,
          low: payload.low ?? payload.price,
          volume: payload.volume ?? 0,
        })
      }
    }
    ws.on("market_data", handler)
    return () => ws.off("market_data")
  }, [symbol, ws])

  const refetch = useCallback(() => {
    chartService.fetchCandles(symbol, interval, 5).then((d) => setCandles(d.candles || []))
  }, [symbol, interval, setCandles])

  return { isLoading, refetch }
}
