"use client"

import { cn } from "@/lib/utils"
import { useMemo } from "react"

interface ReplayMiniMapProps {
  currentIndex: number
  totalCandles: number
  events: { index: number; type: "decision" | "trade" | "signal"; color: string }[]
}

export function ReplayMiniMap({ currentIndex, totalCandles, events }: ReplayMiniMapProps) {
  const progressPercent = totalCandles > 0 ? (currentIndex / totalCandles) * 100 : 0

  // Generate pixel-like overview bars
  const bars = useMemo(() => {
    if (totalCandles === 0) return []
    const maxBars = 120
    const step = Math.max(1, Math.floor(totalCandles / maxBars))
    const count = Math.min(maxBars, Math.ceil(totalCandles / step))
    return Array.from({ length: count }, (_, i) => {
      const barStart = i * step
      const barEnd = Math.min((i + 1) * step, totalCandles)
      const isActive = currentIndex >= barStart && currentIndex <= barEnd
      const hasEvent = events.some((e) => e.index >= barStart && e.index <= barEnd)
      return { isActive, hasEvent, eventColor: hasEvent ? events.find((e) => e.index >= barStart && e.index <= barEnd)?.color : undefined }
    })
  }, [totalCandles, currentIndex, events])

  return (
    <div className="rounded-md border bg-card p-2 space-y-1">
      <div className="text-[9px] font-medium text-muted-foreground uppercase tracking-wider">Overview</div>

      {/* Bar visualization */}
      <div className="flex gap-[1px] items-end h-8 overflow-hidden">
        {bars.map((bar, i) => (
          <div
            key={i}
            className={cn(
              "flex-1 rounded-[1px] transition-all duration-150",
              bar.isActive ? "h-full bg-primary/60" : "h-3/5 bg-muted-foreground/10",
              bar.hasEvent && !bar.isActive && "bg-amber-500/20"
            )}
            style={bar.isActive && bar.eventColor ? { backgroundColor: bar.eventColor } : undefined}
          />
        ))}
      </div>

      {/* Position indicator */}
      <div className="relative h-0.5 rounded-full bg-muted overflow-hidden">
        <div
          className="absolute inset-y-0 left-0 bg-primary transition-all duration-200 rounded-full"
          style={{ width: `${Math.min(progressPercent, 100)}%` }}
        />
      </div>

      {/* Legend */}
      <div className="flex gap-2 text-[8px] text-muted-foreground">
        <span className="flex items-center gap-1">
          <span className="w-2 h-2 rounded-sm bg-primary/60" /> Position
        </span>
        <span className="flex items-center gap-1">
          <span className="w-2 h-2 rounded-sm bg-amber-500/30" /> Events
        </span>
      </div>
    </div>
  )
}
