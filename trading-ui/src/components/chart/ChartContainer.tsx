"use client"

import { useRef } from "react"
import { useTradingView } from "@/hooks/useTradingView"
import { useChartStore } from "@/store/useChartStore"
import { Skeleton } from "@/components/ui/skeleton"
import { cn } from "@/lib/utils"

interface ChartContainerProps {
  className?: string
}

export function ChartContainer({ className }: ChartContainerProps) {
  const containerRef = useRef<HTMLDivElement | null>(null)
  const { loading, error, connected, candles } = useChartStore()

  useTradingView(containerRef)

  if (error) {
    return (
      <div className={cn("flex items-center justify-center h-full", className)}>
        <div className="text-center space-y-2">
          <div className="text-sm text-destructive font-medium">Failed to load chart</div>
          <div className="text-[10px] text-muted-foreground">{error}</div>
        </div>
      </div>
    )
  }

  return (
    <div className={cn("relative h-full w-full", className)}>
      {loading && candles.length === 0 && (
        <div className="absolute inset-0 z-10 flex items-center justify-center bg-background/80">
          <div className="space-y-3 w-3/4 max-w-md">
            <Skeleton className="h-4 w-full" />
            <Skeleton className="h-4 w-5/6" />
            <Skeleton className="h-4 w-4/6" />
            <Skeleton className="h-20 w-full" />
          </div>
        </div>
      )}

      {candles.length === 0 && !loading && (
        <div className="absolute inset-0 z-10 flex items-center justify-center">
          <div className="text-center">
            <div className="text-sm text-muted-foreground mb-1">No data available</div>
            <div className="text-[10px] text-muted-foreground/50">Select a symbol to view the chart</div>
          </div>
        </div>
      )}

      {/* Connection status indicator */}
      <div className={cn(
        "absolute top-2 right-2 z-20 flex items-center gap-1.5 px-2 py-1 rounded-md text-[10px]",
        connected ? "bg-emerald-500/10 text-emerald-500" : "bg-red-500/10 text-red-500"
      )}>
        <span className={cn("w-1.5 h-1.5 rounded-full", connected ? "bg-emerald-500" : "bg-red-500")} />
        {connected ? "Live" : "Offline"}
      </div>

      <div ref={containerRef} className="h-full w-full" />
    </div>
  )
}
