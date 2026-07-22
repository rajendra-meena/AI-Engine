"use client"

import { useCallback, useEffect, useMemo, useRef } from "react"
import { useQuery } from "@tanstack/react-query"
import { scannerService } from "@/services/scannerService"
import { useScannerStore, type ScannerRow } from "@/store/useScannerStore"

/**
 * useScanner — powers the entire Market Scanner.
 *
 * Fetches all symbols from the backend, computes scanner rows,
 * handles auto-refresh, and processes alert rules.
 */
export function useScanner() {
  const store = useScannerStore()
  const prevRowsRef = useRef<ScannerRow[]>([])

  /* ── Fetch scanner data ── */
  const { isLoading, refetch } = useQuery({
    queryKey: ["scanner"],
    queryFn: async () => {
      store.setLoading(true)
      try {
        const rows = await scannerService.scanAll()
        store.setRows(rows)
        store.setLastRefresh(Date.now())
        return rows
      } catch (e) {
        store.setError((e as Error).message)
        throw e
      }
    },
    refetchInterval: store.autoRefresh ? 30_000 : false,
    staleTime: 15_000,
    retry: 2,
  })

  /* ── Alert checking — flash rows that trigger alerts ── */
  useEffect(() => {
    const current = store.rows
    const enabledAlerts = store.alerts.filter((a) => a.enabled)
    if (!enabledAlerts.length) return

    const newFlashes: string[] = []

    for (const row of current) {
      for (const alert of enabledAlerts) {
        let triggered = false
        const val = row[alert.field]
        if (alert.operator === "gt" && val > alert.value) triggered = true
        if (alert.operator === "lt" && val < alert.value) triggered = true
        if (triggered && alert.flash) {
          newFlashes.push(row.symbol)
          break
        }
      }
    }

    if (newFlashes.length) {
      store.addFlashSymbol(newFlashes[0])
      setTimeout(() => store.clearFlashSymbols(), 2000)
    }

    prevRowsRef.current = current
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [store.rows, store.alerts])

  /* ── Filtered & sorted rows ── */
  const filteredRows = useMemo(() => {
    const { filters, sort, watchlist } = store
    let result = [...store.rows]

    // Watchlist filter
    if (filters.watchlist === "favorites") {
      const wlSymbols = new Set(watchlist.map((w) => w.symbol))
      result = result.filter((r) => wlSymbols.has(r.symbol))
    }

    // Direction filters
    if (filters.onlyBuy) result = result.filter((r) => r.institutionalBias === "BULLISH")
    if (filters.onlySell) result = result.filter((r) => r.institutionalBias === "BEARISH")

    // Score/confidence thresholds
    result = result.filter((r) => r.score >= filters.minScore)
    result = result.filter((r) => r.confidence >= filters.minConfidence)

    // Risk filter
    if (filters.maxRisk) {
      const riskOrder = ["LOW", "MEDIUM", "HIGH", "EXTREME"]
      const maxIdx = riskOrder.indexOf(filters.maxRisk)
      result = result.filter((r) => riskOrder.indexOf(r.risk) <= maxIdx)
    }

    // Trend filter
    if (filters.trend) result = result.filter((r) => r.trend === filters.trend)

    // Pattern filter
    if (filters.patternType) result = result.filter((r) => r.pattern?.toLowerCase().includes(filters.patternType!.toLowerCase()))

    // Search
    if (filters.search) {
      const q = filters.search.toLowerCase()
      result = result.filter((r) => r.symbol.toLowerCase().includes(q))
    }

    // Sort
    result.sort((a, b) => {
      const aVal = a[sort.field]
      const bVal = b[sort.field]
      if (typeof aVal === "number" && typeof bVal === "number") {
        return sort.direction === "desc" ? bVal - aVal : aVal - bVal
      }
      const aStr = String(aVal ?? "")
      const bStr = String(bVal ?? "")
      return sort.direction === "desc" ? bStr.localeCompare(aStr) : aStr.localeCompare(bStr)
    })

    return result
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [store.rows, store.filters, store.sort, store.watchlist])

  const pinnedSymbols = useMemo(
    () => store.watchlist.filter((w) => w.pinned).map((w) => w.symbol),
    [store.watchlist],
  )

  const refresh = useCallback(() => refetch(), [refetch])

  return {
    /* state */
    rows: filteredRows,
    allRows: store.rows,
    loading: isLoading || store.loading,
    error: store.error,
    filters: store.filters,
    sort: store.sort,
    watchlist: store.watchlist,
    savedViews: store.savedViews,
    alerts: store.alerts,
    selectedSymbol: store.selectedSymbol,
    autoRefresh: store.autoRefresh,
    lastRefresh: store.lastRefresh,
    flashSymbols: store.flashSymbols,
    pinnedSymbols,

    /* actions */
    setFilters: store.setFilters,
    resetFilters: store.resetFilters,
    setSort: store.setSort,
    setSelectedSymbol: store.setSelectedSymbol,
    setAutoRefresh: store.setAutoRefresh,
    refresh,
    addToWatchlist: store.addToWatchlist,
    removeFromWatchlist: store.removeFromWatchlist,
    togglePin: store.togglePin,
    isWatchlisted: store.isWatchlisted,
    saveView: store.saveView,
    deleteView: store.deleteView,
    loadView: store.loadView,
    toggleAlert: store.toggleAlert,
    updateAlert: store.updateAlert,
  }
}
