"use client"

import { cn } from "@/lib/utils"
import type { ChartConfig, ChartLayout } from "@/store/useWorkspaceStore"
import { workspaceService } from "@/services/workspaceService"

interface MiniMapNavigatorProps {
  charts: ChartConfig[]
  layout: ChartLayout
  activeChartId: string | null
  onSelectChart: (id: string) => void
  className?: string
}

export function MiniMapNavigator({ charts, layout, activeChartId, onSelectChart, className }: MiniMapNavigatorProps) {
  const dims = workspaceService.getGridDimensions(layout)

  return (
    <div className={cn("rounded-lg border bg-card p-2", className)}>
      <div className="text-[9px] font-medium text-muted-foreground uppercase tracking-wider mb-1">Mini Map</div>
      <div className="grid gap-0.5" style={{ gridTemplateColumns: `repeat(${dims.cols}, 1fr)`, gridTemplateRows: `repeat(${dims.rows}, 40px)` }}>
        {charts.map((chart) => (
          <button
            key={chart.id}
            onClick={() => onSelectChart(chart.id)}
            className={cn(
              "rounded border text-[7px] font-mono font-medium transition-colors flex items-center justify-center",
              activeChartId === chart.id ? "border-primary bg-primary/10 text-primary" : "border-border bg-muted/20 text-muted-foreground hover:bg-accent",
            )}
          >
            {chart.symbol.slice(0, 6)}
          </button>
        ))}
      </div>
    </div>
  )
}
