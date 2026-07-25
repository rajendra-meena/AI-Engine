"use client"

import { useQuery } from "@tanstack/react-query"
import { useMarketStore } from "@/store/useMarketStore"
import { contextService } from "@/services/contextService"

export function useContext(symbol?: string, interval?: string) {
  const storeSymbol = useMarketStore((s) => s.selectedSymbol)
  const storeInterval = useMarketStore((s) => s.selectedInterval)
  const sym = symbol ?? storeSymbol
  const ivl = interval ?? storeInterval

  return useQuery({
    queryKey: ["context", sym, ivl],
    queryFn: () => contextService.getLatest(sym, ivl),
    refetchInterval: 30_000,
    staleTime: 10_000,
  })
}
