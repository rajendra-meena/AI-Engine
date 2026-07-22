"use client"

import { useQuery } from "@tanstack/react-query"
import { structureService } from "@/services/structureService"

export function useStructure(symbol = "NIFTY 50", interval = "15m") {
  return useQuery({
    queryKey: ["structure", symbol, interval],
    queryFn: () => structureService.getLatest(symbol, interval),
    refetchInterval: 30_000,
    staleTime: 10_000,
  })
}
