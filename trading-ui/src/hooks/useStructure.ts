"use client"

import { useQuery } from "@tanstack/react-query"
import { useMarketStore } from "@/store/useMarketStore"
import { structureService } from "@/services/structureService"

export function useStructure(symbol?: string, interval?: string) {
  const storeSymbol = useMarketStore((s) => s.selectedSymbol)
  const storeInterval = useMarketStore((s) => s.selectedInterval)
  const sym = symbol ?? storeSymbol
  const ivl = interval ?? storeInterval

  return useQuery({
    queryKey: ["structure", sym, ivl],
    queryFn: () => structureService.getLatest(sym, ivl),
    refetchInterval: 30_000,
    staleTime: 10_000,
  })
}
