"use client"

import { useRef, useEffect, useState } from "react"
import { ChartHeader } from "./ChartHeader"
import { ChartContainer } from "@/components/chart/ChartContainer"
import type { ChartConfig, SyncMode } from "@/store/useWorkspaceStore"

interface ChartViewportProps {
  chart: ChartConfig
  isFullscreen: boolean
  isFloating: boolean
  onFullscreen: () => void
  onDetach: () => void
  onRemove: () => void
  onSymbolChange: (symbol: string) => void
  onIntervalChange: (interval: string) => void
  onSyncChange: (mode: SyncMode, enable: boolean) => void
}

export function ChartViewport({
  chart, isFullscreen, isFloating,
  onFullscreen, onDetach, onRemove,
  onSymbolChange, onIntervalChange, onSyncChange,
}: ChartViewportProps) {
  const containerRef = useRef<HTMLDivElement>(null)
  const [loaded, setLoaded] = useState(false)

  useEffect(() => {
    const timer = setTimeout(() => setLoaded(true), 50)
    return () => clearTimeout(timer)
  }, [])

  return (
    <div ref={containerRef} className="flex flex-col h-full rounded-lg border bg-card overflow-hidden">
      <ChartHeader
        chart={chart}
        isFullscreen={isFullscreen}
        isFloating={isFloating}
        onFullscreen={onFullscreen}
        onDetach={onDetach}
        onRemove={onRemove}
        onSymbolChange={onSymbolChange}
        onIntervalChange={onIntervalChange}
        onSyncChange={onSyncChange}
      />
      <div className="flex-1 min-h-0">
        {loaded ? <ChartContainer /> : <div className="flex items-center justify-center h-full text-[9px] text-muted-foreground">Loading...</div>}
      </div>
    </div>
  )
}
