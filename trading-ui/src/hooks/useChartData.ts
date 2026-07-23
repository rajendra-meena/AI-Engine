"use client"
/* eslint-disable @typescript-eslint/no-explicit-any */

import { useEffect, useCallback } from "react"
import { useQuery } from "@tanstack/react-query"
import { useChartStore } from "@/store/useChartStore"
import { chartService } from "@/services/chartService"
import { getWSManager } from "@/services/websocketManager"

export function useChartData() {
  const { symbol, interval, setCandles, setLoading, setError } = useChartStore()

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
    const ws = getWSManager()
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
    const unsub = ws.onEvent("market_data", handler)
    return () => { unsub() }
  }, [symbol])

  const refetch = useCallback(() => {
    setLoading(true)
    chartService.fetchCandles(symbol, interval, 5)
      .then((d) => {
        setCandles(d.candles || [])
        setLoading(false)
      })
      .catch((err) => {
        setError(err instanceof Error ? err.message : "Failed to fetch")
        setLoading(false)
      })
  }, [symbol, interval, setCandles, setLoading, setError])

  return { isLoading, refetch }
}
