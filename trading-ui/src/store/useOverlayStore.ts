import { create } from "zustand"
import { persist } from "zustand/middleware"

/* ── Indicator color and style presets ── */

export const INDICATOR_COLORS = {
  ema_9: "#6366f1",
  ema_20: "#f59e0b",
  ema_50: "#10b981",
  ema_200: "#ef4444",
  sma_20: "#ec4899",
  sma_50: "#8b5cf6",
  vwap: "#f97316",
  supertrend: "#22c55e",
} as const

export const INDICATOR_LABELS = {
  ema_9: "EMA 9",
  ema_20: "EMA 20",
  ema_50: "EMA 50",
  ema_200: "EMA 200",
  sma_20: "SMA 20",
  sma_50: "SMA 50",
  vwap: "VWAP",
  supertrend: "SuperTrend",
} as const

export type IndicatorId = keyof typeof INDICATOR_COLORS

export interface IndicatorConfig {
  visible: boolean
  color: string
  width: number
  label: string
}

export interface OverlayState {
  /* Toggle flags (keep original for backward compat) */
  ema: boolean
  sma: boolean
  vwap: boolean
  supertrend: boolean
  patterns: boolean
  structure: boolean
  bos: boolean
  choch: boolean
  sr: boolean
  supplyDemand: boolean
  liquidity: boolean
  ai: boolean
  labels: boolean
  targets: boolean

  /* Per-indicator config */
  indicatorConfig: Record<IndicatorId, IndicatorConfig>

  /* Zone and trend line visibility */
  zoneLabels: boolean
  trendLines: boolean
  markerLabels: boolean

  /* Animation enabled */
  animations: boolean

  /* Actions */
  toggle: (key: keyof OverlayState) => void
  setAll: (value: boolean) => void
  setIndicatorConfig: (id: IndicatorId, config: Partial<IndicatorConfig>) => void
  setIndicatorColor: (id: IndicatorId, color: string) => void
  setIndicatorWidth: (id: IndicatorId, width: number) => void
  setIndicatorVisible: (id: IndicatorId, visible: boolean) => void
}

const defaultIndicatorConfig = (): Record<IndicatorId, IndicatorConfig> => ({
  ema_9: { visible: true, color: INDICATOR_COLORS.ema_9, width: 1, label: INDICATOR_LABELS.ema_9 },
  ema_20: { visible: true, color: INDICATOR_COLORS.ema_20, width: 1, label: INDICATOR_LABELS.ema_20 },
  ema_50: { visible: true, color: INDICATOR_COLORS.ema_50, width: 1, label: INDICATOR_LABELS.ema_50 },
  ema_200: { visible: true, color: INDICATOR_COLORS.ema_200, width: 1, label: INDICATOR_LABELS.ema_200 },
  sma_20: { visible: false, color: INDICATOR_COLORS.sma_20, width: 1, label: INDICATOR_LABELS.sma_20 },
  sma_50: { visible: false, color: INDICATOR_COLORS.sma_50, width: 1, label: INDICATOR_LABELS.sma_50 },
  vwap: { visible: true, color: INDICATOR_COLORS.vwap, width: 1, label: INDICATOR_LABELS.vwap },
  supertrend: { visible: true, color: INDICATOR_COLORS.supertrend, width: 2, label: INDICATOR_LABELS.supertrend },
})

export const useOverlayStore = create<OverlayState>()(
  persist(
    (set) => ({
      /* --- backward-compat toggles --- */
      ema: true,
      sma: false,
      vwap: true,
      supertrend: true,
      patterns: true,
      structure: true,
      bos: true,
      choch: true,
      sr: true,
      supplyDemand: true,
      liquidity: true,
      ai: true,
      labels: true,
      targets: true,

      /* --- per-indicator config --- */
      indicatorConfig: defaultIndicatorConfig(),

      /* --- advanced toggles --- */
      zoneLabels: true,
      trendLines: true,
      markerLabels: true,

      /* animations */
      animations: true,

      /* --- actions --- */
      toggle: (key) => set((s) => ({ [key]: !(s as unknown as Record<string, boolean>)[key] })),
      setAll: (value) =>
        set({
          ema: value, sma: value, vwap: value, supertrend: value,
          patterns: value, structure: value, bos: value, choch: value,
          sr: value, supplyDemand: value, liquidity: value, ai: value,
          labels: value, targets: value,
        }),

      setIndicatorConfig: (id, partial) =>
        set((s) => ({
          indicatorConfig: {
            ...s.indicatorConfig,
            [id]: { ...s.indicatorConfig[id], ...partial },
          },
        })),

      setIndicatorColor: (id, color) =>
        set((s) => ({
          indicatorConfig: {
            ...s.indicatorConfig,
            [id]: { ...s.indicatorConfig[id], color },
          },
        })),

      setIndicatorWidth: (id, width) =>
        set((s) => ({
          indicatorConfig: {
            ...s.indicatorConfig,
            [id]: { ...s.indicatorConfig[id], width },
          },
        })),

      setIndicatorVisible: (id, visible) =>
        set((s) => ({
          indicatorConfig: {
            ...s.indicatorConfig,
            [id]: { ...s.indicatorConfig[id], visible },
          },
        })),
    }),
    { name: "marketmind-overlays" }
  )
)
