"use client"

import { useCallback, useMemo } from "react"
import { useQuery } from "@tanstack/react-query"
import { decisionService } from "@/services/decisionService"
import { structureService } from "@/services/structureService"
import { indicatorService } from "@/services/indicatorService"
import { patternService } from "@/services/patternService"
import { srService } from "@/services/srService"
import { useTradePlannerStore, type ChecklistItemData, type TimelineEvent } from "@/store/useTradePlannerStore"
import { tradePlannerService, type TradePlanInput } from "@/services/tradePlannerService"

/**
 * useTradePlanner — single hook that wires AI Decision data + user-configurable
 * position sizing into the TradePlannerStore.
 *
 * Polls all backend services at 30s intervals.
 */
export function useTradePlanner(symbol = "NIFTY 50", interval = "15m") {
  const store = useTradePlannerStore()

  /* ── Fetch all backend data ── */
  const { data: decisionData } = useQuery({
    queryKey: ["decision", symbol],
    queryFn: () => decisionService.getLatest(symbol),
    refetchInterval: 30_000,
    staleTime: 10_000,
  })

  const { data: structureData } = useQuery({
    queryKey: ["structure", symbol, interval],
    queryFn: () => structureService.getLatest(symbol, interval),
    refetchInterval: 30_000,
    staleTime: 10_000,
  })

  const { data: indicatorData } = useQuery({
    queryKey: ["indicators", symbol, interval],
    queryFn: () => indicatorService.getLatest(symbol, interval),
    refetchInterval: 30_000,
    staleTime: 10_000,
  })

  const { data: patternData } = useQuery({
    queryKey: ["patterns", symbol, interval],
    queryFn: () => patternService.getLatest(symbol, interval),
    refetchInterval: 30_000,
    staleTime: 10_000,
  })

  const { data: srData } = useQuery({
    queryKey: ["sr", symbol],
    queryFn: () => srService.getLatest(symbol),
    refetchInterval: 30_000,
    staleTime: 10_000,
  })

  /* ── Process decision data into trade planner state ── */

  // Derive execution
  useMemo(() => {
    if (!decisionData) return
    const plan = (decisionData.trade_plan ?? {}) as TradePlanInput
    const execution = tradePlannerService.calculateExecutionStatus(
      decisionData.decision,
      decisionData.score,
      decisionData.confidence,
      decisionData.risk_level,
      plan,
    )
    store.setExecution(execution)
  }, [decisionData, store])

  // Derive position sizing
  useMemo(() => {
    const plan = (decisionData?.trade_plan ?? {}) as TradePlanInput
    const entryPrice =
      plan.entry_zone?.price ??
      plan.entry_zone?.top ??
      plan.entry_zone?.bottom ??
      null
    const stoploss = plan.sl_zone?.price ?? null

    const pos = tradePlannerService.calculatePositionSize(
      store.capital,
      store.riskPercent,
      entryPrice,
      stoploss,
      store.lotSize,
      store.brokerChargesPercent,
      store.slippagePoints,
    )
    store.setPosition(pos)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [decisionData, store.capital, store.riskPercent, store.lotSize, store.brokerChargesPercent, store.slippagePoints])

  // Derive risk
  useMemo(() => {
    if (!decisionData) return
    const risk = tradePlannerService.calculateRisk(
      decisionData.risk_level,
      decisionData.risk_score,
      decisionData.max_risk_percent,
    )
    store.setRisk(risk)
  }, [decisionData, store])

  // Derive reward
  useMemo(() => {
    const plan = (decisionData?.trade_plan ?? {}) as TradePlanInput
    const entryPrice =
      plan.entry_zone?.price ??
      plan.entry_zone?.top ??
      plan.entry_zone?.bottom ??
      null
    const stoploss = plan.sl_zone?.price ?? null
    const targets = plan.target_zones || []
    const reward = tradePlannerService.calculateReward(entryPrice, stoploss, targets)
    store.setReward(reward)
  }, [decisionData, store])

  // Derive checklist
  useMemo(() => {
    const execution = useTradePlannerStore.getState().execution
    const risk = useTradePlannerStore.getState().risk
    const checklist: ChecklistItemData[] = tradePlannerService.calculateChecklist(
      structureData ?? null,
      indicatorData ?? null,
      patternData ?? null,
      srData ?? null,
      execution,
      risk,
    )
    store.setChecklist(checklist)
  }, [structureData, indicatorData, patternData, srData, store])

  // Derive timeline
  useMemo(() => {
    const execution = useTradePlannerStore.getState().execution
    const now = new Date().toISOString()
    const timeline: TimelineEvent[] = tradePlannerService.calculateTimeline(execution, now)
    store.setTimeline(timeline)
  }, [store])

  // Reasoning + warnings
  useMemo(() => {
    if (decisionData?.reasoning) {
      store.setReasoning(decisionData.reasoning)
    }
    if (decisionData?.warnings) {
      store.setWarnings(decisionData.warnings)
    }
  }, [decisionData, store])

  /* ── User actions ── */

  const updateCapital = useCallback((capital: number) => store.setCapital(capital), [store])
  const updateRiskPercent = useCallback((percent: number) => store.setRiskPercent(percent), [store])
  const updateLotSize = useCallback((size: number) => store.setLotSize(size), [store])
  const updateBrokerCharges = useCallback((percent: number) => store.setBrokerChargesPercent(percent), [store])
  const updateSlippage = useCallback((points: number) => store.setSlippagePoints(points), [store])

  return {
    /* state */
    position: store.position,
    risk: store.risk,
    reward: store.reward,
    execution: store.execution,
    checklist: store.checklist,
    timeline: store.timeline,
    reasoning: store.reasoning,
    warnings: store.warnings,

    /* config */
    capital: store.capital,
    riskPercent: store.riskPercent,
    lotSize: store.lotSize,
    brokerChargesPercent: store.brokerChargesPercent,
    slippagePoints: store.slippagePoints,

    /* raw data */
    decision: decisionData,
    structure: structureData,
    indicators: indicatorData,
    patterns: patternData,
    sr: srData,

    /* actions */
    updateCapital,
    updateRiskPercent,
    updateLotSize,
    updateBrokerCharges,
    updateSlippage,
  }
}
