"use client"

import { useWorkspace } from "@/hooks/useWorkspace"
import { WorkspaceToolbar } from "./WorkspaceToolbar"
import { WorkspaceGrid } from "./WorkspaceGrid"
import { WorkspaceManager } from "./WorkspaceManager"
import { MiniMapNavigator } from "./MiniMapNavigator"
import { Layout } from "lucide-react"
import { useCallback } from "react"

export function MultiChartWorkspace() {
  const ws = useWorkspace()

  const handleSymbolChange = useCallback((chartId: string, symbol: string) => {
    ws.updateChart(chartId, { symbol })
    if (ws.syncState.crosshair) ws.syncToGroup("main", "symbol", symbol)
  }, [ws])

  const handleIntervalChange = useCallback((chartId: string, interval: string) => {
    ws.updateChart(chartId, { interval })
    ws.setSyncState({ timeframe: interval })
    ws.syncToGroup("main", "interval", interval)
  }, [ws])

  const handleSyncChange = useCallback((chartId: string, mode: string, enable: boolean) => {
    const chart = ws.charts.find((c) => c.id === chartId)
    if (!chart) return
    ws.updateChart(chartId, {
      syncModes: enable
        ? [...chart.syncModes, mode as "crosshair" | "zoom" | "scroll" | "timeframe" | "symbol" | "drawing" | "replay" | "indicator" | "overlay" | "ai"]
        : chart.syncModes.filter((m) => m !== mode),
    })
  }, [ws])

  const handleExport = useCallback(() => {
    if (ws.activeWorkspaceId) {
      const data = ws.exportWorkspace(ws.activeWorkspaceId)
      if (data) {
        const blob = new Blob([JSON.stringify(data, null, 2)], { type: "application/json" })
        const url = URL.createObjectURL(blob)
        const a = document.createElement("a"); a.href = url; a.download = `workspace-${ws.activeWorkspaceId}.json`
        a.click(); URL.revokeObjectURL(url)
      }
    }
  }, [ws])

  const handleImport = useCallback(() => {
    const input = document.createElement("input")
    input.type = "file"; input.accept = ".json"
    input.onchange = async (e) => {
      const file = (e.target as HTMLInputElement).files?.[0]
      if (!file) return
      const text = await file.text()
      try { ws.importWorkspace(JSON.parse(text)) } catch {}
    }
    input.click()
  }, [ws])

  if (!ws.workspaces.length) {
    return (
      <div className="flex flex-col items-center justify-center h-64 gap-3">
        <Layout className="w-8 h-8 text-muted-foreground/30" />
        <div className="text-sm text-muted-foreground">No workspaces yet</div>
        <div className="flex gap-2">
          {ws.templates.slice(0, 3).map((tpl) => (
            <button key={tpl.id} onClick={() => ws.createFromTemplate(tpl)}
              className="rounded-md border bg-card px-3 py-2 text-[10px] font-medium hover:bg-accent transition-colors">
              {tpl.name}
            </button>
          ))}
        </div>
      </div>
    )
  }

  return (
    <div className="flex flex-col h-full">
      <WorkspaceToolbar
        layout={ws.currentLayout}
        chartCount={ws.charts.length}
        fullscreen={ws.fullscreenChart != null}
        monitorMode={ws.monitorMode}
        showMiniMap={ws.showMiniMap}
        showStatus={ws.showStatus}
        onLayoutChange={ws.setLayout}
        onFullscreen={() => ws.setFullscreenChart(ws.fullscreenChart ? null : ws.charts[0]?.id ?? null)}
        onMonitorMode={() => ws.setMonitorMode(!ws.monitorMode)}
        onExport={handleExport}
        onImport={handleImport}
        onToggleMiniMap={() => ws.setShowMiniMap(!ws.showMiniMap)}
        onToggleStatus={() => ws.setShowStatus(!ws.showStatus)}
      />

      <div className="flex flex-1 overflow-hidden">
        {/* Sidebar */}
        <div className="w-48 shrink-0 border-r p-1 space-y-1 overflow-y-auto hidden lg:flex lg:flex-col">
          <WorkspaceManager
            workspaces={ws.workspaces}
            activeId={ws.activeWorkspaceId}
            templates={ws.templates}
            onSelect={ws.setActiveWorkspace}
            onAddTemplate={ws.createFromTemplate}
            onDuplicate={ws.duplicateWorkspace}
            onRemove={ws.removeWorkspace}
            onRename={ws.renameWorkspace}
            onExport={() => {}}
            onImport={() => {}}
          />
          {ws.showMiniMap && (
            <MiniMapNavigator
              charts={ws.charts}
              layout={ws.currentLayout}
              activeChartId={null}
              onSelectChart={(id) => ws.setFullscreenChart(id)}
            />
          )}
        </div>

        {/* Main grid */}
        <div className="flex-1 p-2 overflow-auto">
          <WorkspaceGrid
            charts={ws.charts}
            gridClass={ws.getGridClass(ws.currentLayout)}
            fullscreenChart={ws.fullscreenChart}
            onFullscreen={ws.setFullscreenChart}
            onDetach={ws.toggleFloatingChart}
            onRemove={ws.removeChart}
            onSymbolChange={handleSymbolChange}
            onIntervalChange={handleIntervalChange}
            onSyncChange={handleSyncChange}
          />
        </div>
      </div>
    </div>
  )
}
