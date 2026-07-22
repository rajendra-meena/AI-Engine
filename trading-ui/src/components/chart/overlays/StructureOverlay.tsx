"use client"

import { useEffect, useRef, useMemo } from "react"
import { useQuery } from "@tanstack/react-query"
import { structureService } from "@/services/structureService"
import { useChartStore, type ChartMarker, type ChartLine } from "@/store/useChartStore"
import { useOverlayStore } from "@/store/useOverlayStore"
import type { TrendLineData } from "@/types"

const BULL_COLOR = "#22c55e"
const BEAR_COLOR = "#ef4444"
const BOS_COLOR = "#f59e0b"
const CHoCH_COLOR = "#8b5cf6"

/**
 * StructureOverlay
 * - Renders swing high/low levels as horizontal lines
 * - HH/HL/LH/LL markers and labels
 * - BOS (Break of Structure) and CHoCH (Change of Character) trend lines
 * - Trend direction labels
 * - Respects toggle state from useOverlayStore
 * - Real-time updates via backend snapshot polling
 */
export function StructureOverlay() {
  const { structure, bos, choch, labels, trendLines: showTrendLines } = useOverlayStore()
  const { candles, setMarkers, setHorizontalLines, setTrendLines } = useChartStore()
  const prevRef = useRef<string>("")

  const { data } = useQuery({
    queryKey: ["structure", "NIFTY 50", "15m"],
    queryFn: () => structureService.getLatest("NIFTY 50", "15m"),
    refetchInterval: 30_000,
    staleTime: 10_000,
  })

  const newMarkers = useMemo((): ChartMarker[] => {
    if (!data || !candles.length || !structure) return []
    const result: ChartMarker[] = []
    const last = candles[candles.length - 1]
    const time = last.time

    // Trend label
    if (labels && data.trend) {
      const trendColor = data.trend === "UP" ? BULL_COLOR : data.trend === "DOWN" ? BEAR_COLOR : "#888"
      result.push({
        time, position: "aboveBar",
        color: trendColor, shape: "circle",
        text: `${data.trend} ${data.trend_strength || ""}`.trim(),
      })
    }

    // Swing levels
    if (data.current_swing_high) {
      result.push({
        time, position: "belowBar",
        color: BEAR_COLOR, shape: "arrowDown", text: `SH ${data.current_swing_high.toFixed(0)}`,
      })
    }
    if (data.current_swing_low) {
      result.push({
        time, position: "aboveBar",
        color: BULL_COLOR, shape: "arrowUp", text: `SL ${data.current_swing_low.toFixed(0)}`,
      })
    }

    // HH/HL/LH/LL
    if (labels) {
      if (data.last_hh) result.push({
        time, position: "aboveBar", color: BULL_COLOR, shape: "arrowUp", text: `HH ${data.last_hh.toFixed(0)}`,
      })
      if (data.last_hl) result.push({
        time, position: "aboveBar", color: BULL_COLOR, shape: "arrowUp", text: `HL ${data.last_hl.toFixed(0)}`,
      })
      if (data.last_lh) result.push({
        time, position: "belowBar", color: BEAR_COLOR, shape: "arrowDown", text: `LH ${data.last_lh.toFixed(0)}`,
      })
      if (data.last_ll) result.push({
        time, position: "belowBar", color: BEAR_COLOR, shape: "arrowDown", text: `LL ${data.last_ll.toFixed(0)}`,
      })
    }

    // BOS markers
    if (bos && data.bos_count > 0 && labels) {
      result.push({
        time, position: "belowBar", color: BOS_COLOR, shape: "arrowDown", text: `BOS x${data.bos_count}`,
      })
    }

    // CHoCH markers
    if (choch && data.choch_count > 0 && labels) {
      result.push({
        time, position: "aboveBar", color: CHoCH_COLOR, shape: "arrowUp", text: `CHoCH x${data.choch_count}`,
      })
    }

    return result
  }, [data, candles, structure, bos, choch, labels])

  const newLines = useMemo((): ChartLine[] => {
    if (!data || !candles.length || !structure) return []
    const result: ChartLine[] = []
    const last = candles[candles.length - 1]
    const time = last.time

    if (data.current_swing_high) {
      result.push({
        time, price: data.current_swing_high, color: BEAR_COLOR,
        lineStyle: "dotted", title: "Swing High", width: 1,
      })
    }
    if (data.current_swing_low) {
      result.push({
        time, price: data.current_swing_low, color: BULL_COLOR,
        lineStyle: "dotted", title: "Swing Low", width: 1,
      })
    }

    // HH/HL/LH/LL lines
    if (labels) {
      if (data.last_hh) result.push({ time, price: data.last_hh, color: BULL_COLOR, lineStyle: "dashed", title: "HH", width: 1 })
      if (data.last_hl) result.push({ time, price: data.last_hl, color: BULL_COLOR, lineStyle: "dashed", title: "HL", width: 1 })
      if (data.last_lh) result.push({ time, price: data.last_lh, color: BEAR_COLOR, lineStyle: "dashed", title: "LH", width: 1 })
      if (data.last_ll) result.push({ time, price: data.last_ll, color: BEAR_COLOR, lineStyle: "dashed", title: "LL", width: 1 })
    }

    return result
  }, [data, candles, structure, labels])

  // Trend lines (connecting swing points for visual structure)
  const newTrendLines = useMemo((): TrendLineData[] => {
    if (!data || !candles.length || !showTrendLines) return []
    const result: TrendLineData[] = []
    const last = candles[candles.length - 1]

    // Draw a trend line from the last swing low to current price (uptrend)
    if (data.trend === "UP" && data.last_hl) {
      result.push({
        id: "trend_up",
        label: "Uptrend",
        points: [
          { time: candles[Math.max(0, candles.length - 10)].time, price: data.last_hl },
          { time: last.time, price: last.close + (data.current_swing_high ? (data.current_swing_high - data.last_hl) * 0.5 : 50) },
        ],
        color: BULL_COLOR + "60",
        lineStyle: "dashed",
        lineWidth: 1,
        visible: true,
      })
    }

    // Draw a trend line from last swing high to current price (downtrend)
    if (data.trend === "DOWN" && data.last_lh) {
      result.push({
        id: "trend_down",
        label: "Downtrend",
        points: [
          { time: candles[Math.max(0, candles.length - 10)].time, price: data.last_lh },
          { time: last.time, price: last.close - (data.last_lh - (data.current_swing_low || last.close)) * 0.5 },
        ],
        color: BEAR_COLOR + "60",
        lineStyle: "dashed",
        lineWidth: 1,
        visible: true,
      })
    }

    return result
  }, [data, candles, showTrendLines])

  // Push to store with change detection
  useEffect(() => {
    const key = JSON.stringify([
      ...newMarkers.map((m) => `${m.text}:${m.time}`),
      ...newLines.map((l) => `${l.title}:${l.price}`),
    ])
    if (key !== prevRef.current) {
      prevRef.current = key
      setMarkers((newMarkers.length > 0) ? newMarkers : [])
      setHorizontalLines(newLines)
      setTrendLines(newTrendLines)
    }
  }, [newMarkers, newLines, newTrendLines, setMarkers, setHorizontalLines, setTrendLines])

  return null
}
