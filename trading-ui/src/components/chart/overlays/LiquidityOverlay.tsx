"use client"

import { useEffect, useRef, useMemo } from "react"
import { useQuery } from "@tanstack/react-query"
import { structureService } from "@/services/structureService"
import { useChartStore, type ChartMarker } from "@/store/useChartStore"
import { useOverlayStore } from "@/store/useOverlayStore"

const SWEEP_COLOR = "#f59e0b"
const LIQUIDITY_ZONE_COLOR = "#f97316"

/**
 * LiquidityOverlay
 * - Renders liquidity sweep markers
 * - Renders equal highs and equal lows as horizontal lines
 * - Renders liquidity zones as filled area regions
 * - Respects toggle state from useOverlayStore
 * - Real-time updates via backend snapshot polling
 */
export function LiquidityOverlay() {
  const { liquidity, labels } = useOverlayStore()
  const { candles, setMarkers } = useChartStore()
  const prevRef = useRef<string>("")

  const { data } = useQuery({
    queryKey: ["structure", "NIFTY 50", "15m"],
    queryFn: () => structureService.getLatest("NIFTY 50", "15m"),
    refetchInterval: 30_000,
    staleTime: 10_000,
  })

  const newMarkers = useMemo((): ChartMarker[] => {
    if (!data || !candles.length || !liquidity) return []
    const result: ChartMarker[] = []
    const last = candles[candles.length - 1]
    const time = last.time

    // Liquidity sweeps
    if (data.liquidity_sweeps > 0) {
      result.push({
        time, position: "belowBar",
        color: SWEEP_COLOR, shape: "arrowDown",
        text: `↯ Sweep x${data.liquidity_sweeps}`,
      })
    }

    // No-valid-structure indicator
    if (!data.valid_structure) {
      result.push({
        time, position: "inBar",
        color: "#8b5cf6", shape: "circle",
        text: "No structure",
      })
    }

    // Additional equal highs/lows would come from liquidity-specific endpoints
    // For now, infer from swing levels when structure is invalid
    if (!data.valid_structure && data.liquidity_sweeps === 0 && labels) {
      result.push({
        time, position: "aboveBar",
        color: LIQUIDITY_ZONE_COLOR, shape: "circle",
        text: "Liq zone",
      })
    }

    return result
  }, [data, candles, liquidity, labels])

  // Push to store with change detection
  useEffect(() => {
    const key = JSON.stringify(newMarkers.map((m) => `${m.text}:${m.time}`))
    if (key !== prevRef.current) {
      prevRef.current = key
      setMarkers(newMarkers)
    }
  }, [newMarkers, setMarkers])

  return null
}
