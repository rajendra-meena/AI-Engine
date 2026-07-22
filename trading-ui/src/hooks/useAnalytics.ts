"use client"

import { useMemo, useCallback } from "react"
import { useQuery } from "@tanstack/react-query"
import { analyticsService, type SummaryMetrics, type ConfidenceBin, type RiskBin, type TimeframeMetric, type DecisionHistoryItem } from "@/services/analyticsService"
import { useAnalyticsStore } from "@/store/useAnalyticsStore"

/**
 * useAnalytics — single hook powering the entire AI Analytics Dashboard.
 *
 * Fetches predictions + stats from backend, computes all derived analytics
 * client-side from real data.
 */
export function useAnalytics(symbol = "NIFTY 50") {
  const store = useAnalyticsStore()

  /* ── Fetch predictions ── */
  const predictionsQuery = useQuery({
    queryKey: ["analytics-predictions", symbol],
    queryFn: async () => {
      try {
        const { predictions, total } = await analyticsService.fetchPredictions(symbol, 200)
        store.setPredictions(predictions, total)
        return { predictions, total }
      } catch (e) {
        store.setError((e as Error).message)
        throw e
      }
    },
    refetchInterval: store.autoRefresh ? 60_000 : false,
    staleTime: 30_000,
    retry: 2,
  })

  /* ── Fetch stats ── */
  const statsQuery = useQuery({
    queryKey: ["analytics-stats", symbol],
    queryFn: () => analyticsService.fetchPredictionStats(symbol),
    refetchInterval: store.autoRefresh ? 120_000 : false,
    staleTime: 60_000,
    retry: 2,
  })

  /* ── Fetch latest decision ── */
  const decisionQuery = useQuery({
    queryKey: ["analytics-decision", symbol],
    queryFn: () => analyticsService.fetchLatestDecision(symbol),
    refetchInterval: store.autoRefresh ? 30_000 : false,
    staleTime: 10_000,
    retry: 1,
  })

  /* ── Derived computations ── */
  const predictions = store.predictions
  const stats = statsQuery.data ?? null

  const summary: SummaryMetrics = useMemo(
    () => analyticsService.computeSummary(predictions, stats),
    [predictions, stats],
  )

  const dailyAccuracy = useMemo(
    () => analyticsService.computeAccuracy(predictions, "day"),
    [predictions],
  )

  const weeklyAccuracy = useMemo(
    () => analyticsService.computeAccuracy(predictions, "week"),
    [predictions],
  )

  const monthlyAccuracy = useMemo(
    () => analyticsService.computeAccuracy(predictions, "month"),
    [predictions],
  )

  const confidenceDistribution: ConfidenceBin[] = useMemo(
    () => analyticsService.computeConfidenceDistribution(predictions),
    [predictions],
  )

  const riskDistribution: RiskBin[] = useMemo(
    () => analyticsService.computeRiskDistribution(predictions),
    [predictions],
  )

  const timeframeMetrics: TimeframeMetric[] = useMemo(
    () => analyticsService.computeTimeframeMetrics(predictions),
    [predictions],
  )

  const decisionHistory: DecisionHistoryItem[] = useMemo(
    () => analyticsService.computeDecisionHistory(predictions),
    [predictions],
  )

  /* ── Actions ── */

  const refresh = useCallback(() => {
    predictionsQuery.refetch()
    statsQuery.refetch()
    decisionQuery.refetch()
  }, [predictionsQuery, statsQuery, decisionQuery])

  const exportAll = useCallback(async () => {
    return analyticsService.exportAll(symbol)
  }, [symbol])

  return {
    /* raw data */
    predictions,
    stats: statsQuery.data,
    decision: decisionQuery.data,
    loading: store.loading || predictionsQuery.isLoading,
    error: store.error || predictionsQuery.error?.message || null,

    /* derived metrics */
    summary,
    dailyAccuracy,
    weeklyAccuracy,
    monthlyAccuracy,
    confidenceDistribution,
    riskDistribution,
    timeframeMetrics,
    decisionHistory,

    /* UI state */
    filters: store.filters,
    sort: store.sort,
    pagination: store.pagination,
    view: store.view,
    selectedSymbol: store.selectedSymbol,
    autoRefresh: store.autoRefresh,

    /* actions */
    setFilters: store.setFilters,
    resetFilters: store.resetFilters,
    setSort: store.setSort,
    setPage: store.setPage,
    setPageSize: store.setPageSize,
    setView: store.setView,
    setAutoRefresh: store.setAutoRefresh,
    refresh,
    exportAll,
  }
}
