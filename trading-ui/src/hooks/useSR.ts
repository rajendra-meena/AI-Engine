"use client"

import { useQuery } from "@tanstack/react-query"
import { useMarketStore } from "@/store/useMarketStore"
import { srService } from "@/services/srService"

export function useSR(symbol?: string) {
  const storeSymbol = useMarketStore((s) => s.selectedSymbol)
  const sym = symbol ?? storeSymbol

  return useQuery({
    queryKey: ["sr", sym],
    queryFn: () => srService.getLatest(sym),
    refetchInterval: 30_000,
    staleTime: 10_000,
  })
}
