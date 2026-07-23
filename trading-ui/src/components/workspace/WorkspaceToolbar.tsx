"use client"

import { LayoutSelector } from "./LayoutSelector"
import { WorkspaceStatus } from "./WorkspaceStatus"
import { Maximize2, Minimize2, Monitor, Map, Eye } from "lucide-react"
import { cn } from "@/lib/utils"
import type { ChartLayout } from "@/store/useWorkspaceStore"

interface WorkspaceToolbarProps {
  layout: ChartLayout
  chartCount: number
  fullscreen: boolean
  monitorMode: boolean
  showMiniMap: boolean
  showStatus: boolean
  onLayoutChange: (layout: ChartLayout) => void
  onFullscreen: () => void
  onMonitorMode: () => void
  onExport?: () => void
  onImport?: () => void
  onToggleMiniMap: () => void
  onToggleStatus: () => void
  className?: string
}

export function WorkspaceToolbar({
  layout, chartCount, fullscreen, monitorMode, showMiniMap, showStatus,
  onLayoutChange, onFullscreen, onMonitorMode,
  onToggleMiniMap, onToggleStatus, className,
}: WorkspaceToolbarProps) {
  return (
    <div className={cn("flex items-center gap-1.5 px-2 py-1.5 border-b bg-card shrink-0", className)}>
      <LayoutSelector current={layout} onSelect={onLayoutChange} />
      <div className="w-px h-4 bg-border mx-1" />
      <button onClick={onFullscreen} className={cn("rounded p-1 transition-colors", fullscreen ? "text-primary" : "text-muted-foreground hover:bg-accent hover:text-foreground")} title="Fullscreen">
        {fullscreen ? <Minimize2 className="w-3.5 h-3.5" /> : <Maximize2 className="w-3.5 h-3.5" />}
      </button>
      <button onClick={onMonitorMode} className={cn("rounded p-1 transition-colors", monitorMode ? "text-primary" : "text-muted-foreground hover:bg-accent hover:text-foreground")} title="Monitor Mode">
        <Monitor className="w-3.5 h-3.5" />
      </button>
      <div className="w-px h-4 bg-border mx-1" />
      <button onClick={onToggleMiniMap} className={cn("rounded p-1 transition-colors", showMiniMap ? "text-primary" : "text-muted-foreground hover:bg-accent hover:text-foreground")} title="Mini Map">
        <Map className="w-3.5 h-3.5" />
      </button>
      <button onClick={onToggleStatus} className={cn("rounded p-1 transition-colors", showStatus ? "text-primary" : "text-muted-foreground hover:bg-accent hover:text-foreground")} title="Status">
        <Eye className="w-3.5 h-3.5" />
      </button>
      <div className="flex-1" />
      <WorkspaceStatus chartCount={chartCount} />
    </div>
  )
}
