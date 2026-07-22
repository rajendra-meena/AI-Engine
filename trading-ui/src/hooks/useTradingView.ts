"use client"

// lightweight-charts v5 API requires `as any` for series instances and options
/* eslint-disable @typescript-eslint/no-explicit-any */

import { useEffect, useRef, useCallback } from "react"
import {
  createChart,
  createSeriesMarkers,
  ColorType,
  CandlestickSeries,
  HistogramSeries,
  LineSeries,
  AreaSeries,
} from "lightweight-charts"
import type { IChartApi, Time } from "lightweight-charts"
import { useChartStore } from "@/store/useChartStore"

const THEME = {
  textColor: "#888",
  gridColor: "#1a1a2e",
  borderColor: "#2a2a3e",
  upColor: "#22c55e",
  downColor: "#ef4444",
  wickUpColor: "#22c55e",
  wickDownColor: "#ef4444",
  crosshairColor: "#6366f1",
}

export function useTradingView(containerRef: React.RefObject<HTMLDivElement | null>) {
  const chartRef = useRef<IChartApi | null>(null)
  const candleSeriesRef = useRef<any>(null)
  const volumeSeriesRef = useRef<any>(null)
  const markersPluginRef = useRef<any>(null)

  // Separate map clusters to avoid conflicts
  const hLineMap = useRef<Map<string, any>>(new Map())      // horizontal lines (existing)
  const indicatorMap = useRef<Map<string, any>>(new Map())   // indicator series (Phase 6)
  const trendLineMap = useRef<Map<string, any>>(new Map())   // trend lines (Phase 6)
  const zoneMap = useRef<Map<string, any>>(new Map())        // zone area series (Phase 6)

  const {
    candles, markers, horizontalLines,
    indicatorSeries, chartZones, trendLines,
    autoScale,
  } = useChartStore()

  // ── Create chart ──
  useEffect(() => {
    if (!containerRef.current) return

    const chart = createChart(containerRef.current, {
      layout: {
        background: { type: ColorType.Solid, color: "transparent" },
        textColor: THEME.textColor,
        fontSize: 10,
        fontFamily: "ui-monospace, monospace",
      },
      grid: {
        vertLines: { color: THEME.gridColor, style: 1 },
        horzLines: { color: THEME.gridColor, style: 1 },
      },
      crosshair: {
        mode: 0,
        vertLine: {
          color: THEME.crosshairColor,
          width: 1,
          style: 2,
          labelBackgroundColor: THEME.crosshairColor,
        },
        horzLine: {
          color: THEME.crosshairColor,
          width: 1,
          style: 2,
          labelBackgroundColor: THEME.crosshairColor,
        },
      },
      rightPriceScale: { borderColor: THEME.borderColor },
      timeScale: {
        borderColor: THEME.borderColor,
        timeVisible: true,
        secondsVisible: false,
        fixRightEdge: true,
      },
      handleScroll: { vertTouchDrag: false },
      autoSize: true,
    })

    const candleSeries = chart.addSeries(CandlestickSeries, {
      upColor: THEME.upColor,
      downColor: THEME.downColor,
      borderUpColor: THEME.upColor,
      borderDownColor: THEME.downColor,
      wickUpColor: THEME.wickUpColor,
      wickDownColor: THEME.wickDownColor,
    })

    const volumeSeries = chart.addSeries(HistogramSeries, {
      priceFormat: { type: "volume" },
      priceScaleId: "volume",
    });
    (chart as any).priceScale("volume").applyOptions({
      scaleMargins: { top: 0.8, bottom: 0 },
      visible: true,
    })

    chartRef.current = chart
    candleSeriesRef.current = candleSeries as any
    volumeSeriesRef.current = volumeSeries as any
    markersPluginRef.current = createSeriesMarkers(candleSeries as any)

    const handleResize = () => {
      if (containerRef.current) {
        chart.resize(containerRef.current.clientWidth, containerRef.current.clientHeight)
      }
    }
    window.addEventListener("resize", handleResize)

    return () => {
      window.removeEventListener("resize", handleResize)
      chart.remove()
      chartRef.current = null
      candleSeriesRef.current = null
      volumeSeriesRef.current = null
    }
  }, [containerRef])

  // ── Candle data ──
  useEffect(() => {
    if (!candleSeriesRef.current || !volumeSeriesRef.current) return

    const cd = candles.map((c) => ({
      time: (new Date(c.time).getTime() / 1000) as Time,
      open: c.open,
      high: c.high,
      low: c.low,
      close: c.close,
    }))

    const vd = candles.map((c) => ({
      time: (new Date(c.time).getTime() / 1000) as Time,
      value: c.volume,
      color: c.close >= c.open ? THEME.upColor + "40" : THEME.downColor + "40",
    }))

    candleSeriesRef.current.setData(cd)
    volumeSeriesRef.current.setData(vd)

    if (autoScale && chartRef.current) {
      chartRef.current.timeScale().fitContent()
    }
  }, [candles, autoScale])

  // ── Markers ──
  useEffect(() => {
    if (!markersPluginRef.current) return
    markersPluginRef.current.setMarkers(
      markers.map((m) => ({
        time: (new Date(m.time).getTime() / 1000) as Time,
        position: m.position as "aboveBar" | "belowBar" | "inBar",
        color: m.color,
        shape: m.shape as "circle" | "arrowUp" | "arrowDown",
        text: m.text,
      }))
    )
  }, [markers])

  // ── Horizontal lines (existing, backward compat) ──
  useEffect(() => {
    if (!chartRef.current) return
    hLineMap.current.forEach((s: any) => {
      try { chartRef.current!.removeSeries(s) } catch {}
    })
    hLineMap.current.clear()

    horizontalLines.forEach((line) => {
      const s = chartRef.current!.addSeries(LineSeries, {
        color: line.color,
        lineStyle: line.lineStyle === "dashed" ? 2 : line.lineStyle === "dotted" ? 3 : 0,
        lineWidth: (line.width ?? 1) as any,
        lastValueVisible: false,
        priceLineVisible: false,
        title: line.title,
      })
      const time = (new Date(line.time).getTime() / 1000) as Time
      s.setData([
        { time: time as any, value: line.price },
        { time: (time as number) + 3600 as any, value: line.price },
      ])
      hLineMap.current.set("h_" + line.title + "_" + line.price, s)
    })
  }, [horizontalLines])

  // ── Indicator Series (Phase 6) ──
  useEffect(() => {
    if (!chartRef.current) return

    // Remove stale indicator series
    const currentKeys = new Set(indicatorSeries.map((s) => s.id))
    indicatorMap.current.forEach((series: any, key: string) => {
      if (!currentKeys.has(key)) {
        try { chartRef.current!.removeSeries(series) } catch {}
        indicatorMap.current.delete(key)
      }
    })

    // Add/update indicator series
    indicatorSeries.forEach((indicator) => {
      let s = indicatorMap.current.get(indicator.id)
      if (!s) {
        s = chartRef.current!.addSeries(LineSeries, {
          color: indicator.color,
          lineStyle: indicator.lineStyle === "dashed" ? 2 : indicator.lineStyle === "dotted" ? 3 : 0,
          lineWidth: indicator.lineWidth as any,
          lastValueVisible: true,
          priceLineVisible: false,
          title: indicator.label,
          visible: indicator.visible !== false,
        })
        indicatorMap.current.set(indicator.id, s)
      }
      const data = indicator.data
        .filter((d) => d.value != null)
        .map((d) => ({
          time: (new Date(d.time).getTime() / 1000) as Time,
          value: d.value,
        }))
      s.setData(data)
      s.applyOptions({ visible: indicator.visible !== false })
    })
  }, [indicatorSeries])

  // ── Trend Lines (Phase 6) ──
  useEffect(() => {
    if (!chartRef.current) return

    const currentKeys = new Set(trendLines.map((l) => l.id))
    trendLineMap.current.forEach((series: any, key: string) => {
      if (!currentKeys.has(key)) {
        try { chartRef.current!.removeSeries(series) } catch {}
        trendLineMap.current.delete(key)
      }
    })

    trendLines.forEach((line) => {
      if (line.points.length < 2) return
      let s = trendLineMap.current.get(line.id)
      if (!s) {
        s = chartRef.current!.addSeries(LineSeries, {
          color: line.color,
          lineStyle: line.lineStyle === "dashed" ? 2 : line.lineStyle === "dotted" ? 3 : 0,
          lineWidth: line.lineWidth as any,
          lastValueVisible: false,
          priceLineVisible: false,
          title: line.label,
          visible: line.visible !== false,
        })
        trendLineMap.current.set(line.id, s)
      }
      const data = line.points.map((p) => ({
        time: (new Date(p.time).getTime() / 1000) as Time,
        value: p.price,
      }))
      s.setData(data)
      s.applyOptions({ visible: line.visible !== false })
    })
  }, [trendLines])

  // ── Zone Area Series (Phase 6) ──
  // Render zones as semi-transparent area fills between top and bottom prices
  useEffect(() => {
    if (!chartRef.current) return

    const currentKeys = new Set(chartZones.map((z) => z.id))
    zoneMap.current.forEach((series: any, key: string) => {
      if (!currentKeys.has(key)) {
        try { chartRef.current!.removeSeries(series) } catch {}
        zoneMap.current.delete(key)
      }
    })

    chartZones.forEach((zone) => {
      let s = zoneMap.current.get(zone.id)
      if (!s) {
        // Use AreaSeries to create a filled zone appearance
        s = chartRef.current!.addSeries(AreaSeries, {
          lineColor: zone.borderColor || zone.color,
          topColor: zone.color,
          bottomColor: zone.color + "10",
          lineWidth: 1 as any,
          lastValueVisible: false,
          priceLineVisible: false,
          title: zone.label,
          visible: zone.visible !== false,
        })
        zoneMap.current.set(zone.id, s)
      }
      const time = (new Date(zone.time).getTime() / 1000) as Time
      // Use an area series at the midpoint with narrow spread to simulate a filled band
      const mid = (zone.top + zone.bottom) / 2
      s.setData([
        { time: time as any, value: mid },
        { time: (time as number) + 3600 as any, value: mid },
      ])
      s.applyOptions({
        topColor: zone.color + "30",
        bottomColor: zone.color + "05",
        lineColor: zone.borderColor || zone.color,
        visible: zone.visible !== false,
      })
    })
  }, [chartZones])

  const fitContent = useCallback(() => chartRef.current?.timeScale().fitContent(), [])

  return { fitContent }
}
