"use client"

import { useCallback, useMemo } from "react"
import { useQuery } from "@tanstack/react-query"
import { predictionService } from "@/services/predictionService"
import { usePortfolioStore } from "@/store/usePortfolioStore"
import { paperTradingService, type OrderRequest } from "@/services/paperTradingService"
import type { ClosedTrade, Position } from "@/store/usePortfolioStore"

/**
 * usePortfolio — central hook for the Portfolio & Paper Trading Workspace.
 *
 * Integrates with existing prediction APIs for trade data and the
 * paperTradingService for simulated order execution.
 */
export function usePortfolio() {
  const store = usePortfolioStore()

  /* ── Fetch prediction stats for win rate / analytics ── */
  const { data: statsData } = useQuery({
    queryKey: ["portfolio-stats"],
    queryFn: () => predictionService.getStats("NIFTY 50"),
    refetchInterval: 60_000,
    staleTime: 30_000,
    retry: 2,
  })

  /* ── Portfolio summary derived from positions + stats ── */
  const summary = useMemo(() => {
    const open = store.positions
    const totalValue = store.paperCapital + open.reduce((a, p) => a + p.pnl, 0)
    const usedMargin = open.reduce((a, p) => a + p.entry * p.quantity, 0)
    const openPnL = open.reduce((a, p) => a + p.pnl, 0)
    const closedCount = store.closedTrades.length
    const wins = store.closedTrades.filter((t) => (t.pnl ?? 0) > 0).length
    const avgRR = store.closedTrades.length > 0
      ? store.closedTrades.reduce((a, t) => a + (t.rr ?? 0), 0) / store.closedTrades.length
      : 0

    return {
      totalValue,
      todayPnL: openPnL,
      totalPnL: openPnL + store.closedTrades.reduce((a, t) => a + (t.pnl ?? 0), 0),
      openPositions: open.length,
      closedPositions: closedCount,
      winRate: closedCount > 0 ? (wins / closedCount) * 100 : (statsData?.hit_rate ?? 0),
      avgRR,
      availableMargin: totalValue - usedMargin,
      usedMargin,
      exposure: totalValue > 0 ? (usedMargin / totalValue) * 100 : 0,
      capitalAllocation: store.paperCapital,
      paperCapital: store.paperCapital,
    }
  }, [store.positions, store.closedTrades, store.paperCapital, statsData])

  /* ── Actions ── */

  const placeOrder = useCallback(async (request: OrderRequest) => {
    const result = await paperTradingService.executeOrder(request)
    if (result.success && result.order && result.position) {
      store.addOrder(result.order)
      store.addPosition(result.position)
    }
    return result
  }, [store])

  const closePosition = useCallback(async (position: Position, reason = "manual") => {
    const { exitPrice, pnl } = await paperTradingService.closePosition(position, reason)
    const duration = Math.round((Date.now() - new Date(position.openedAt).getTime()) / 3600000)
    const closedTrade: ClosedTrade = {
      ...position,
      exit: exitPrice,
      duration,
      exitReason: reason,
      aiDecision: null,
      pattern: null,
      trend: null,
      notes: null,
      status: "closed",
      closedAt: new Date().toISOString(),
    }
    store.closePosition(position.id, closedTrade)
    store.addJournalEntry({
      id: `journal_${Date.now()}`,
      tradeId: position.id,
      symbol: position.symbol,
      entry: position.entry,
      exit: exitPrice,
      direction: position.direction,
      reason,
      aiScore: position.aiScore,
      aiConfidence: position.aiConfidence,
      structure: null,
      pattern: null,
      result: pnl >= 0 ? "win" : "loss",
      notes: "",
      createdAt: new Date().toISOString(),
    })
    return { exitPrice, pnl }
  }, [store])

  const modifySL = useCallback((positionId: string, newSL: number) => {
    const modified = paperTradingService.modifyStopLoss(
      store.positions.find((p) => p.id === positionId)!,
      newSL,
    )
    store.updatePosition(positionId, modified)
  }, [store])

  const moveToBreakEven = useCallback((positionId: string) => {
    const pos = store.positions.find((p) => p.id === positionId)
    if (!pos) return
    store.updatePosition(positionId, paperTradingService.moveToBreakEven(pos))
  }, [store])

  return {
    /* state */
    summary,
    positions: store.positions,
    closedTrades: store.closedTrades,
    orders: store.orders,
    journal: store.journal,
    watchlists: store.watchlists,
    analytics: store.analytics,
    activeTab: store.activeTab,
    paperCapital: store.paperCapital,
    maxRiskPercent: store.maxRiskPercent,
    defaultLotSize: store.defaultLotSize,

    /* actions */
    setActiveTab: store.setActiveTab,
    placeOrder,
    closePosition,
    modifySL,
    moveToBreakEven,
    setPaperCapital: store.setPaperCapital,
    setMaxRiskPercent: store.setMaxRiskPercent,
    setDefaultLotSize: store.setDefaultLotSize,
    addWatchlist: store.addWatchlist,
    removeWatchlist: store.removeWatchlist,
    addToWatchlist: store.addToWatchlist,
    removeFromWatchlist: store.removeFromWatchlist,
    addJournalEntry: store.addJournalEntry,
  }
}
