"use client"

import { useQuery } from "@tanstack/react-query"
import { indicatorService } from "@/services/indicatorService"

export function useIndicators(symbol = "NIFTY 50", interval = "15m") {
  return useQuery({
    queryKey: ["indicators", symbol, interval],
    queryFn: () => indicatorService.getLatest(symbol, interval),
    refetchInterval: 30_000,
    staleTime: 10_000,
  })
}
