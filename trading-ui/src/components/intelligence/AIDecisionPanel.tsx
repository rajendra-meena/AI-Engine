"use client"

import { useDecision } from "@/hooks/useDecision"
import { DecisionBadge, RiskBadge, ProgressBar } from "./RiskBadge"
import { Skeleton } from "@/components/ui/skeleton"
import { AlertCircle, RefreshCw, Target, ShieldAlert } from "lucide-react"

export function AIDecisionPanel() {
  const { data, isLoading, error, refetch } = useDecision()

  if (isLoading) return <div className="space-y-2 p-3"><Skeleton className="h-4 w-full" /><Skeleton className="h-3 w-5/6" /><Skeleton className="h-3 w-4/6" /></div>
  if (error) return <div className="p-3 text-[10px] text-red-500 flex items-center gap-2"><AlertCircle className="w-3 h-3" /> Failed <button onClick={() => refetch()}><RefreshCw className="w-3 h-3" /></button></div>
  if (!data) return <div className="p-3 text-[10px] text-muted-foreground">No AI decision data</div>

  const plan = data.trade_plan

  return (
    <div className="space-y-2">
      {/* Decision Header */}
      <div className="flex items-center gap-2">
        <DecisionBadge value={data.decision} />
        <RiskBadge level={data.risk_level} />
      </div>

      {/* Score & Confidence */}
      <div className="grid grid-cols-2 gap-2">
        <div className="rounded-md bg-muted/30 p-2">
          <div className="text-[8px] text-muted-foreground uppercase tracking-wider mb-1">Score</div>
          <div className="text-lg font-bold font-mono">{data.score}</div>
          <ProgressBar value={data.score} className="mt-1" />
          <div className="text-[8px] text-muted-foreground mt-0.5">{data.score_grade}</div>
        </div>
        <div className="rounded-md bg-muted/30 p-2">
          <div className="text-[8px] text-muted-foreground uppercase tracking-wider mb-1">Confidence</div>
          <div className="text-lg font-bold font-mono">{data.confidence}</div>
          <ProgressBar value={data.confidence} className="mt-1" />
          <div className="text-[8px] text-muted-foreground mt-0.5">{data.confidence_grade}</div>
        </div>
      </div>

      {/* Trade Plan */}
      {plan?.valid && (
        <div className="rounded-md border border-emerald-500/20 bg-emerald-500/5 p-2 space-y-1">
          <div className="text-[9px] font-medium text-emerald-500 uppercase tracking-wider">Trade Plan</div>
          <div className="text-[10px] font-bold">{plan.direction}</div>

          {plan.entry_zone && (
            <div className="flex items-center gap-1 text-[10px]">
              <Target className="w-3 h-3 text-emerald-500" />
              <span className="text-muted-foreground">Entry:</span>
              <span className="font-mono font-medium">{plan.entry_zone.zone || "Market"}</span>
            </div>
          )}

          {plan.sl_zone && (
            <div className="flex items-center gap-1 text-[10px]">
              <ShieldAlert className="w-3 h-3 text-red-500" />
              <span className="text-muted-foreground">SL:</span>
              <span className="font-mono font-medium">{plan.sl_zone.price?.toFixed(2) || plan.sl_zone.zone}</span>
            </div>
          )}

          {plan.target_zones?.length > 0 && (
            <div className="text-[10px] text-muted-foreground">
              Targets: {plan.target_zones.map((t: { price?: number; zone?: string }, i: number) => (
                <span key={i} className="font-mono font-medium text-emerald-500 ml-1">{t.price?.toFixed(2) || t.zone}</span>
              ))}
            </div>
          )}

          <div className="text-[9px] text-muted-foreground">
            Max Risk: {plan.max_risk_percent}% · Context: {plan.risk_reward_context}
          </div>
        </div>
      )}

      {!plan?.valid && (
        <div className="rounded-md bg-muted/30 p-2 text-center text-[9px] text-muted-foreground/50">
          No valid trade plan
        </div>
      )}

      {/* Reasoning */}
      {data.reasoning?.length > 0 && (
        <div>
          <div className="text-[9px] font-medium text-muted-foreground uppercase tracking-wider mb-1">Reasoning</div>
          <div className="space-y-0.5">
            {data.reasoning.slice(0, 4).map((r: string, i: number) => (
              <div key={i} className="text-[9px] text-muted-foreground flex items-start gap-1">
                <span className="text-primary mt-0.5">&#8226;</span> {r}
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Warnings */}
      {data.warnings?.length > 0 && (
        <div>
          <div className="text-[9px] font-medium text-amber-500 uppercase tracking-wider mb-1">Warnings</div>
          {data.warnings.slice(0, 3).map((w: string, i: number) => (
            <div key={i} className="text-[9px] text-amber-500/80 flex items-start gap-1">
              <span className="mt-0.5">!</span> {w}
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
