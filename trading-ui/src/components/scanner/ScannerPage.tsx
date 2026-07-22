"use client"

import { useScanner } from "@/hooks/useScanner"
import { ScannerToolbar } from "./ScannerToolbar"
import { ScannerTable } from "./ScannerTable"
import { OpportunityCards } from "./OpportunityCards"
import { WatchlistPanel } from "./WatchlistPanel"
import { AlertsPanel } from "./AlertsPanel"
import { Skeleton } from "@/components/ui/skeleton"
import { AlertCircle, RefreshCw, BarChart3 } from "lucide-react"

export function ScannerPage() {
  const scanner = useScanner()

  if (scanner.error && !scanner.loading && scanner.allRows.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center h-64 gap-2">
        <AlertCircle className="w-8 h-8 text-red-500" />
        <div className="text-sm text-red-500">Failed to load scanner</div>
        <button onClick={scanner.refresh} className="flex items-center gap-1 text-xs text-muted-foreground hover:text-foreground">
          <RefreshCw className="w-3 h-3" /> Retry
        </button>
      </div>
    )
  }

  return (
    <div className="space-y-3">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <BarChart3 className="w-4 h-4 text-primary" />
          <h2 className="text-sm font-bold">Market Scanner</h2>
          {scanner.lastRefresh && (
            <span className="text-[8px] text-muted-foreground">
              Updated {new Date(scanner.lastRefresh).toLocaleTimeString()}
            </span>
          )}
        </div>
      </div>

      {/* Toolbar */}
      <ScannerToolbar
        filters={scanner.filters}
        sort={scanner.sort}
        savedViews={scanner.savedViews}
        autoRefresh={scanner.autoRefresh}
        onFilterChange={scanner.setFilters}
        onReset={scanner.resetFilters}
        onRefresh={scanner.refresh}
        onAutoRefreshChange={scanner.setAutoRefresh}
        onSaveView={() => scanner.saveView(`View ${new Date().toLocaleTimeString()}`)}
        onLoadView={scanner.loadView}
        onSortChange={scanner.setSort}
      />

      {/* Main grid */}
      <div className="flex gap-3">
        {/* Left sidebar */}
        <div className="w-48 shrink-0 space-y-2 hidden lg:block">
          <WatchlistPanel
            items={scanner.watchlist}
            onRemove={scanner.removeFromWatchlist}
            onTogglePin={scanner.togglePin}
            onSelect={scanner.setSelectedSymbol}
            selectedSymbol={scanner.selectedSymbol}
          />
          <AlertsPanel
            alerts={scanner.alerts}
            onToggle={scanner.toggleAlert}
            onUpdate={scanner.updateAlert}
          />
        </div>

        {/* Main content */}
        <div className="flex-1 min-w-0 space-y-3">
          {scanner.loading && scanner.allRows.length === 0 ? (
            <div className="space-y-2">
              {Array.from({ length: 5 }).map((_, i) => <Skeleton key={i} className="h-8 rounded" />)}
            </div>
          ) : (
            <>
              <OpportunityCards rows={scanner.rows} />
              <ScannerTable
                rows={scanner.rows}
                sort={scanner.sort}
                watchlist={scanner.watchlist}
                flashSymbols={scanner.flashSymbols}
                selectedSymbol={scanner.selectedSymbol}
                onSelectSymbol={scanner.setSelectedSymbol}
                onToggleWatchlist={(symbol) =>
                  scanner.isWatchlisted(symbol)
                    ? scanner.removeFromWatchlist(symbol)
                    : scanner.addToWatchlist(symbol)
                }
                onTogglePin={scanner.togglePin}
                onSortChange={scanner.setSort}
              />
            </>
          )}
        </div>
      </div>
    </div>
  )
}
