"use client"

import { useChartStore, type ChartDrawingTool } from "@/store/useChartStore"
import { cn } from "@/lib/utils"
import { Crosshair, Minus, Move, TrendingUp, Target, Ruler, CircleDot, Maximize2 } from "lucide-react"

const TOOLS: { id: ChartDrawingTool; icon: React.ReactNode; label: string }[] = [
  { id: "crosshair", icon: <Crosshair className="w-3.5 h-3.5" />, label: "Crosshair" },
  { id: "horizontal", icon: <Minus className="w-3.5 h-3.5 rotate-90" />, label: "Horizontal" },
  { id: "vertical", icon: <Minus className="w-3.5 h-3.5" />, label: "Vertical" },
  { id: "trend", icon: <TrendingUp className="w-3.5 h-3.5" />, label: "Trend" },
  { id: "ray", icon: <Move className="w-3.5 h-3.5" />, label: "Ray" },
  { id: "fib", icon: <Ruler className="w-3.5 h-3.5" />, label: "Fibonacci" },
  { id: "cursor", icon: <CircleDot className="w-3.5 h-3.5" />, label: "Cursor" },
]

const TIMEFRAMES = ["1m", "3m", "5m", "15m", "30m", "60m", "4h", "1d"]

interface ChartToolbarProps {
  onToggleReplay?: () => void
  replayMode?: boolean
}

export function ChartToolbar({ onToggleReplay, replayMode }: ChartToolbarProps) {
  const { interval, setInterval, drawingTool, setDrawingTool, autoScale, setAutoScale } = useChartStore()

  return (
    <div className="flex items-center gap-1.5 px-3 py-1.5 border-b bg-card shrink-0 overflow-x-auto">
      {/* Timeframes */}
      <div className="flex items-center rounded-md border overflow-hidden shrink-0">
        {TIMEFRAMES.map((tf) => (
          <button
            key={tf}
            onClick={() => setInterval(tf)}
            className={cn(
              "px-2 py-1 text-[11px] font-medium transition-colors",
              interval === tf ? "bg-primary text-primary-foreground" : "bg-card text-muted-foreground hover:bg-accent"
            )}
          >
            {tf}
          </button>
        ))}
      </div>

      <div className="w-px h-4 bg-border mx-1 shrink-0" />

      {/* Drawing tools */}
      <div className="flex items-center rounded-md border overflow-hidden shrink-0">
        {TOOLS.map((tool) => (
          <button
            key={tool.id}
            onClick={() => setDrawingTool(tool.id)}
            className={cn(
              "p-1.5 transition-colors",
              drawingTool === tool.id ? "bg-primary/20 text-primary" : "text-muted-foreground hover:bg-accent"
            )}
            title={tool.label}
          >
            {tool.icon}
          </button>
        ))}
      </div>

      <div className="w-px h-4 bg-border mx-1 shrink-0" />

      {/* Actions */}
      <button
        onClick={() => setAutoScale(!autoScale)}
        className={cn("p-1.5 rounded transition-colors", autoScale ? "text-primary" : "text-muted-foreground hover:bg-accent")}
        title="Auto scale"
      >
        <Maximize2 className="w-3.5 h-3.5" />
      </button>

      {onToggleReplay && (
        <>
          <div className="w-px h-4 bg-border mx-1 shrink-0" />
          <button
            onClick={onToggleReplay}
            className={cn("px-2 py-1 text-[11px] rounded transition-colors font-medium", replayMode ? "bg-amber-500/20 text-amber-500" : "text-muted-foreground hover:bg-accent")}
          >
            {replayMode ? "Stop Replay" : "Replay"}
          </button>
        </>
      )}
    </div>
  )
}
