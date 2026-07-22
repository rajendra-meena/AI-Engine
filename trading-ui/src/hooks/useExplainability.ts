"use client"

import { useQuery } from "@tanstack/react-query"
import { explainabilityService } from "@/services/explainabilityService"
import { useExplainabilityStore } from "@/store/useExplainabilityStore"

/**
 * useExplainability — single hook for the AI Explainability Center.
 *
 * Fetches decision + context data from all backend engines and computes
 * structured explainability visualizations.
 */
export function useExplainability(symbol = "NIFTY 50", interval = "15m") {
  const store = useExplainabilityStore()

  const { data, isLoading, error, refetch } = useQuery({
    queryKey: ["explainability", symbol, interval],
    queryFn: () => explainabilityService.explain(symbol, interval),
    refetchInterval: 60_000,
    staleTime: 30_000,
    retry: 2,
  })

  return {
    data,
    isLoading,
    error: error?.message ?? null,
    refetch,
    view: store.view,
    toggleSection: store.toggleSection,
    setActiveChart: store.setActiveChart,
    setShowConfidenceGauge: store.setShowConfidenceGauge,
    setShowDecisionFlow: store.setShowDecisionFlow,
    setSymbol: store.setSymbol,
    setInterval: store.setInterval,
  }
}
