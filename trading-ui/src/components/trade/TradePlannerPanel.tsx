"use client"

import { useTradePlanner } from "@/hooks/useTradePlanner"
import { RiskGauge } from "./RiskGauge"
import { RewardGauge } from "./RewardGauge"
import { ChecklistItem } from "./ChecklistItem"
import { TargetCard } from "./TargetCard"
import { PositionCard } from "./PositionCard"
import { ExecutionStatus } from "./ExecutionStatus"
import { TradeTimeline } from "./TradeTimeline"
import { Skeleton } from "@/components/ui/skeleton"
import { TrendingUp, TrendingDown, Minus, ShieldAlert, Lightbulb } from "lucide-react"
import { cn } from "@/lib/utils"

/**
 * TradePlannerPanel
 *
 * Institutional Trade Planner & Execution Workstation.
 *
 * Architecture:
 *   Entry / Stoploss / Targets / RR
 *   Position Sizing (capital, risk %, quantity, margin, fees, slippage)
 *   Execution Checklist (8 checks — PASS/FAIL/WARNING)
 *   Risk Meter (circular gauge)
 *   Reward Meter (RR gauge)
 *   Trade Timeline (6 stages)
 *   Trade Status (WAIT/READY/HIGH_CONVICTION/...)
 *   Reasoning & Warnings
 *
 * No mock data — all data from backend AI Decision APIs via useTradePlanner hook.
 */
export function TradePlannerPanel() {
  const planner = useTradePlanner()

  const { execution, risk, reward, position, checklist, timeline, reasoning, warnings } = planner
  const { decision } = planner

  if (!decision) {
    return (
      <div className="space-y-2 p-1">
        <Skeleton className="h-4 w-full" />
        <Skeleton className="h-3 w-5/6" />
        <Skeleton className="h-3 w-4/6" />
        <Skeleton className="h-20 w-full" />
      </div>
    )
  }

  const plan = decision?.trade_plan ?? ({} as Record<string, unknown>)
  const isBullish = plan.direction === "LONG"
  const directionIcon = isBullish ? <TrendingUp className="w-3.5 h-3.5" /> : plan.direction === "SHORT" ? <TrendingDown className="w-3.5 h-3.5" /> : <Minus className="w-3.5 h-3.5" />
  const directionColor = isBullish ? "text-emerald-500" : plan.direction === "SHORT" ? "text-red-500" : "text-muted-foreground"

  return (
    <div className="space-y-2">
      {/* ── Execution Status ── */}
      <ExecutionStatus status={execution.status} />

      {/* ── Direction & Timeframe ── */}
      <div className="grid grid-cols-2 gap-1.5">
        <div className="rounded-md bg-muted/30 p-2">
          <div className="text-[8px] text-muted-foreground uppercase tracking-wider mb-0.5">Direction</div>
          <div className={cn("flex items-center gap-1 text-xs font-bold", directionColor)}>
            {directionIcon}
            {plan.direction || "NONE"}
          </div>
        </div>
        <div className="rounded-md bg-muted/30 p-2">
          <div className="text-[8px] text-muted-foreground uppercase tracking-wider mb-0.5">Timeframe</div>
          <div className="text-xs font-bold font-mono">{execution.executionTimeframe || "--"}</div>
        </div>
      </div>

      {/* ── Institutional Bias / Market Condition / Trading Permission ── */}
      <div className="rounded-md border bg-muted/20 p-2 space-y-1">
        <div className="flex items-center justify-between">
          <span className="text-[9px] text-muted-foreground">Institutional Bias</span>
          <span className={cn(
            "text-[10px] font-bold",
            execution.institutionalBias === "BULLISH" ? "text-emerald-500" :
            execution.institutionalBias === "BEARISH" ? "text-red-500" : "text-muted-foreground"
          )}>
            {execution.institutionalBias}
          </span>
        </div>
        <div className="flex items-center justify-between">
          <span className="text-[9px] text-muted-foreground">Market Condition</span>
          <span className={cn(
            "text-[10px] font-bold",
            execution.marketCondition === "FAVORABLE" ? "text-emerald-500" :
            execution.marketCondition === "CAUTIOUS" ? "text-amber-500" : "text-muted-foreground"
          )}>
            {execution.marketCondition}
          </span>
        </div>
        <div className="flex items-center justify-between">
          <span className="text-[9px] text-muted-foreground">Trading Permission</span>
          <span className={cn(
            "text-[10px] font-bold",
            execution.tradingPermission === "APPROVED" ? "text-emerald-500" :
            execution.tradingPermission === "DENIED" ? "text-red-500" :
            execution.tradingPermission === "PENDING" ? "text-amber-500" : "text-muted-foreground"
          )}>
            {execution.tradingPermission}
          </span>
        </div>
      </div>

      {/* ── Entry / Stoploss / Targets ── */}
      <div className="rounded-md border bg-card p-2 space-y-1.5">
        <div className="text-[9px] font-medium text-muted-foreground uppercase tracking-wider">Trade Setup</div>

        {/* Entry */}
        <div className="flex items-center justify-between">
          <span className="text-[9px] text-muted-foreground flex items-center gap-1">
            <TrendingUp className="w-3 h-3 text-blue-500" /> Entry Zone
          </span>
          <span className="text-[10px] font-mono font-medium">
            {plan.entry_zone?.zone || (execution.entryPrice ? execution.entryPrice.toFixed(2) : "Pending")}
          </span>
        </div>

        {/* Confirmation */}
        <div className="flex items-center justify-between">
          <span className="text-[9px] text-muted-foreground">Confirmation</span>
          <span className={cn("text-[10px] font-medium", execution.entryConfirmed ? "text-emerald-500" : "text-amber-500")}>
            {execution.entryConfirmed ? "Confirmed" : "Pending"}
          </span>
        </div>

        {/* Stoploss */}
        <div className="flex items-center justify-between">
          <span className="text-[9px] text-muted-foreground flex items-center gap-1">
            <ShieldAlert className="w-3 h-3 text-red-500" /> Stoploss
          </span>
          <span className="text-[10px] font-mono font-medium">
            {execution.stoploss ? execution.stoploss.toFixed(2) : plan.sl_zone?.zone || "N/A"}
          </span>
        </div>

        {/* Risk Points */}
        <div className="flex items-center justify-between">
          <span className="text-[9px] text-muted-foreground">Risk Points</span>
          <span className="text-[10px] font-mono text-red-500">
            {execution.riskPoints != null ? execution.riskPoints.toFixed(2) : "--"}
          </span>
        </div>

        {/* Targets (1-5) */}
        {(plan.target_zones || []).length > 0 && (
          <div className="pt-1">
            <div className="text-[9px] text-muted-foreground mb-1">Targets</div>
            <div className={cn(
              "grid gap-1",
              (plan.target_zones || []).length <= 3 ? "grid-cols-3" : "grid-cols-5"
            )}>
              {(plan.target_zones || []).slice(0, 5).map((t, i: number) => {
                const target = t as { price?: number; probability?: number }
                return (
                  <TargetCard
                    key={i}
                    number={i + 1}
                    price={typeof target.price === "number" ? target.price : null}
                    probability={typeof target.probability === "number" ? target.probability : undefined}
                  />
                )
              })}
            </div>
          </div>
        )}

        {/* Expected RR */}
        <div className="flex items-center justify-between pt-0.5 border-t">
          <span className="text-[9px] text-muted-foreground">Expected RR</span>
          <span className="text-[11px] font-bold font-mono" style={{ color: reward.expectedRR >= 1 ? "#22c55e" : reward.expectedRR >= 0.5 ? "#f59e0b" : "#ef4444" }}>
            {reward.expectedRR.toFixed(1)}:1
          </span>
        </div>
      </div>

      {/* ── Risk & Reward Gauges ── */}
      <div className="grid grid-cols-2 gap-2">
        <div className="rounded-md border bg-card p-2">
          <div className="text-[9px] font-medium text-muted-foreground uppercase tracking-wider text-center mb-1">Risk</div>
          <RiskGauge level={risk.level} score={risk.score} size="sm" />
        </div>
        <div className="rounded-md border bg-card p-2">
          <div className="text-[9px] font-medium text-muted-foreground uppercase tracking-wider text-center mb-1">Reward</div>
          <RewardGauge expectedRR={reward.expectedRR} netRR={reward.netRR} size="sm" />
        </div>
      </div>

      {/* ── Position Sizing ── */}
      <PositionCard
        position={position}
        capital={planner.capital}
        riskPercent={planner.riskPercent}
        lotSize={planner.lotSize}
        brokerChargesPercent={planner.brokerChargesPercent}
        slippagePoints={planner.slippagePoints}
        onCapitalChange={planner.updateCapital}
        onRiskPercentChange={planner.updateRiskPercent}
        onLotSizeChange={planner.updateLotSize}
        onBrokerChargesChange={planner.updateBrokerCharges}
        onSlippageChange={planner.updateSlippage}
      />

      {/* ── Execution Checklist ── */}
      <div className="rounded-md border bg-card p-2">
        <div className="text-[9px] font-medium text-muted-foreground uppercase tracking-wider mb-1">Execution Checklist</div>
        {checklist.map((item) => (
          <ChecklistItem key={item.id} label={item.label} status={item.status} detail={item.detail} />
        ))}
      </div>

      {/* ── Trade Timeline ── */}
      {timeline.length > 0 && (
        <div className="rounded-md border bg-card p-2">
          <div className="text-[9px] font-medium text-muted-foreground uppercase tracking-wider mb-1">Timeline</div>
          <TradeTimeline events={timeline} />
        </div>
      )}

      {/* ── Reasoning ── */}
      {reasoning.length > 0 && (
        <div className="rounded-md border bg-card p-2">
          <div className="text-[9px] font-medium text-muted-foreground uppercase tracking-wider mb-1 flex items-center gap-1">
            <Lightbulb className="w-3 h-3" /> Reasoning
          </div>
          <div className="space-y-0.5">
            {reasoning.slice(0, 5).map((r: string, i: number) => (
              <div key={i} className="text-[9px] text-muted-foreground flex items-start gap-1">
                <span className="text-primary mt-0.5">•</span> {r}
              </div>
            ))}
          </div>
        </div>
      )}

      {/* ── Warnings ── */}
      {warnings.length > 0 && (
        <div className="rounded-md border border-amber-500/20 bg-amber-500/5 p-2">
          <div className="text-[9px] font-medium text-amber-500 uppercase tracking-wider mb-1">Warnings</div>
          {warnings.slice(0, 3).map((w: string, i: number) => (
            <div key={i} className="text-[9px] text-amber-500/80 flex items-start gap-1">
              <span>!</span> {w}
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
