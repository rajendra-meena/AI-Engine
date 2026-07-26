"use client"

import { useQuery } from "@tanstack/react-query"
import { useMarketStore } from "@/store/useMarketStore"
import { aiDecisionService } from "@/services/aiDecisionService"

export function useAIValidation(symbol?: string) {
  const storeSymbol = useMarketStore((s) => s.selectedSymbol)
  const sym = symbol ?? storeSymbol

  return useQuery({
    queryKey: ["ai-validation", sym],
    queryFn: () => aiDecisionService.getDecision(sym),
    refetchInterval: 30_000,
    staleTime: 10_000,
  })
}

export function useConfidenceDetail(symbol?: string) {
  const storeSymbol = useMarketStore((s) => s.selectedSymbol)
  const sym = symbol ?? storeSymbol

  return useQuery({
    queryKey: ["ai-confidence", sym],
    queryFn: () => aiDecisionService.getConfidence(sym),
    refetchInterval: 30_000,
    staleTime: 10_000,
  })
}

export function useSignalQuality(symbol?: string) {
  const storeSymbol = useMarketStore((s) => s.selectedSymbol)
  const sym = symbol ?? storeSymbol

  return useQuery({
    queryKey: ["ai-quality", sym],
    queryFn: () => aiDecisionService.getQuality(sym),
    refetchInterval: 30_000,
    staleTime: 10_000,
  })
}

export function useMTFAgreement(symbol?: string) {
  const storeSymbol = useMarketStore((s) => s.selectedSymbol)
  const sym = symbol ?? storeSymbol

  return useQuery({
    queryKey: ["ai-agreement", sym],
    queryFn: () => aiDecisionService.getAgreement(sym),
    refetchInterval: 30_000,
    staleTime: 10_000,
  })
}

export function useFalseSignals(symbol?: string) {
  const storeSymbol = useMarketStore((s) => s.selectedSymbol)
  const sym = symbol ?? storeSymbol

  return useQuery({
    queryKey: ["ai-rejections", sym],
    queryFn: () => aiDecisionService.getRejections(sym),
    refetchInterval: 30_000,
    staleTime: 10_000,
  })
}

export function useTradeApproval(symbol?: string) {
  const storeSymbol = useMarketStore((s) => s.selectedSymbol)
  const sym = symbol ?? storeSymbol

  return useQuery({
    queryKey: ["ai-approval", sym],
    queryFn: () => aiDecisionService.getApproval(sym),
    refetchInterval: 30_000,
    staleTime: 10_000,
  })
}
