"use client"

import { useCallback } from "react"
import { cn } from "@/lib/utils"
import { ChartViewport } from "./ChartViewport"
import type { ChartConfig, SyncMode } from "@/store/useWorkspaceStore"

interface WorkspaceGridProps {
  charts: ChartConfig[]
  gridClass: string
  fullscreenChart: string | null
  onFullscreen: (id: string | null) => void
  onDetach: (id: string) => void
  onRemove: (id: string) => void
  onSymbolChange: (id: string, symbol: string) => void
  onIntervalChange: (id: string, interval: string) => void
  onSyncChange: (id: string, mode: SyncMode, enable: boolean) => void
  className?: string
}

export function WorkspaceGrid({ charts, gridClass, fullscreenChart, onFullscreen, onDetach, onRemove, onSymbolChange, onIntervalChange, onSyncChange, className }: WorkspaceGridProps) {
  const handleSymbol = useCallback((id: string) => (symbol: string) => onSymbolChange(id, symbol), [onSymbolChange])
  const handleInterval = useCallback((id: string) => (interval: string) => onIntervalChange(id, interval), [onIntervalChange])
  const handleSync = useCallback((id: string) => (mode: SyncMode, enable: boolean) => onSyncChange(id, mode, enable), [onSyncChange])
  const handleFullscreen = useCallback((id: string) => () => onFullscreen(fullscreenChart === id ? null : id), [fullscreenChart, onFullscreen])
  const handleDetach = useCallback((id: string) => () => onDetach(id), [onDetach])
  const handleRemove = useCallback((id: string) => () => onRemove(id), [onRemove])

  if (!charts.length) {
    return <div className="flex items-center justify-center h-48 text-[10px] text-muted-foreground">No charts. Add a chart or select a layout.</div>
  }

  // Fullscreen mode
  if (fullscreenChart) {
    const chart = charts.find((c) => c.id === fullscreenChart)
    if (!chart) return null
    return (
      <div className="flex-1">
        <ChartViewport
          chart={chart}
          isFullscreen
          isFloating={false}
          onFullscreen={handleFullscreen(chart.id)}
          onDetach={handleDetach(chart.id)}
          onRemove={handleRemove(chart.id)}
          onSymbolChange={handleSymbol(chart.id)}
          onIntervalChange={handleInterval(chart.id)}
          onSyncChange={handleSync(chart.id)}
        />
      </div>
    )
  }

  return (
    <div className={cn("grid gap-2 flex-1", gridClass, className)}>
      {charts.map((chart) => (
        <ChartViewport
          key={chart.id}
          chart={chart}
          isFullscreen={false}
          isFloating={false}
          onFullscreen={handleFullscreen(chart.id)}
          onDetach={handleDetach(chart.id)}
          onRemove={handleRemove(chart.id)}
          onSymbolChange={handleSymbol(chart.id)}
          onIntervalChange={handleInterval(chart.id)}
          onSyncChange={handleSync(chart.id)}
        />
      ))}
    </div>
  )
}
