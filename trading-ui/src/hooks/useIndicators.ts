"use client"

import { useQuery } from "@tanstack/react-query"
import { useMarketStore } from "@/store/useMarketStore"
import { indicatorService } from "@/services/indicatorService"

export function useIndicators(symbol?: string, interval?: string) {
  const storeSymbol = useMarketStore((s) => s.selectedSymbol)
  const storeInterval = useMarketStore((s) => s.selectedInterval)
  const sym = symbol ?? storeSymbol
  const ivl = interval ?? storeInterval

  return useQuery({
    queryKey: ["indicators", sym, ivl],
    queryFn: () => indicatorService.getLatest(sym, ivl),
    refetchInterval: 30_000,
    staleTime: 10_000,
  })
}
