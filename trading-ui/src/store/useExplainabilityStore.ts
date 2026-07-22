import { create } from "zustand"
import { persist } from "zustand/middleware"

export interface ExplainView {
  expandedSections: Record<string, boolean>
  activeChart: "pie" | "bar" | "treemap"
  showConfidenceGauge: boolean
  showDecisionFlow: boolean
}

interface ExplainabilityState {
  view: ExplainView
  symbol: string
  interval: string

  toggleSection: (section: string) => void
  setActiveChart: (chart: "pie" | "bar" | "treemap") => void
  setShowConfidenceGauge: (v: boolean) => void
  setShowDecisionFlow: (v: boolean) => void
  setSymbol: (symbol: string) => void
  setInterval: (interval: string) => void
  reset: () => void
}

const DEFAULT_VIEW: ExplainView = {
  expandedSections: {
    score: true, confidence: true, risk: true, context: false,
    indicators: false, patterns: false, structure: false, sr: false,
    mtf: false, conflicts: true, reasoning: true, matrix: true,
  },
  activeChart: "bar",
  showConfidenceGauge: true,
  showDecisionFlow: true,
}

export const useExplainabilityStore = create<ExplainabilityState>()(
  persist(
    (set) => ({
      view: { ...DEFAULT_VIEW },
      symbol: "NIFTY 50",
      interval: "15m",

      toggleSection: (section) =>
        set((s) => ({
          view: {
            ...s.view,
            expandedSections: {
              ...s.view.expandedSections,
              [section]: !s.view.expandedSections[section],
            },
          },
        })),

      setActiveChart: (activeChart) =>
        set((s) => ({ view: { ...s.view, activeChart } })),

      setShowConfidenceGauge: (v) =>
        set((s) => ({ view: { ...s.view, showConfidenceGauge: v } })),

      setShowDecisionFlow: (v) =>
        set((s) => ({ view: { ...s.view, showDecisionFlow: v } })),

      setSymbol: (symbol) => set({ symbol }),
      setInterval: (interval) => set({ interval }),
      reset: () => set({ view: { ...DEFAULT_VIEW } }),
    }),
    { name: "marketmind-explainability" }
  )
)
