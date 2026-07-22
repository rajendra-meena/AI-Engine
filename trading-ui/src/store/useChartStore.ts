import { create } from "zustand"
import type { Candle, IndicatorSeriesData, ChartZone, TrendLineData } from "@/types"

export type CrosshairMode = "normal" | "magnet"

export type ChartDrawingTool = "cursor" | "crosshair" | "horizontal" | "vertical" | "trend" | "ray" | "fib"

export interface ChartMarker {
  time: string
  position: "aboveBar" | "belowBar" | "inBar"
  color: string
  shape: "circle" | "arrowUp" | "arrowDown"
  text: string
  size?: number
}

export interface ChartLine {
  time: string
  price: number
  color: string
  lineStyle: "solid" | "dashed" | "dotted"
  title: string
  width?: number
}

export interface ChartSeries {
  time: string
  value: number
  color?: string
  lineWidth?: number
}

interface ChartState {
  symbol: string
  interval: string
  candles: Candle[]
  markers: ChartMarker[]
  seriesLines: ChartSeries[]
  horizontalLines: ChartLine[]

  /* ── Phase 6: Enhanced overlays ── */
  indicatorSeries: IndicatorSeriesData[]   // full time-series lines (EMA, SMA, VWAP, etc.)
  chartZones: ChartZone[]                   // zone rectangles (supply/demand/entry)
  trendLines: TrendLineData[]               // swing point connections, trend lines

  loading: boolean
  error: string | null
  connected: boolean
  drawingTool: ChartDrawingTool
  crosshairMode: CrosshairMode
  autoScale: boolean
  replayMode: boolean
  replayIndex: number

  setSymbol: (symbol: string) => void
  setInterval: (interval: string) => void
  setCandles: (candles: Candle[]) => void
  addCandle: (candle: Candle) => void
  updateLastCandle: (candle: Partial<Candle>) => void
  setMarkers: (markers: ChartMarker[]) => void
  setSeriesLines: (lines: ChartSeries[]) => void
  setHorizontalLines: (lines: ChartLine[]) => void

  /* ── Phase 6 setter actions ── */
  setIndicatorSeries: (series: IndicatorSeriesData[]) => void
  setChartZones: (zones: ChartZone[]) => void
  setTrendLines: (lines: TrendLineData[]) => void

  setLoading: (loading: boolean) => void
  setError: (error: string | null) => void
  setConnected: (connected: boolean) => void
  setDrawingTool: (tool: ChartDrawingTool) => void
  setCrosshairMode: (mode: CrosshairMode) => void
  setAutoScale: (auto: boolean) => void
  setReplayMode: (mode: boolean) => void
  setReplayIndex: (index: number) => void
  clearData: () => void
}

export const useChartStore = create<ChartState>((set) => ({
  symbol: "NIFTY 50",
  interval: "15m",
  candles: [],
  markers: [],
  seriesLines: [],
  horizontalLines: [],

  /* ── Phase 6 ── */
  indicatorSeries: [],
  chartZones: [],
  trendLines: [],

  loading: false,
  error: null,
  connected: false,
  drawingTool: "crosshair",
  crosshairMode: "normal",
  autoScale: true,
  replayMode: false,
  replayIndex: 0,

  setSymbol: (symbol) => set({ symbol }),
  setInterval: (interval) => set({ interval }),
  setCandles: (candles) => set({ candles }),
  addCandle: (candle) => set((s) => ({ candles: [...s.candles, candle] })),
  updateLastCandle: (partial) =>
    set((s) => {
      if (s.candles.length === 0) return s
      const updated = [...s.candles]
      updated[updated.length - 1] = { ...updated[updated.length - 1], ...partial }
      return { candles: updated }
    }),
  setMarkers: (markers) => set({ markers }),
  setSeriesLines: (lines) => set({ seriesLines: lines }),
  setHorizontalLines: (lines) => set({ horizontalLines: lines }),

  /* ── Phase 6 setters ── */
  setIndicatorSeries: (series) => set({ indicatorSeries: series }),
  setChartZones: (zones) => set({ chartZones: zones }),
  setTrendLines: (lines) => set({ trendLines: lines }),

  setLoading: (loading) => set({ loading }),
  setError: (error) => set({ error }),
  setConnected: (connected) => set({ connected }),
  setDrawingTool: (tool) => set({ drawingTool: tool }),
  setCrosshairMode: (mode) => set({ crosshairMode: mode }),
  setAutoScale: (auto) => set({ autoScale: auto }),
  setReplayMode: (mode) => set({ replayMode: mode }),
  setReplayIndex: (index) => set({ replayIndex: index }),
  clearData: () => set({ candles: [], markers: [], seriesLines: [], horizontalLines: [], indicatorSeries: [], chartZones: [], trendLines: [] }),
}))
