"use client"

import { useQuery } from "@tanstack/react-query"
import { useMarketStore } from "@/store/useMarketStore"
import { patternService } from "@/services/patternService"

export function usePatterns(symbol?: string, interval?: string) {
  const storeSymbol = useMarketStore((s) => s.selectedSymbol)
  const storeInterval = useMarketStore((s) => s.selectedInterval)
  const sym = symbol ?? storeSymbol
  const ivl = interval ?? storeInterval

  return useQuery({
    queryKey: ["patterns", sym, ivl],
    queryFn: () => patternService.getLatest(sym, ivl),
    refetchInterval: 30_000,
    staleTime: 10_000,
  })
}
