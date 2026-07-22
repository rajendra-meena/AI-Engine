/**
 * workspaceService.ts
 *
 * Multi-Chart Workspace management — layout, templates, export/import.
 */

import { useWorkspaceStore, type ChartLayout, type WorkspaceLayout, type WorkspaceTemplate, type ChartConfig } from "@/store/useWorkspaceStore"

export const workspaceService = {
  /**
   * Create a workspace from a template.
   */
  createFromTemplate(template: WorkspaceTemplate): WorkspaceLayout {
    const charts: ChartConfig[] = template.presets.map((p, i) => ({
      id: `chart_${Date.now()}_${i}`,
      symbol: p.symbol,
      interval: p.interval,
      position: i,
      syncModes: ["timeframe", "crosshair"],
      syncedGroup: i === 0 ? "main" : null,
      detached: false,
      indicators: true, overlays: true, ai: true,
    }))

    const ws: WorkspaceLayout = {
      id: `ws_${Date.now()}`,
      name: template.name,
      template: template.id,
      layout: template.layout,
      charts,
      syncedGroups: { main: { label: "Main Group", modes: ["timeframe", "crosshair"] } },
    }

    return ws
  },

  /**
   * Export workspace as JSON.
   */
  exportWorkspace(id: string): WorkspaceLayout | null {
    const ws = useWorkspaceStore.getState().workspaces.find((w) => w.id === id)
    return ws ?? null
  },

  /**
   * Import workspace from JSON.
   */
  importWorkspace(data: WorkspaceLayout): boolean {
    if (!data.id || !data.name || !Array.isArray(data.charts)) return false
    useWorkspaceStore.getState().addWorkspace(data)
    return true
  },

  /**
   * Get the chart grid dimensions for a layout.
   */
  getGridDimensions(layout: ChartLayout): { cols: number; rows: number } {
    switch (layout) {
      case "single": return { cols: 1, rows: 1 }
      case "2h": return { cols: 2, rows: 1 }
      case "2v": return { cols: 1, rows: 2 }
      case "4": return { cols: 2, rows: 2 }
      case "6": return { cols: 3, rows: 2 }
      case "8": return { cols: 4, rows: 2 }
    }
  },

  /**
   * Sync a value across all charts in a sync group.
   */
  syncToGroup(groupId: string | null, key: string, value: unknown): void {
    if (!groupId) return
    const state = useWorkspaceStore.getState()
    const ws = state.workspaces.find((w) => w.id === state.activeWorkspaceId)
    if (!ws) return
    ws.charts.filter((c) => c.syncedGroup === groupId).forEach((chart) => {
      if (key === "symbol") state.updateChart(chart.id, { symbol: value as string })
      if (key === "interval") state.updateChart(chart.id, { interval: value as string })
    })
  },

  /**
   * Layout grid class generation.
   */
  getGridClass(layout: ChartLayout): string {
    switch (layout) {
      case "single": return "grid-cols-1 grid-rows-1"
      case "2h": return "grid-cols-2 grid-rows-1"
      case "2v": return "grid-cols-1 grid-rows-2"
      case "4": return "grid-cols-2 grid-rows-2"
      case "6": return "grid-cols-3 grid-rows-2"
      case "8": return "grid-cols-4 grid-rows-2"
    }
  },
}
