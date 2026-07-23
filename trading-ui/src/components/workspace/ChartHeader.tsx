"use client"

import { cn } from "@/lib/utils"
import { MoreHorizontal, Maximize2, Minimize2, X, GripVertical, Link, Link2Off } from "lucide-react"
import type { ChartConfig, SyncMode } from "@/store/useWorkspaceStore"

interface ChartHeaderProps {
  chart: ChartConfig
  isFullscreen: boolean
  isFloating: boolean
  onFullscreen: () => void
  onDetach: () => void
  onRemove: () => void
  onSymbolChange: (symbol: string) => void
  onIntervalChange: (interval: string) => void
  onSyncChange: (mode: SyncMode, enabled: boolean) => void
  className?: string
}

const SYMBOLS = ["NIFTY 50", "BANK NIFTY", "SENSEX"]
const INTERVALS = ["1m", "3m", "5m", "15m", "30m", "60m", "4h", "1d"]

export function ChartHeader({ chart, isFullscreen, onFullscreen, onDetach, onRemove, onSymbolChange, onIntervalChange, className }: ChartHeaderProps) {
  const hasSync = chart.syncedGroup != null

  return (
    <div className={cn("flex items-center gap-1 px-2 py-1 border-b bg-card shrink-0", className)}>
      <GripVertical className="w-3 h-3 text-muted-foreground/30 cursor-grab" />

      {/* Symbol */}
      <select
        value={chart.symbol}
        onChange={(e) => onSymbolChange(e.target.value)}
        className="h-6 rounded border bg-muted/30 px-1.5 text-[9px] font-medium font-mono focus:outline-none focus:ring-1 focus:ring-primary"
      >
        {SYMBOLS.map((s) => <option key={s} value={s}>{s}</option>)}
      </select>

      {/* Interval */}
      <div className="flex gap-0.5">
        {INTERVALS.map((tf) => (
          <button
            key={tf}
            onClick={() => onIntervalChange(tf)}
            className={cn("px-1 py-0.5 rounded text-[8px] font-mono font-medium transition-colors", chart.interval === tf ? "bg-primary/20 text-primary" : "text-muted-foreground hover:bg-accent")}
          >
            {tf}
          </button>
        ))}
      </div>

      <div className="flex-1" />

      {/* Sync indicator */}
      {hasSync && <Link className="w-3 h-3 text-primary" />}
      {!hasSync && <Link2Off className="w-3 h-3 text-muted-foreground/30" />}

      {/* Actions */}
      <button onClick={onFullscreen} className="rounded p-0.5 text-muted-foreground hover:text-foreground hover:bg-accent transition-colors" title={isFullscreen ? "Exit fullscreen" : "Fullscreen"}>
        {isFullscreen ? <Minimize2 className="w-3 h-3" /> : <Maximize2 className="w-3 h-3" />}
      </button>
      <button onClick={onDetach} className="rounded p-0.5 text-muted-foreground hover:text-foreground hover:bg-accent transition-colors" title="Detach">
        <MoreHorizontal className="w-3 h-3" />
      </button>
      <button onClick={onRemove} className="rounded p-0.5 text-muted-foreground hover:text-red-500 hover:bg-accent transition-colors" title="Remove">
        <X className="w-3 h-3" />
      </button>
    </div>
  )
}
