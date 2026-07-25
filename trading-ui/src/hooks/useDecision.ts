"use client"

import { useQuery } from "@tanstack/react-query"
import { useMarketStore } from "@/store/useMarketStore"
import { decisionService } from "@/services/decisionService"

export function useDecision(symbol?: string) {
  const storeSymbol = useMarketStore((s) => s.selectedSymbol)
  const sym = symbol ?? storeSymbol

  return useQuery({
    queryKey: ["decision", sym],
    queryFn: () => decisionService.getLatest(sym),
    refetchInterval: 30_000,
    staleTime: 10_000,
  })
}
