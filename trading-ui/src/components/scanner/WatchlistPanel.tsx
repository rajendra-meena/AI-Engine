"use client"

import { cn } from "@/lib/utils"
import { Pin, X } from "lucide-react"
import type { WatchlistItem } from "@/store/useScannerStore"

interface WatchlistPanelProps {
  items: WatchlistItem[]
  onRemove: (symbol: string) => void
  onTogglePin: (symbol: string) => void
  onSelect: (symbol: string) => void
  selectedSymbol: string | null
  className?: string
}

export function WatchlistPanel({ items, onRemove, onTogglePin, onSelect, selectedSymbol, className }: WatchlistPanelProps) {
  if (!items.length) {
    return (
      <div className={cn("rounded-lg border bg-card p-3", className)}>
        <div className="text-[9px] font-medium text-muted-foreground uppercase tracking-wider mb-2">Watchlist</div>
        <div className="text-[9px] text-muted-foreground/50 text-center py-2">No symbols yet</div>
      </div>
    )
  }

  const sorted = [...items].sort((a, b) => (a.pinned === b.pinned ? 0 : a.pinned ? -1 : 1))

  return (
    <div className={cn("rounded-lg border bg-card", className)}>
      <div className="text-[9px] font-medium text-muted-foreground uppercase tracking-wider px-3 pt-2 pb-1">Watchlist ({items.length})</div>
      <div className="space-y-0.5 px-2 pb-2 max-h-[200px] overflow-y-auto">
        {sorted.map((item) => (
          <div
            key={item.symbol}
            onClick={() => onSelect(item.symbol)}
            className={cn(
              "flex items-center gap-1 px-1.5 py-1 rounded text-[10px] cursor-pointer transition-colors",
              selectedSymbol === item.symbol ? "bg-muted/30 text-foreground" : "text-muted-foreground hover:bg-muted/20",
            )}
          >
            <button onClick={(e) => { e.stopPropagation(); onTogglePin(item.symbol) }} className="p-0.5">
              <Pin className={cn("w-2.5 h-2.5", item.pinned ? "text-primary fill-primary" : "text-muted-foreground/30")} />
            </button>
            <span className="flex-1 font-medium">{item.symbol}</span>
            <button onClick={(e) => { e.stopPropagation(); onRemove(item.symbol) }} className="p-0.5 opacity-0 hover:opacity-100 transition-opacity">
              <X className="w-2.5 h-2.5 text-muted-foreground/50 hover:text-red-500" />
            </button>
          </div>
        ))}
      </div>
    </div>
  )
}
