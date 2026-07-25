"use client"

import { useQuery } from "@tanstack/react-query"
import { useMarketStore } from "@/store/useMarketStore"
import { mtfService } from "@/services/mtfService"

export function useMTF(symbol?: string) {
  const storeSymbol = useMarketStore((s) => s.selectedSymbol)
  const sym = symbol ?? storeSymbol

  return useQuery({
    queryKey: ["mtf", sym],
    queryFn: () => mtfService.getLatest(sym),
    refetchInterval: 30_000,
    staleTime: 10_000,
  })
}
