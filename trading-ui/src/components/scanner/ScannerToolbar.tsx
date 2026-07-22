"use client"

import { Search, RotateCcw, RefreshCw, Save } from "lucide-react"
import { cn } from "@/lib/utils"
import type { ScannerFilters, ScannerSort, SavedView } from "@/store/useScannerStore"

interface ScannerToolbarProps {
  filters: ScannerFilters
  sort: ScannerSort
  savedViews: SavedView[]
  autoRefresh: boolean
  onFilterChange: (filters: Partial<ScannerFilters>) => void
  onReset: () => void
  onRefresh: () => void
  onAutoRefreshChange: (v: boolean) => void
  onSaveView: () => void
  onLoadView: (id: string) => void
  onSortChange: (sort: ScannerSort) => void
  className?: string
}

export function ScannerToolbar({
  filters, sort, savedViews, autoRefresh,
  onFilterChange, onReset, onRefresh, onAutoRefreshChange,
  onSaveView, onLoadView, onSortChange, className,
}: ScannerToolbarProps) {
  return (
    <div className={cn("rounded-lg border bg-card p-2 space-y-2", className)}>
      {/* Row 1: Search + actions */}
      <div className="flex items-center gap-2">
        <div className="flex items-center gap-1 bg-muted/50 rounded border px-2 flex-1 max-w-xs">
          <Search className="w-3 h-3 text-muted-foreground shrink-0" />
          <input
            type="text"
            value={filters.search}
            onChange={(e) => onFilterChange({ search: e.target.value })}
            placeholder="Search symbols..."
            className="h-7 bg-transparent text-[10px] font-mono flex-1 focus:outline-none placeholder:text-muted-foreground/50"
          />
        </div>

        <div className="flex items-center gap-1" />

        <button onClick={onRefresh} className="rounded p-1 text-muted-foreground hover:text-foreground hover:bg-accent transition-colors" title="Refresh">
          <RefreshCw className="w-3.5 h-3.5" />
        </button>
        <button onClick={onReset} className="rounded p-1 text-muted-foreground hover:text-foreground hover:bg-accent transition-colors" title="Reset">
          <RotateCcw className="w-3.5 h-3.5" />
        </button>
        <button onClick={onSaveView} className="rounded p-1 text-muted-foreground hover:text-foreground hover:bg-accent transition-colors" title="Save View">
          <Save className="w-3.5 h-3.5" />
        </button>

        <label className="flex items-center gap-1 text-[8px] text-muted-foreground cursor-pointer ml-2">
          <input type="checkbox" checked={autoRefresh} onChange={(e) => onAutoRefreshChange(e.target.checked)} className="rounded" />
          Auto
        </label>

        {savedViews.length > 0 && (
          <select
            onChange={(e) => e.target.value && onLoadView(e.target.value)}
            className="h-6 rounded border bg-muted/50 px-1.5 text-[9px] focus:outline-none"
          >
            <option value="">Views</option>
            {savedViews.map((v) => <option key={v.id} value={v.id}>{v.name}</option>)}
          </select>
        )}
      </div>

      {/* Row 2: Filters */}
      <div className="flex flex-wrap gap-1.5">
        <select value={filters.trend || ""} onChange={(e) => onFilterChange({ trend: e.target.value || null })}
          className="h-6 rounded border bg-muted/50 px-1.5 text-[9px] focus:outline-none">
          <option value="">Trend</option>
          <option value="UPTREND">Uptrend</option>
          <option value="DOWNTREND">Downtrend</option>
          <option value="RANGING">Ranging</option>
        </select>

        <select value={filters.maxRisk || ""} onChange={(e) => onFilterChange({ maxRisk: e.target.value || null })}
          className="h-6 rounded border bg-muted/50 px-1.5 text-[9px] focus:outline-none">
          <option value="">Risk</option>
          <option value="LOW">Low</option>
          <option value="MEDIUM">Medium</option>
          <option value="HIGH">High</option>
          <option value="EXTREME">Extreme</option>
        </select>

        <select value={filters.watchlist || ""} onChange={(e) => onFilterChange({ watchlist: e.target.value || null })}
          className="h-6 rounded border bg-muted/50 px-1.5 text-[9px] focus:outline-none">
          <option value="">All</option>
          <option value="favorites">Watchlist</option>
        </select>

        <label className="flex items-center gap-1 text-[9px] text-muted-foreground cursor-pointer">
          <input type="checkbox" checked={filters.onlyBuy} onChange={(e) => onFilterChange({ onlyBuy: e.target.checked })} className="rounded" />
          Buy
        </label>
        <label className="flex items-center gap-1 text-[9px] text-muted-foreground cursor-pointer">
          <input type="checkbox" checked={filters.onlySell} onChange={(e) => onFilterChange({ onlySell: e.target.checked })} className="rounded" />
          Sell
        </label>

        <div className="flex items-center gap-1">
          <span className="text-[8px] text-muted-foreground">Score</span>
          <input type="number" value={filters.minScore} onChange={(e) => onFilterChange({ minScore: Number(e.target.value) })}
            className="h-6 w-12 rounded border bg-muted/50 px-1 text-[9px] font-mono focus:outline-none" min={0} max={100} />
          <span className="text-[8px] text-muted-foreground">Conf</span>
          <input type="number" value={filters.minConfidence} onChange={(e) => onFilterChange({ minConfidence: Number(e.target.value) })}
            className="h-6 w-12 rounded border bg-muted/50 px-1 text-[9px] font-mono focus:outline-none" min={0} max={100} />
        </div>

        {/* Sort */}
        <div className="flex items-center gap-1 ml-auto">
          <span className="text-[8px] text-muted-foreground">Sort:</span>
          <select value={sort.field} onChange={(e) => onSortChange({ field: e.target.value as "score" | "confidence" | "rr" | "change" | "volume" | "price" | "symbol", direction: sort.direction })}
            className="h-6 rounded border bg-muted/50 px-1.5 text-[9px] focus:outline-none">
            <option value="score">Score</option>
            <option value="confidence">Confidence</option>
            <option value="rr">RR</option>
            <option value="change">Change</option>
            <option value="volume">Volume</option>
          </select>
          <button
            onClick={() => onSortChange({ field: sort.field, direction: sort.direction === "desc" ? "asc" : "desc" })}
            className="rounded p-1 text-muted-foreground hover:text-foreground hover:bg-accent transition-colors text-[9px]"
          >
            {sort.direction === "desc" ? "↓" : "↑"}
          </button>
        </div>
      </div>
    </div>
  )
}
