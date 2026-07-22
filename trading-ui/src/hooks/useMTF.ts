"use client"

import { useQuery } from "@tanstack/react-query"
import { mtfService } from "@/services/mtfService"

export function useMTF(symbol = "NIFTY 50") {
  return useQuery({
    queryKey: ["mtf", symbol],
    queryFn: () => mtfService.getLatest(symbol),
    refetchInterval: 30_000,
    staleTime: 10_000,
  })
}
