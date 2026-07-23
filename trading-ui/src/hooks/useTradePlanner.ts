"use client"

import { useCallback, useRef, useEffect } from "react"
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
 *
 * IMPORTANT: Store mutations use getState() + refs to avoid cascading
 * re-render loops. Never put the full Zustand store object in a dependency
 * array of an effect/memo that also mutates the store.
 */
export function useTradePlanner(symbol = "NIFTY 50", interval = "15m") {
  // Use individual selectors — never the full store object
  const position = useTradePlannerStore((s) => s.position)
  const risk = useTradePlannerStore((s) => s.risk)
  const reward = useTradePlannerStore((s) => s.reward)
  const execution = useTradePlannerStore((s) => s.execution)
  const checklist = useTradePlannerStore((s) => s.checklist)
  const timeline = useTradePlannerStore((s) => s.timeline)
  const reasoning = useTradePlannerStore((s) => s.reasoning)
  const warnings = useTradePlannerStore((s) => s.warnings)
  const capital = useTradePlannerStore((s) => s.capital)
  const riskPercent = useTradePlannerStore((s) => s.riskPercent)
  const lotSize = useTradePlannerStore((s) => s.lotSize)
  const brokerChargesPercent = useTradePlannerStore((s) => s.brokerChargesPercent)
  const slippagePoints = useTradePlannerStore((s) => s.slippagePoints)

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

  // Track previous decision data to avoid redundant store updates
  const prevDecisionRef = useRef<string | null>(null)

  /* ── Sync backend data to store (only on meaningful changes) ── */
  useEffect(() => {
    const decisionKey = JSON.stringify(decisionData?.decision ?? "") + "|" + JSON.stringify(decisionData?.score ?? "")
    if (decisionKey === prevDecisionRef.current) return
    prevDecisionRef.current = decisionKey

    // Only sync when decision data actually changes
    if (!decisionData) return

    const plan = (decisionData.trade_plan ?? {}) as TradePlanInput
    const store = useTradePlannerStore.getState()

    // Execution
    const newExecution = tradePlannerService.calculateExecutionStatus(
      decisionData.decision,
      decisionData.score,
      decisionData.confidence,
      decisionData.risk_level,
      plan,
    )
    store.setExecution(newExecution)

    // Risk
    const newRisk = tradePlannerService.calculateRisk(
      decisionData.risk_level,
      decisionData.risk_score,
      decisionData.max_risk_percent,
    )
    store.setRisk(newRisk)

    // Position sizing
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

    // Reward
    const targets = plan.target_zones || []
    const newReward = tradePlannerService.calculateReward(entryPrice, stoploss, targets)
    store.setReward(newReward)

    // Reasoning + warnings
    if (decisionData.reasoning) store.setReasoning(decisionData.reasoning)
    if (decisionData.warnings) store.setWarnings(decisionData.warnings)
  }, [decisionData])

  // Checklist — separate effect since it depends on different data
  useEffect(() => {
    const store = useTradePlannerStore.getState()
    const checklist: ChecklistItemData[] = tradePlannerService.calculateChecklist(
      structureData ?? null,
      indicatorData ?? null,
      patternData ?? null,
      srData ?? null,
      store.execution,
      store.risk,
    )
    store.setChecklist(checklist)
  }, [structureData, indicatorData, patternData, srData])

  // Timeline — separate effect
  useEffect(() => {
    const store = useTradePlannerStore.getState()
    const now = new Date().toISOString()
    const timeline: TimelineEvent[] = tradePlannerService.calculateTimeline(store.execution, now)
    store.setTimeline(timeline)
  }, [execution])

  /* ── User actions ── */

  const updateCapital = useCallback((v: number) => useTradePlannerStore.getState().setCapital(v), [])
  const updateRiskPercent = useCallback((v: number) => useTradePlannerStore.getState().setRiskPercent(v), [])
  const updateLotSize = useCallback((v: number) => useTradePlannerStore.getState().setLotSize(v), [])
  const updateBrokerCharges = useCallback((v: number) => useTradePlannerStore.getState().setBrokerChargesPercent(v), [])
  const updateSlippage = useCallback((v: number) => useTradePlannerStore.getState().setSlippagePoints(v), [])

  return {
    position,
    risk,
    reward,
    execution,
    checklist,
    timeline,
    reasoning,
    warnings,
    capital,
    riskPercent,
    lotSize,
    brokerChargesPercent,
    slippagePoints,
    decision: decisionData,
    structure: structureData,
    indicators: indicatorData,
    patterns: patternData,
    sr: srData,
    updateCapital,
    updateRiskPercent,
    updateLotSize,
    updateBrokerCharges,
    updateSlippage,
  }
}
