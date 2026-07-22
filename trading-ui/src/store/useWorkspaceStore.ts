import { create } from "zustand"
import { persist } from "zustand/middleware"

/* ─── Types ─── */

export type ChartLayout = "single" | "2h" | "2v" | "4" | "6" | "8"
export type SyncMode = "off" | "crosshair" | "zoom" | "scroll" | "timeframe" | "symbol" | "drawing" | "replay" | "indicator" | "overlay" | "ai"

export interface ChartConfig {
  id: string
  symbol: string
  interval: string
  position: number
  syncModes: SyncMode[]
  syncedGroup: string | null
  detached: boolean
  detachedPosition?: { x: number; y: number; width: number; height: number }
  indicators: boolean
  overlays: boolean
  ai: boolean
}

export interface WorkspaceLayout {
  id: string
  name: string
  template: string
  layout: ChartLayout
  charts: ChartConfig[]
  syncedGroups: Record<string, { label: string; modes: SyncMode[] }>
}

export interface WorkspaceTemplate {
  id: string
  name: string
  layout: ChartLayout
  description: string
  presets: Array<{ symbol: string; interval: string }>
}

export interface SyncState {
  crosshair: { time: string | null; price: number | null }
  zoom: { start: number | null; end: number | null }
  timeframe: string | null
  symbol: string | null
  scroll: { position: number | null }
}

/* ─── Store ─── */

interface WorkspaceState {
  activeWorkspaceId: string | null
  workspaces: WorkspaceLayout[]
  templates: WorkspaceTemplate[]
  currentLayout: ChartLayout
  syncState: SyncState
  fullscreenChart: string | null
  monitorMode: boolean
  floatingCharts: string[]
  showMiniMap: boolean
  showStatus: boolean

  /* actions */
  setActiveWorkspace: (id: string) => void
  setLayout: (layout: ChartLayout) => void
  addWorkspace: (ws: WorkspaceLayout) => void
  removeWorkspace: (id: string) => void
  renameWorkspace: (id: string, name: string) => void
  duplicateWorkspace: (id: string) => void
  updateChart: (chartId: string, update: Partial<ChartConfig>) => void
  addChart: (chart: ChartConfig) => void
  removeChart: (chartId: string) => void
  setSyncedGroup: (chartId: string, group: string | null) => void
  setFullscreenChart: (id: string | null) => void
  setMonitorMode: (on: boolean) => void
  toggleFloatingChart: (chartId: string) => void
  setSyncState: (partial: Partial<SyncState>) => void
  setShowMiniMap: (v: boolean) => void
  setShowStatus: (v: boolean) => void
  reset: () => void
}

const DEFAULT_TEMPLATES: WorkspaceTemplate[] = [
  { id: "scalping", name: "Scalping", layout: "4", description: "1m/3m charts for fast trading", presets: [{ symbol: "NIFTY 50", interval: "1m" }, { symbol: "BANK NIFTY", interval: "3m" }] },
  { id: "intraday", name: "Intraday", layout: "2v", description: "15m/30m daily trading", presets: [{ symbol: "NIFTY 50", interval: "15m" }, { symbol: "SENSEX", interval: "15m" }] },
  { id: "swing", name: "Swing", layout: "2h", description: "60m/4h multi-day", presets: [{ symbol: "NIFTY 50", interval: "60m" }, { symbol: "BANK NIFTY", interval: "60m" }] },
  { id: "institutional", name: "Institutional", layout: "6", description: "Full analysis suite", presets: [{ symbol: "NIFTY 50", interval: "15m" }, { symbol: "BANK NIFTY", interval: "15m" }, { symbol: "FIN NIFTY", interval: "15m" }] },
]

const createDefaultChart = (position: number, symbol = "NIFTY 50", interval = "15m"): ChartConfig => ({
  id: `chart_${Date.now()}_${position}`,
  symbol, interval, position,
  syncModes: ["timeframe", "crosshair"],
  syncedGroup: position === 0 ? "main" : null,
  detached: false,
  indicators: true, overlays: true, ai: true,
})

const createDefaultWorkspace = (): WorkspaceLayout => ({
  id: `ws_${Date.now()}`,
  name: "Default Workspace",
  template: "custom",
  layout: "2v",
  charts: [createDefaultChart(0), createDefaultChart(1, "BANK NIFTY")],
  syncedGroups: { main: { label: "Main Group", modes: ["timeframe", "crosshair"] } },
})

export const useWorkspaceStore = create<WorkspaceState>()(
  persist(
    (set, get) => ({
      activeWorkspaceId: null,
      workspaces: [],
      templates: DEFAULT_TEMPLATES,
      currentLayout: "2v",
      syncState: { crosshair: { time: null, price: null }, zoom: { start: null, end: null }, timeframe: "15m", symbol: "NIFTY 50", scroll: { position: null } },
      fullscreenChart: null,
      monitorMode: false,
      floatingCharts: [],
      showMiniMap: true,
      showStatus: true,

      setActiveWorkspace: (id) => {
        const ws = get().workspaces.find((w) => w.id === id) ?? createDefaultWorkspace()
        set({ activeWorkspaceId: id, currentLayout: ws.layout })
      },

      setLayout: (layout) =>
        set((s) => {
          const count: Record<string, number> = { single: 1, "2h": 2, "2v": 2, "4": 4, "6": 6, "8": 8 }
          const num = count[layout] ?? 1
          const currentWs = s.workspaces.find((w) => w.id === s.activeWorkspaceId)
          const charts = currentWs?.charts ?? []
          const updated = charts.slice(0, num)
          while (updated.length < num) {
            updated.push(createDefaultChart(updated.length, s.syncState.symbol ?? "NIFTY 50", s.syncState.timeframe ?? "15m"))
          }
          return { currentLayout: layout, workspaces: s.workspaces.map((w) => w.id === s.activeWorkspaceId ? { ...w, layout, charts: updated } : w) }
        }),

      addWorkspace: (ws) => set((s) => ({ workspaces: [...s.workspaces, ws], activeWorkspaceId: ws.id, currentLayout: ws.layout })),
      removeWorkspace: (id) => set((s) => ({ workspaces: s.workspaces.filter((w) => w.id !== id) })),
      renameWorkspace: (id, name) => set((s) => ({ workspaces: s.workspaces.map((w) => w.id === id ? { ...w, name } : w) })),

      duplicateWorkspace: (id) => set((s) => {
        const orig = s.workspaces.find((w) => w.id === id)
        if (!orig) return s
        const copy = { ...orig, id: `ws_${Date.now()}`, name: `${orig.name} (Copy)` }
        return { workspaces: [...s.workspaces, copy] }
      }),

      updateChart: (chartId, update) => set((s) => ({
        workspaces: s.workspaces.map((w) => w.id === s.activeWorkspaceId ? { ...w, charts: w.charts.map((c) => c.id === chartId ? { ...c, ...update } : c) } : w),
      })),

      addChart: (chart) => set((s) => ({
        workspaces: s.workspaces.map((w) => w.id === s.activeWorkspaceId ? { ...w, charts: [...w.charts, chart] } : w),
      })),

      removeChart: (chartId) => set((s) => ({
        workspaces: s.workspaces.map((w) => w.id === s.activeWorkspaceId ? { ...w, charts: w.charts.filter((c) => c.id !== chartId) } : w),
      })),

      setSyncedGroup: (chartId, group) => set((s) => ({
        workspaces: s.workspaces.map((w) => w.id === s.activeWorkspaceId ? { ...w, charts: w.charts.map((c) => c.id === chartId ? { ...c, syncedGroup: group } : c) } : w),
      })),

      setFullscreenChart: (fullscreenChart) => set({ fullscreenChart }),
      setMonitorMode: (monitorMode) => set({ monitorMode }),
      toggleFloatingChart: (chartId) => set((s) => ({
        floatingCharts: s.floatingCharts.includes(chartId) ? s.floatingCharts.filter((id) => id !== chartId) : [...s.floatingCharts, chartId],
      })),
      setSyncState: (partial) => set((s) => ({ syncState: { ...s.syncState, ...partial } })),
      setShowMiniMap: (showMiniMap) => set({ showMiniMap }),
      setShowStatus: (showStatus) => set({ showStatus }),
      reset: () => set({ workspaces: [], activeWorkspaceId: null, floatingCharts: [], fullscreenChart: null }),
    }),
    {
      name: "marketmind-workspace",
      version: 1,
      partialize: (state) => ({ workspaces: state.workspaces, activeWorkspaceId: state.activeWorkspaceId, templates: state.templates }),
    }
  )
)

// currentWorkspace is resolved in the useWorkspace hook via find()
