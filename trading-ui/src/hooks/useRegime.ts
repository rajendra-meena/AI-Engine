"use client"

import { useQuery } from "@tanstack/react-query"
import { useMarketStore } from "@/store/useMarketStore"
import { regimeService } from "@/services/regimeService"

export function useRegime(symbol?: string) {
  const storeSymbol = useMarketStore((s) => s.selectedSymbol)
  const sym = symbol ?? storeSymbol

  return useQuery({
    queryKey: ["regime", sym],
    queryFn: () => regimeService.getCurrent(sym),
    refetchInterval: 30_000,
    staleTime: 10_000,
  })
}

export function useRegimeHistory(symbol?: string, count = 100) {
  const storeSymbol = useMarketStore((s) => s.selectedSymbol)
  const sym = symbol ?? storeSymbol

  return useQuery({
    queryKey: ["regime-history", sym, count],
    queryFn: () => regimeService.getHistory(sym, count),
    refetchInterval: 60_000,
    staleTime: 30_000,
  })
}

export function useRegimeStrategies(symbol?: string) {
  const storeSymbol = useMarketStore((s) => s.selectedSymbol)
  const sym = symbol ?? storeSymbol

  return useQuery({
    queryKey: ["regime-strategies", sym],
    queryFn: () => regimeService.getStrategies(sym),
    refetchInterval: 30_000,
    staleTime: 10_000,
  })
}

export function useRegimePerformance() {
  return useQuery({
    queryKey: ["regime-performance"],
    queryFn: () => regimeService.getPerformance(),
    refetchInterval: 120_000,
    staleTime: 60_000,
  })
}

export function useRegimeExplanation(symbol?: string) {
  const storeSymbol = useMarketStore((s) => s.selectedSymbol)
  const sym = symbol ?? storeSymbol

  return useQuery({
    queryKey: ["regime-explain", sym],
    queryFn: () => regimeService.getExplain(sym),
    refetchInterval: 30_000,
    staleTime: 10_000,
  })
}

export function useStrategyComparison() {
  return useQuery({
    queryKey: ["strategy-comparison"],
    queryFn: () => regimeService.getComparison(),
    refetchInterval: 300_000,
    staleTime: 120_000,
  })
}
