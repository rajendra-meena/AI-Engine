"use client"

import { useQuery } from "@tanstack/react-query"
import { patternService } from "@/services/patternService"

export function usePatterns(symbol = "NIFTY 50", interval = "15m") {
  return useQuery({
    queryKey: ["patterns", symbol, interval],
    queryFn: () => patternService.getLatest(symbol, interval),
    refetchInterval: 30_000,
    staleTime: 10_000,
  })
}
