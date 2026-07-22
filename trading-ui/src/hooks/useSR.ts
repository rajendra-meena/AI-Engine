"use client"

import { useQuery } from "@tanstack/react-query"
import { srService } from "@/services/srService"

export function useSR(symbol = "NIFTY 50") {
  return useQuery({
    queryKey: ["sr", symbol],
    queryFn: () => srService.getLatest(symbol),
    refetchInterval: 30_000,
    staleTime: 10_000,
  })
}
