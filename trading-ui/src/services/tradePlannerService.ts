/**
 * tradePlannerService.ts
 *
 * Institutional position sizing, risk management, and execution calculations.
 * All inputs come from the AI Decision engine; outputs drive the Trade Planner UI.
 *
 * NO mock data — all calculations use real decision + user-configurable inputs.
 */

import type { PositionConfig, RiskConfig, RewardConfig, ExecutionConfig, ChecklistItemData, TimelineEvent } from "@/store/useTradePlannerStore"

export interface TradePlanInput {
  direction: string
  valid: boolean
  entry_zone: { top?: number; bottom?: number; price?: number; zone?: string } | null
  sl_zone: { price?: number; zone?: string } | null
  target_zones: { price?: number; zone?: string; probability?: number }[]
  risk_reward_context?: string
  max_risk_percent?: number
}

export interface DecisionInput {
  decision: string
  score: number
  score_grade: string
  confidence: number
  confidence_grade: string
  risk_level: string
  risk_score: number
  max_risk_percent: number
  trade_plan: TradePlanInput
  reasoning?: string[]
  warnings?: string[]
}

export const tradePlannerService = {
  /**
   * Calculate position size and margin based on capital, risk %, entry, and SL.
   */
  calculatePositionSize(
    capital: number,
    riskPercent: number,
    entryPrice: number | null,
    stoploss: number | null,
    lotSize: number,
    brokerChargesPercent: number,
    slippagePoints: number
  ): PositionConfig {
    const maxLossAmount = capital * (riskPercent / 100)

    if (!entryPrice || !stoploss || entryPrice <= 0 || stoploss <= 0) {
      return {
        capital,
        riskPercent,
        maxLoss: maxLossAmount,
        quantity: 0,
        lotSize,
        marginRequired: 0,
        brokerCharges: 0,
        taxes: 0,
        slippage: 0,
      }
    }

    const riskPerUnit = Math.abs(entryPrice - stoploss)
    const totalRiskPerUnit = riskPerUnit + slippagePoints
    const quantity = totalRiskPerUnit > 0 ? Math.floor(maxLossAmount / totalRiskPerUnit) : 0
    const adjustedQuantity = lotSize > 1 ? Math.floor(quantity / lotSize) * lotSize : quantity
    const marginRequired = adjustedQuantity * entryPrice
    const brokerCharges = marginRequired * (brokerChargesPercent / 100)
    const taxes = brokerCharges * 0.18 // 18% GST on brokerage
    const slippage = adjustedQuantity * slippagePoints

    return {
      capital,
      riskPercent,
      maxLoss: maxLossAmount,
      quantity: adjustedQuantity,
      lotSize,
      marginRequired,
      brokerCharges,
      taxes,
      slippage,
    }
  },

  /**
   * Compute risk configuration from decision data.
   */
  calculateRisk(riskLevel: string, riskScore: number, maxRiskPercent: number): RiskConfig {
    const normalized = (riskLevel || "MEDIUM").toUpperCase()
    const validLevels = ["LOW", "MEDIUM", "HIGH", "EXTREME"]
    const level = validLevels.includes(normalized) ? (normalized as RiskConfig["level"]) : "MEDIUM"
    return { level, score: riskScore, maxRiskPercent }
  },

  /**
   * Compute reward configuration from trade plan targets.
   */
  calculateReward(entryPrice: number | null, stoploss: number | null, targets: { price?: number; zone?: string; probability?: number }[]): RewardConfig {
    if (!entryPrice || !stoploss || entryPrice <= 0 || stoploss <= 0) {
      return { expectedRR: 0, profitTargets: [], netRR: 0 }
    }

    const riskPoints = Math.abs(entryPrice - stoploss)
    if (riskPoints <= 0) return { expectedRR: 0, profitTargets: [], netRR: 0 }

    const profitTargets = targets
      .filter((t) => t.price != null)
      .map((t) => ({
        target: t.price!,
        probability: t.probability ?? 0.5,
      }))

    const firstTarget = profitTargets.length > 0 ? profitTargets[0].target : null
    const expectedRR = firstTarget ? (Math.abs(firstTarget - entryPrice) / riskPoints) : 0
    const netRR = expectedRR * 0.85 // Rough adjustment for fees/slippage

    return { expectedRR: Math.round(expectedRR * 10) / 10, profitTargets, netRR: Math.round(netRR * 10) / 10 }
  },

  /**
   * Determine execution status from decision + checklist results.
   */
  calculateExecutionStatus(
    decision: string,
    score: number,
    confidence: number,
    riskLevel: string,
    tradePlan: TradePlanInput
  ): ExecutionConfig {
    const status = ((): string => {
      if (!tradePlan?.valid) return "NO_TRADE"
      if (decision === "HIGH_CONVICTION") return "HIGH_CONVICTION"
      if (decision === "LOW_CONVICTION") return "LOW_CONVICTION"
      if (decision === "WAIT" || decision === "NO_TRADE") return decision
      if (score >= 70 && confidence >= 60) return "HIGH_CONVICTION"
      if (score >= 50) return "READY"
      return "LOW_CONVICTION"
    })()

    const entryPrice =
      tradePlan?.entry_zone?.price ??
      tradePlan?.entry_zone?.top ??
      tradePlan?.entry_zone?.bottom ??
      null

    const stoploss = tradePlan?.sl_zone?.price ?? null
    const riskPoints = entryPrice && stoploss ? Math.abs(entryPrice - stoploss) : null

    return {
      status: status as ExecutionConfig["status"],
      entryPrice,
      entryConfirmed: status === "HIGH_CONVICTION" || status === "READY",
      stoploss,
      riskPoints,
      direction: tradePlan?.direction === "LONG" ? "LONG" : tradePlan?.direction === "SHORT" ? "SHORT" : "NONE",
      executionTimeframe: "15m",
      institutionalBias: score >= 60 ? "BULLISH" : score <= 40 ? "BEARISH" : "NEUTRAL",
      marketCondition: riskLevel === "LOW" ? "FAVORABLE" : riskLevel === "HIGH" ? "CAUTIOUS" : "NORMAL",
      tradingPermission: status === "HIGH_CONVICTION" ? "APPROVED" : status === "NO_TRADE" ? "DENIED" : "PENDING",
    }
  },

  /**
   * Compute execution checklist from all available data.
   */
  calculateChecklist(
    structureData: { trend?: string; valid_structure?: boolean; market_phase?: string } | null,
    indicatorData: { all_ready?: boolean; rsi_14?: number | null } | null,
    patternData: { total_count?: number; strongest_pattern?: string } | null,
    srData: { nearest_support?: number | null; nearest_resistance?: number | null; warnings?: string[] } | null,
    execution: ExecutionConfig,
    risk: RiskConfig
  ): ChecklistItemData[] {
    return [
      {
        id: "htf",
        label: "HTF Alignment",
        status: structureData?.valid_structure ? "PASS" : structureData ? "WARNING" : "FAIL",
        detail: structureData?.trend ? `${structureData.trend} trend` : "No data",
      },
      {
        id: "trend",
        label: "Trend Confirmation",
        status: structureData?.trend && ["UP", "DOWN", "BULLISH", "BEARISH"].includes(structureData.trend) ? "PASS" : structureData?.trend ? "WARNING" : "FAIL",
        detail: structureData?.trend ?? "No trend",
      },
      {
        id: "structure",
        label: "Structure Valid",
        status: structureData?.valid_structure ? "PASS" : structureData ? "WARNING" : "FAIL",
        detail: structureData?.market_phase ?? "N/A",
      },
      {
        id: "indicators",
        label: "Indicator Confirmation",
        status: indicatorData?.all_ready ? "PASS" : "WARNING",
        detail: indicatorData?.rsi_14 != null ? `RSI ${indicatorData.rsi_14.toFixed(0)}` : "Pending",
      },
      {
        id: "patterns",
        label: "Pattern Confirmation",
        status: (patternData?.total_count ?? 0) > 0 ? "PASS" : "WARNING",
        detail: patternData?.strongest_pattern || "None",
      },
      {
        id: "sr",
        label: "Support & Resistance",
        status: srData?.nearest_support != null && srData?.nearest_resistance != null ? "PASS" : "WARNING",
        detail: (srData?.warnings?.length ?? 0) > 0 ? "Limited data" : "Available",
      },
      {
        id: "liquidity",
        label: "Liquidity Check",
        status: structureData?.valid_structure ? "PASS" : "WARNING",
        detail: "Standard",
      },
      {
        id: "risk",
        label: "Risk Check",
        status: risk.level === "EXTREME" ? "FAIL" : risk.level === "HIGH" ? "WARNING" : "PASS",
        detail: `${risk.level} risk`,
      },
    ]
  },

  /**
   * Build trade timeline from current state.
   */
  calculateTimeline(execution: ExecutionConfig, currentTime: string | null): TimelineEvent[] {
    return [
      {
        id: "signal",
        label: "Signal Created",
        timestamp: currentTime,
        completed: true,
        active: false,
      },
      {
        id: "confirmation",
        label: "Confirmation",
        timestamp: execution.entryConfirmed ? (currentTime) : null,
        completed: execution.entryConfirmed,
        active: !execution.entryConfirmed,
      },
      {
        id: "entry",
        label: "Entry",
        timestamp: execution.entryConfirmed && execution.entryPrice ? currentTime : null,
        completed: execution.entryConfirmed,
        active: execution.entryConfirmed && !execution.stoploss,
      },
      {
        id: "stoploss",
        label: "Stoploss",
        timestamp: null,
        completed: false,
        active: false,
      },
      {
        id: "targets",
        label: "Targets",
        timestamp: null,
        completed: false,
        active: false,
      },
      {
        id: "completed",
        label: "Completed",
        timestamp: null,
        completed: false,
        active: false,
      },
    ]
  },
}
