"use client"

import { useEffect, useRef, useMemo } from "react"
import { useQuery } from "@tanstack/react-query"
import { patternService } from "@/services/patternService"
import { useChartStore, type ChartMarker } from "@/store/useChartStore"
import { useOverlayStore } from "@/store/useOverlayStore"

const BULL_COLOR = "#22c55e"
const BEAR_COLOR = "#ef4444"
const BREAKOUT_COLOR = "#f59e0b"

/**
 * PatternOverlay
 * - Renders candlestick patterns (hammer, engulfing, doji, etc.)
 * - Renders breakout patterns
 * - Shows pattern name, direction color, and confidence level
 * - Respects toggle state from useOverlayStore
 * - Real-time updates via backend snapshot polling
 */
export function PatternOverlay() {
  const { patterns, labels } = useOverlayStore()
  const { candles, setMarkers } = useChartStore()
  const prevRef = useRef<string>("")

  const { data } = useQuery({
    queryKey: ["patterns", "NIFTY 50", "15m"],
    queryFn: () => patternService.getLatest("NIFTY 50", "15m"),
    refetchInterval: 30_000,
    staleTime: 10_000,
  })

  const patternMarkers = useMemo((): ChartMarker[] => {
    if (!data || !candles.length || !patterns) return []
    const result: ChartMarker[] = []
    const last = candles[candles.length - 1]
    const time = last.time

    // Strongest pattern if labels enabled
    if (labels && data.strongest_pattern) {
      const isBullish = data.pattern_direction === "bullish"
      result.push({
        time, position: isBullish ? "aboveBar" : "belowBar",
        color: isBullish ? BULL_COLOR : BEAR_COLOR,
        shape: isBullish ? "arrowUp" : "arrowDown",
        text: `${data.strongest_pattern} (${data.confidence || "N/A"})`,
      })
    }

    // Candlestick patterns (max 3)
    let added = 0
    for (const p of data.candlestick_patterns || []) {
      if (added >= 3) break
      const isBullish = p.direction === "bullish"
      const confLabel = p.confidence ? `${Math.round(p.confidence * 100)}%` : ""
      result.push({
        time, position: isBullish ? "aboveBar" : "belowBar",
        color: isBullish ? BULL_COLOR : BEAR_COLOR,
        shape: isBullish ? "arrowUp" : "arrowDown",
        text: labels ? `${p.name}${confLabel ? ` ${confLabel}` : ""}` : p.name,
      })
      added++
    }

    // Chart patterns (max 2)
    for (const p of data.chart_patterns || []) {
      if (added >= 5) break
      const isBullish = p.direction === "bullish"
      const confLabel = p.confidence ? `${Math.round(p.confidence * 100)}%` : ""
      result.push({
        time, position: isBullish ? "aboveBar" : "belowBar",
        color: isBullish ? BULL_COLOR : BEAR_COLOR,
        shape: "circle",
        text: labels ? `${p.name} ${confLabel}` : p.name,
      })
      added++
    }

    // Breakout patterns (max 2)
    for (const p of data.breakout_patterns || []) {
      if (added >= 7) break
      const isBullish = p.direction === "bullish"
      const confLabel = p.confidence ? `${Math.round(p.confidence * 100)}%` : ""
      result.push({
        time, position: isBullish ? "aboveBar" : "belowBar",
        color: BREAKOUT_COLOR,
        shape: isBullish ? "arrowUp" : "arrowDown",
        text: labels ? `${p.name}${p.volume_confirmed ? " (Vol)" : ""} ${confLabel}` : p.name,
      })
      added++
    }

    return result
  }, [data, candles, patterns, labels])

  // Merge with existing non-pattern markers
  useEffect(() => {
    if (!patternMarkers.length) return

    // Filter out old pattern markers from the existing markers array
    // Pattern markers are identified by having certain key substrings
    const existingNonPattern = useChartStore.getState().markers.filter(
      (m) => !["hammer", "engulfing", "doji", "breakout", "nr7", "pinbar", "insidebar"]
        .some((k) => m.text.toLowerCase().includes(k))
    )

    // Remove all existing pattern markers that would be replaced
    const newMarkers = [...existingNonPattern, ...patternMarkers]

    const key = JSON.stringify(patternMarkers.map((m) => `${m.text}:${m.time}`))
    if (key !== prevRef.current) {
      prevRef.current = key
      setMarkers(newMarkers)
    }
  }, [patternMarkers, setMarkers])

  return null
}
