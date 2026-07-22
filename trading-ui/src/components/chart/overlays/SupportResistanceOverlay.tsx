"use client"

import { useEffect, useRef, useMemo } from "react"
import { useQuery } from "@tanstack/react-query"
import { srService } from "@/services/srService"
import { useChartStore, type ChartLine, type ChartMarker } from "@/store/useChartStore"
import { useOverlayStore } from "@/store/useOverlayStore"
import type { ChartZone } from "@/types"

const S_COLOR = "#22c55e"
const R_COLOR = "#ef4444"
const PSY_COLOR = "#a855f7"
const BREAKOUT_COLOR = "#f59e0b"

/**
 * SupportResistanceOverlay
 * - Renders major support and resistance lines
 * - Renders nearest S/R levels
 * - Renders supply and demand zones as filled area regions
 * - Renders dynamic EMA levels (from backend snapshot)
 * - Renders psychological levels (round numbers)
 * - Renders breakout labels
 * - Respects toggle state from useOverlayStore
 * - Real-time updates via backend snapshot polling
 */
export function SupportResistanceOverlay() {
  const { sr, supplyDemand, zoneLabels, labels } = useOverlayStore()
  const { candles, setHorizontalLines, setMarkers, setChartZones } = useChartStore()
  const linesPrevRef = useRef<string>("")
  const zonesPrevRef = useRef<string>("")
  const markersPrevRef = useRef<string>("")

  const { data } = useQuery({
    queryKey: ["sr", "NIFTY 50"],
    queryFn: () => srService.getLatest("NIFTY 50"),
    refetchInterval: 30_000,
    staleTime: 10_000,
  })

  const newLines = useMemo((): ChartLine[] => {
    if (!data || !candles.length) return []
    const result: ChartLine[] = []
    const last = candles[candles.length - 1]
    const time = last.time

    if (sr) {
      // Major supports
      for (const s of data.major_supports || []) {
        result.push({
          time, price: s.price, color: S_COLOR, lineStyle: "solid",
          title: s.label || "S", width: 1,
        })
      }
      // Major resistances
      for (const r of data.major_resistances || []) {
        result.push({
          time, price: r.price, color: R_COLOR, lineStyle: "solid",
          title: r.label || "R", width: 1,
        })
      }
      // Nearest S/R
      if (data.nearest_support) {
        result.push({
          time, price: data.nearest_support, color: S_COLOR, lineStyle: "dashed",
          title: "Nearest S", width: 1,
        })
      }
      if (data.nearest_resistance) {
        result.push({
          time, price: data.nearest_resistance, color: R_COLOR, lineStyle: "dashed",
          title: "Nearest R", width: 1,
        })
      }

      // Dynamic levels (EMA-based)
      for (const level of data.dynamic_levels || []) {
        result.push({
          time, price: level.price, color: level.color || "#6366f1", lineStyle: "dotted",
          title: level.label || "Dynamic", width: 1,
        })
      }

      // Psychological levels
      for (const level of data.psychological_levels || []) {
        result.push({
          time, price: level.price, color: PSY_COLOR, lineStyle: "dotted",
          title: level.label || "Psy", width: 1,
        })
      }
    }

    return result
  }, [data, candles, sr])

  const newMarkers = useMemo((): ChartMarker[] => {
    if (!data || !candles.length || !sr) return []
    const result: ChartMarker[] = []
    const last = candles[candles.length - 1]
    const time = last.time

    // Support markers
    for (const s of data.major_supports || []) {
      if (!labels) break
      result.push({
        time, position: "aboveBar", color: S_COLOR, shape: "arrowUp",
        text: s.label ? `${s.label} ${s.price?.toFixed(0)}` : `S ${s.price?.toFixed(0)}`,
      })
    }

    // Resistance markers
    for (const r of data.major_resistances || []) {
      if (!labels) break
      result.push({
        time, position: "belowBar", color: R_COLOR, shape: "arrowDown",
        text: r.label ? `${r.label} ${r.price?.toFixed(0)}` : `R ${r.price?.toFixed(0)}`,
      })
    }

    // Breakout label
    if (labels && data.breakout_state && data.breakout_state !== "none") {
      const isBullish = data.breakout_state === "breakout_up"
      result.push({
        time, position: isBullish ? "aboveBar" : "belowBar",
        color: BREAKOUT_COLOR, shape: isBullish ? "arrowUp" : "arrowDown",
        text: isBullish ? "Breakout ↑" : "Breakout ↓",
      })
    }

    return result
  }, [data, candles, sr, labels])

  const newZones = useMemo((): ChartZone[] => {
    if (!data || !candles.length || !supplyDemand) return []
    const result: ChartZone[] = []
    const last = candles[candles.length - 1]
    const time = last.time

    // Supply zones (red tinted)
    for (const z of data.supply_zones || []) {
      result.push({
        id: `supply_${z.top}_${z.bottom}`,
        time,
        top: z.top,
        bottom: z.bottom,
        color: "#ef4444",
        borderColor: "#ef4444",
        label: zoneLabels ? (z.label || "Supply") : "",
        visible: true,
      })
    }

    // Demand zones (green tinted)
    for (const z of data.demand_zones || []) {
      result.push({
        id: `demand_${z.top}_${z.bottom}`,
        time,
        top: z.top,
        bottom: z.bottom,
        color: "#22c55e",
        borderColor: "#22c55e",
        label: zoneLabels ? (z.label || "Demand") : "",
        visible: true,
      })
    }

    return result
  }, [data, candles, supplyDemand, zoneLabels])

  // Push to store with change detection
  useEffect(() => {
    const key = JSON.stringify(newLines.map((l) => `${l.title}:${l.price}`))
    if (key !== linesPrevRef.current) {
      linesPrevRef.current = key
      setHorizontalLines(newLines)
    }
  }, [newLines, setHorizontalLines])

  useEffect(() => {
    const key = JSON.stringify(newMarkers.map((m) => `${m.text}:${m.time}`))
    if (key !== markersPrevRef.current) {
      markersPrevRef.current = key
      setMarkers(newMarkers)
    }
  }, [newMarkers, setMarkers])

  useEffect(() => {
    const key = JSON.stringify(newZones.map((z) => `${z.id}:${z.top}:${z.bottom}`))
    if (key !== zonesPrevRef.current) {
      zonesPrevRef.current = key
      setChartZones(newZones)
    }
  }, [newZones, setChartZones])

  return null
}
