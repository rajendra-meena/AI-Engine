"use client"

import { cn } from "@/lib/utils"
import { Search, RotateCcw, RefreshCw } from "lucide-react"
import type { AnalyticsFilters } from "@/store/useAnalyticsStore"

interface FilterPanelProps {
  filters: AnalyticsFilters
  onFilterChange: (filters: Partial<AnalyticsFilters>) => void
  onReset: () => void
  onRefresh: () => void
  autoRefresh: boolean
  onAutoRefreshChange: (v: boolean) => void
  className?: string
}

export function FilterPanel({ filters, onFilterChange, onReset, onRefresh, autoRefresh, onAutoRefreshChange, className }: FilterPanelProps) {
  const DIRECTION_OPTIONS = ["LONG", "SHORT", "NEUTRAL"]
  const TIMEFRAME_OPTIONS = ["1m", "3m", "5m", "15m", "30m", "60m"]
  const RESULT_OPTIONS = [{ value: "all", label: "All" }, { value: "win", label: "Wins" }, { value: "loss", label: "Losses" }]

  return (
    <div className={cn("rounded-lg border bg-card p-2 space-y-2", className)}>
      <div className="flex items-center justify-between">
        <span className="text-[9px] font-medium text-muted-foreground uppercase tracking-wider">Filters</span>
        <div className="flex items-center gap-1">
          <button
            onClick={onRefresh}
            className="rounded p-1 text-muted-foreground hover:text-foreground hover:bg-accent transition-colors"
            title="Refresh"
          >
            <RefreshCw className="w-3 h-3" />
          </button>
          <button
            onClick={onReset}
            className="rounded p-1 text-muted-foreground hover:text-foreground hover:bg-accent transition-colors"
            title="Reset Filters"
          >
            <RotateCcw className="w-3 h-3" />
          </button>
          <label className="flex items-center gap-1 text-[8px] text-muted-foreground cursor-pointer">
            <input type="checkbox" checked={autoRefresh} onChange={(e) => onAutoRefreshChange(e.target.checked)} className="rounded" />
            Auto
          </label>
        </div>
      </div>

      <div className="flex flex-wrap gap-1.5">
        {/* Date range */}
        <div className="flex items-center gap-1">
          <input
            type="date"
            value={filters.dateFrom || ""}
            onChange={(e) => onFilterChange({ dateFrom: e.target.value || null })}
            className="h-6 rounded border bg-muted/50 px-1.5 text-[9px] font-mono w-28 focus:outline-none focus:ring-1 focus:ring-primary"
            placeholder="From"
          />
          <span className="text-[8px] text-muted-foreground">-</span>
          <input
            type="date"
            value={filters.dateTo || ""}
            onChange={(e) => onFilterChange({ dateTo: e.target.value || null })}
            className="h-6 rounded border bg-muted/50 px-1.5 text-[9px] font-mono w-28 focus:outline-none focus:ring-1 focus:ring-primary"
            placeholder="To"
          />
        </div>

        {/* Direction */}
        <select
          value={filters.direction || ""}
          onChange={(e) => onFilterChange({ direction: e.target.value || null })}
          className="h-6 rounded border bg-muted/50 px-1.5 text-[9px] focus:outline-none focus:ring-1 focus:ring-primary"
        >
          <option value="">Direction</option>
          {DIRECTION_OPTIONS.map((d) => <option key={d} value={d}>{d}</option>)}
        </select>

        {/* Timeframe */}
        <select
          value={filters.timeframe || ""}
          onChange={(e) => onFilterChange({ timeframe: e.target.value || null })}
          className="h-6 rounded border bg-muted/50 px-1.5 text-[9px] focus:outline-none focus:ring-1 focus:ring-primary"
        >
          <option value="">Timeframe</option>
          {TIMEFRAME_OPTIONS.map((tf) => <option key={tf} value={tf}>{tf}</option>)}
        </select>

        {/* Result */}
        <select
          value={filters.result || "all"}
          onChange={(e) => onFilterChange({ result: (e.target.value || null) as AnalyticsFilters["result"] })}
          className="h-6 rounded border bg-muted/50 px-1.5 text-[9px] focus:outline-none focus:ring-1 focus:ring-primary"
        >
          {RESULT_OPTIONS.map((r) => <option key={r.value} value={r.value}>{r.label}</option>)}
        </select>

        {/* Search */}
        <div className="flex items-center gap-1 bg-muted/50 rounded border px-1.5">
          <Search className="w-3 h-3 text-muted-foreground shrink-0" />
          <input
            type="text"
            value={filters.search}
            onChange={(e) => onFilterChange({ search: e.target.value })}
            placeholder="Search..."
            className="h-6 bg-transparent text-[9px] font-mono w-24 focus:outline-none placeholder:text-muted-foreground/50"
          />
        </div>
      </div>
    </div>
  )
}
