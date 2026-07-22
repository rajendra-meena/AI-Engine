"use client"

import { useQuery } from "@tanstack/react-query"
import { decisionService } from "@/services/decisionService"

export function useDecision(symbol = "NIFTY 50") {
  return useQuery({
    queryKey: ["decision", symbol],
    queryFn: () => decisionService.getLatest(symbol),
    refetchInterval: 30_000,
    staleTime: 10_000,
  })
}
