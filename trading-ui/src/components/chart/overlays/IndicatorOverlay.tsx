"use client"

import { useEffect, useRef, useMemo } from "react"
import { useChartStore } from "@/store/useChartStore"
import { useOverlayStore, INDICATOR_COLORS } from "@/store/useOverlayStore"
import {
  computeEMA,
  computeSMA,
  computeVWAP,
  computeSuperTrend,
  toSeriesPoints,
} from "@/utils/indicatorEngine"
import type { IndicatorSeriesData } from "@/types"

/**
 * IndicatorOverlay
 * - Reads candle data from useChartStore
 * - Computes full time-series for EMA9, EMA20, EMA50, EMA200, SMA20, SMA50, VWAP, SuperTrend
 * - Pushes time-series into chart store as indicatorSeries[]
 * - Respects toggle visibility from useOverlayStore
 * - Real-time updates from candles via useChartStore
 * - Each indicator uses unique colors, toggles visibility per-indicator
 */
export function IndicatorOverlay() {
  const { ema, sma, vwap, supertrend, indicatorConfig } = useOverlayStore()
  const candles = useChartStore((s) => s.candles)
  const setIndicatorSeries = useChartStore((s) => s.setIndicatorSeries)
  const prevRef = useRef<string>("")

  const computedSeries = useMemo((): IndicatorSeriesData[] => {
    if (!candles.length) return []

    const result: IndicatorSeriesData[] = []

    // ── EMA Series ──
    if (ema) {
      for (const [key, period] of [["ema_9", 9], ["ema_20", 20], ["ema_50", 50], ["ema_200", 200]] as const) {
        const cfg = indicatorConfig[key]
        if (cfg?.visible !== false) {
          const values = computeEMA(candles, period)
          const points = toSeriesPoints(candles, values)
          if (points.length > 0) {
            result.push({
              id: `indicator_${key}`,
              label: cfg?.label || key.toUpperCase(),
              color: cfg?.color || INDICATOR_COLORS[key] || "#888",
              lineStyle: "solid",
              lineWidth: cfg?.width || 1,
              data: points,
              visible: true,
            })
          }
        }
      }
    }

    // ── SMA Series ──
    if (sma) {
      for (const [key, period] of [["sma_20", 20], ["sma_50", 50]] as const) {
        const cfg = indicatorConfig[key]
        if (cfg?.visible !== false) {
          const values = computeSMA(candles, period)
          const points = toSeriesPoints(candles, values)
          if (points.length > 0) {
            result.push({
              id: `indicator_${key}`,
              label: cfg?.label || key.toUpperCase(),
              color: cfg?.color || INDICATOR_COLORS[key] || "#888",
              lineStyle: "solid",
              lineWidth: cfg?.width || 1,
              data: points,
              visible: true,
            })
          }
        }
      }
    }

    // ── VWAP ──
    if (vwap) {
      const cfg = indicatorConfig.vwap
      if (cfg?.visible !== false) {
        const values = computeVWAP(candles)
        const points = toSeriesPoints(candles, values)
        if (points.length > 0) {
          result.push({
            id: "indicator_vwap",
            label: cfg?.label || "VWAP",
            color: cfg?.color || INDICATOR_COLORS.vwap,
            lineStyle: "dashed",
            lineWidth: cfg?.width || 1,
            data: points,
            visible: true,
          })
        }
      }
    }

    // ── SuperTrend ──
    if (supertrend) {
      const cfg = indicatorConfig.supertrend
      if (cfg?.visible !== false) {
        const st = computeSuperTrend(candles, 10, 3)
        const points: { time: string; value: number }[] = []
        for (let i = 0; i < candles.length; i++) {
          if (st.supertrend[i] !== null) {
            points.push({ time: candles[i].time, value: st.supertrend[i]! })
          }
        }
        if (points.length > 0) {
          result.push({
            id: "indicator_supertrend",
            label: cfg?.label || "SuperTrend",
            color: cfg?.color || INDICATOR_COLORS.supertrend,
            lineStyle: "solid",
            lineWidth: cfg?.width || 2,
            data: points,
            visible: true,
          })
        }
      }
    }

    return result
  }, [candles, ema, sma, vwap, supertrend, indicatorConfig])

  // Push to chart store with change detection
  useEffect(() => {
    const key = JSON.stringify(computedSeries.map((s) => `${s.id}:${s.data.length}:${s.data.slice(-1)?.[0]?.value}`))
    if (key !== prevRef.current) {
      prevRef.current = key
      setIndicatorSeries(computedSeries)
    }
  }, [computedSeries, setIndicatorSeries])

  return null
}
