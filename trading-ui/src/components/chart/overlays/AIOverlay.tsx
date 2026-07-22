"use client"

import { useEffect, useRef, useMemo } from "react"
import { useQuery } from "@tanstack/react-query"
import { decisionService } from "@/services/decisionService"
import { useChartStore, type ChartMarker, type ChartLine } from "@/store/useChartStore"
import { useOverlayStore } from "@/store/useOverlayStore"
import type { ChartZone } from "@/types"

const BULL_COLOR = "#22c55e"
const BEAR_COLOR = "#ef4444"
const NEUTRAL_COLOR = "#8b5cf6"
const ENTRY_COLOR = "#6366f1"
const SL_COLOR = "#ef4444"
const TARGET_COLORS = ["#22c55e", "#16a34a", "#15803d"]

/**
 * AIOverlay
 * - Renders institutional bias, score, and confidence markers
 * - Renders entry zone as a filled rectangle
 * - Renders stoploss line
 * - Renders up to 3 target lines (T1, T2, T3)
 * - Renders risk-reward ratio label
 * - Renders decision text and reasoning labels
 * - Respects toggle state from useOverlayStore
 * - Real-time updates via backend snapshot polling
 */
export function AIOverlay() {
  const { ai, targets, labels, supplyDemand } = useOverlayStore()
  const { candles, setMarkers, setHorizontalLines, setChartZones } = useChartStore()
  const prevRef = useRef<{ markers: string; lines: string; zones: string }>({ markers: "", lines: "", zones: "" })

  const { data } = useQuery({
    queryKey: ["decision", "NIFTY 50"],
    queryFn: () => decisionService.getLatest("NIFTY 50"),
    refetchInterval: 30_000,
    staleTime: 10_000,
  })

  const newMarkers = useMemo((): ChartMarker[] => {
    if (!data || !candles.length || !ai) return []
    const result: ChartMarker[] = []
    const last = candles[candles.length - 1]
    const time = last.time
    const plan = data.trade_plan

    // Institutional bias + score
    if (labels) {
      const isBullish = data.score >= 60
      const isBearish = data.score <= 40
      const biasColor = isBullish ? BULL_COLOR : isBearish ? BEAR_COLOR : NEUTRAL_COLOR
      result.push({
        time, position: "aboveBar",
        color: biasColor, shape: "circle",
        text: `Score:${data.score} ${data.decision} | Conf:${data.confidence}%`,
      })

      // Risk level
      if (data.risk_level) {
        result.push({
          time, position: "belowBar",
          color: data.risk_level === "low" ? BULL_COLOR : data.risk_level === "medium" ? NEUTRAL_COLOR : BEAR_COLOR,
          shape: "circle",
          text: `Risk:${data.risk_level}(${data.risk_score?.toFixed(0) || "?"})`,
        })
      }
    }

    // Trade plan markers
    if (plan?.valid && plan.direction !== "NONE") {
      const isLong = plan.direction === "LONG"
      const entryColor = isLong ? ENTRY_COLOR : BEAR_COLOR

      if (labels) {
        result.push({
          time, position: isLong ? "aboveBar" : "belowBar",
          color: entryColor, shape: isLong ? "arrowUp" : "arrowDown",
          text: plan.direction === "LONG" ? "LONG ↑" : "SHORT ↓",
        })
      }

      // SL zone
      if (targets && plan.sl_zone?.price && labels) {
        result.push({
          time, position: "belowBar",
          color: SL_COLOR, shape: "arrowDown",
          text: `SL ${plan.sl_zone.price.toFixed(0)}`,
        })
      }

      // Target zones (T1, T2, T3)
      if (targets) {
        for (let i = 0; i < (plan.target_zones?.length || 0); i++) {
          const t = plan.target_zones[i]
          const tColor = TARGET_COLORS[Math.min(i, TARGET_COLORS.length - 1)]
          result.push({
            time, position: isLong ? "aboveBar" : "belowBar",
            color: tColor, shape: isLong ? "arrowUp" : "arrowDown",
            text: labels
              ? `T${i + 1} ${t.price?.toFixed(0) || ""}${t.probability ? ` (${Math.round(t.probability * 100)}%)` : ""}`
              : `T${i + 1}`,
          })
        }
      }
    }

    return result
  }, [data, candles, ai, targets, labels])

  const newLines = useMemo((): ChartLine[] => {
    if (!data || !candles.length || !ai) return []
    const result: ChartLine[] = []
    const last = candles[candles.length - 1]
    const time = last.time
    const plan = data.trade_plan

    if (plan?.valid && plan.direction !== "NONE") {
      // Entry zone boundaries
      if (plan.entry_zone) {
        const entryPrice = typeof plan.entry_zone === "number" ? plan.entry_zone : plan.entry_zone?.price || plan.entry_zone?.top
        if (entryPrice) {
          result.push({
            time, price: entryPrice, color: ENTRY_COLOR,
            lineStyle: "dashed", title: "Entry", width: 1,
          })
        }
      }

      // Stoploss line
      if (targets && plan.sl_zone?.price) {
        result.push({
          time, price: plan.sl_zone.price, color: SL_COLOR,
          lineStyle: "solid", title: "Stoploss", width: 1,
        })
      }

      // Target lines
      if (targets) {
        for (let i = 0; i < (plan.target_zones?.length || 0); i++) {
          const t = plan.target_zones[i]
          const tColor = TARGET_COLORS[Math.min(i, TARGET_COLORS.length - 1)]
          if (t.price) {
            result.push({
              time, price: t.price, color: tColor,
              lineStyle: "dashed", title: `T${i + 1}`, width: 1,
            })
          }
        }
      }
    }

    return result
  }, [data, candles, ai, targets])

  const newZones = useMemo((): ChartZone[] => {
    if (!data || !candles.length || !ai || !supplyDemand) return []
    const result: ChartZone[] = []
    const last = candles[candles.length - 1]
    const time = last.time
    const plan = data.trade_plan

    // Entry zone as filled rectangle if we have top/bottom
    if (plan?.valid && plan.entry_zone && typeof plan.entry_zone === "object" && "top" in plan.entry_zone && "bottom" in plan.entry_zone) {
      const entry = plan.entry_zone as { top: number; bottom: number }
      if (entry.top && entry.bottom) {
        result.push({
          id: "ai_entry_zone",
          time,
          top: Math.max(entry.top, entry.bottom),
          bottom: Math.min(entry.top, entry.bottom),
          color: ENTRY_COLOR + "20",
          borderColor: ENTRY_COLOR,
          label: "Entry Zone",
          visible: true,
        })
      }
    }

    return result
  }, [data, candles, ai, supplyDemand])

  // Push to store with change detection
  useEffect(() => {
    const markersKey = JSON.stringify(newMarkers.map((m) => `${m.text}:${m.time}`))
    const linesKey = JSON.stringify(newLines.map((l) => `${l.title}:${l.price}`))
    const zonesKey = JSON.stringify(newZones.map((z) => `${z.id}:${z.top}:${z.bottom}`))

    if (markersKey !== prevRef.current.markers) {
      prevRef.current.markers = markersKey
      // Merge with existing non-AI markers
      const existing = useChartStore.getState().markers.filter(
        (m) => !["ENTRY", "SL", "T1", "T2", "T3", "BIAS", "Score", "LONG", "SHORT", "Risk:"]
          .some((k) => m.text.includes(k))
      )
      setMarkers([...existing, ...newMarkers])
    }

    if (linesKey !== prevRef.current.lines) {
      prevRef.current.lines = linesKey
      // Merge with existing non-AI lines
      const existing = useChartStore.getState().horizontalLines.filter(
        (l) => !["Entry", "Stoploss", "T1", "T2", "T3"].includes(l.title)
      )
      setHorizontalLines([...existing, ...newLines])
    }

    if (zonesKey !== prevRef.current.zones) {
      prevRef.current.zones = zonesKey
      // Add AI zones to existing chart zones
      setChartZones(newZones)
    }
  }, [newMarkers, newLines, newZones, setMarkers, setHorizontalLines, setChartZones])

  return null
}
