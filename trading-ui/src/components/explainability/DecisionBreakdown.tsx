"use client"

import { cn } from "@/lib/utils"
import { TrendingUp, TrendingDown, Minus, Activity, Lock } from "lucide-react"

interface DecisionBreakdownProps {
  decision: string
  score: number
  confidence: number
  riskLevel: string
  institutionalBias: string
  marketCondition: string
  tradingPermission: string
  direction: string
  timestamp: string
}

export function DecisionBreakdown({
  decision, score, confidence, riskLevel, institutionalBias,
  marketCondition, tradingPermission, direction, timestamp,
}: DecisionBreakdownProps) {
  const isBullish = institutionalBias === "BULLISH" || direction === "LONG"
  const isBearish = institutionalBias === "BEARISH" || direction === "SHORT"

  return (
    <div className="rounded-lg border bg-card p-3 space-y-2">
      <div className="text-[9px] font-medium text-muted-foreground uppercase tracking-wider">Decision Summary</div>

      <div className="grid grid-cols-2 sm:grid-cols-4 gap-2">
        <div className="rounded-md bg-muted/20 p-2 text-center">
          <div className="text-[8px] text-muted-foreground uppercase">Decision</div>
          <div className={cn("text-sm font-bold mt-0.5", decision === "HIGH_CONVICTION" ? "text-emerald-500" : decision === "NO_TRADE" ? "text-red-500" : "text-amber-500")}>
            {decision.replace(/_/g, " ")}
          </div>
        </div>

        <div className="rounded-md bg-muted/20 p-2 text-center">
          <div className="text-[8px] text-muted-foreground uppercase">Bias</div>
          <div className={cn("flex items-center justify-center gap-1 text-sm font-bold mt-0.5", isBullish ? "text-emerald-500" : isBearish ? "text-red-500" : "")}>
            {isBullish ? <TrendingUp className="w-4 h-4" /> : isBearish ? <TrendingDown className="w-4 h-4" /> : <Minus className="w-4 h-4" />}
            {institutionalBias}
          </div>
        </div>

        <div className="rounded-md bg-muted/20 p-2 text-center">
          <div className="text-[8px] text-muted-foreground uppercase">Condition</div>
          <div className="flex items-center justify-center gap-1 text-xs font-medium mt-0.5">
            <Activity className="w-3 h-3" /> {marketCondition}
          </div>
        </div>

        <div className="rounded-md bg-muted/20 p-2 text-center">
          <div className="text-[8px] text-muted-foreground uppercase">Permission</div>
          <div className={cn("flex items-center justify-center gap-1 text-xs font-medium mt-0.5", tradingPermission === "APPROVED" ? "text-emerald-500" : tradingPermission === "DENIED" ? "text-red-500" : "")}>
            <Lock className="w-3 h-3" /> {tradingPermission}
          </div>
        </div>
      </div>

      <div className="grid grid-cols-3 gap-2">
        <div className="text-center">
          <div className="text-[8px] text-muted-foreground">Score</div>
          <div className={cn("text-lg font-bold font-mono", score >= 80 ? "text-emerald-500" : score >= 60 ? "text-blue-500" : score >= 40 ? "text-amber-500" : "text-red-500")}>{score}</div>
        </div>
        <div className="text-center">
          <div className="text-[8px] text-muted-foreground">Confidence</div>
          <div className={cn("text-lg font-bold font-mono", confidence >= 80 ? "text-emerald-500" : confidence >= 60 ? "text-blue-500" : "text-amber-500")}>{confidence}%</div>
        </div>
        <div className="text-center">
          <div className="text-[8px] text-muted-foreground">Risk</div>
          <div className={cn("text-lg font-bold font-mono", riskLevel === "LOW" ? "text-emerald-500" : riskLevel === "HIGH" || riskLevel === "EXTREME" ? "text-red-500" : "text-amber-500")}>{riskLevel}</div>
        </div>
      </div>

      {timestamp && <div className="text-[8px] text-muted-foreground text-center">{new Date(timestamp).toLocaleString()}</div>}
    </div>
  )
}
