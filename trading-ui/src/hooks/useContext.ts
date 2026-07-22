"use client"

import { useQuery } from "@tanstack/react-query"
import { contextService } from "@/services/contextService"

export function useContext(symbol = "NIFTY 50", interval = "15m") {
  return useQuery({
    queryKey: ["context", symbol, interval],
    queryFn: () => contextService.getLatest(symbol, interval),
    refetchInterval: 30_000,
    staleTime: 10_000,
  })
}
