"use client"

import type { AIExplanationResponse } from "@/services/aiDecisionService"

export function ExplanationPanel({ data }: { data: AIExplanationResponse | null }) {
  if (!data) {
    return <div className="p-8 text-center text-[10px] text-muted-foreground">No explanation data</div>
  }

  const exp = data.decision_explanation

  return (
    <div className="space-y-4">
      {/* Primary Reason */}
      <div className="rounded-lg border bg-card p-4">
        <div className="text-[9px] text-muted-foreground uppercase mb-1">Primary Reason</div>
        <div className="text-sm font-medium">{exp.primary_reason}</div>
      </div>

      {/* WHY BUY */}
      {data.why_buy && (
        <div className="rounded-lg border border-emerald-500/20 bg-emerald-500/5 p-3">
          <div className="text-[9px] text-emerald-500 uppercase font-medium mb-1">WHY BUY</div>
          <div className="text-[10px] text-emerald-600">{data.why_buy}</div>
        </div>
      )}

      {/* WHY SELL */}
      {data.why_sell && (
        <div className="rounded-lg border border-red-500/20 bg-red-500/5 p-3">
          <div className="text-[9px] text-red-500 uppercase font-medium mb-1">WHY SELL</div>
          <div className="text-[10px] text-red-600">{data.why_sell}</div>
        </div>
      )}

      {/* WHY NO TRADE */}
      {data.why_no_trade && (
        <div className="rounded-lg border border-amber-500/20 bg-amber-500/5 p-3">
          <div className="text-[9px] text-amber-500 uppercase font-medium mb-1">WHY NO TRADE</div>
          <div className="text-[10px] text-amber-600">{data.why_no_trade}</div>
        </div>
      )}

      {/* Supporting Factors */}
      {exp.supporting_factors.length > 0 && (
        <div className="rounded-lg border bg-card p-3">
          <div className="text-[9px] text-muted-foreground uppercase mb-2">Supporting Factors</div>
          <div className="space-y-1">
            {exp.supporting_factors.map((f, i) => (
              <div key={i} className="flex items-center gap-2 text-[10px]">
                <span className="w-1.5 h-1.5 rounded-full bg-emerald-500" />
                <span className="font-medium">{f.factor}</span>
                <span className="text-muted-foreground">{f.detail}</span>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Blocking Factors */}
      {exp.blocking_factors.length > 0 && (
        <div className="rounded-lg border bg-card p-3">
          <div className="text-[9px] text-muted-foreground uppercase mb-2">Blocking Factors</div>
          <div className="space-y-1">
            {exp.blocking_factors.map((f, i) => (
              <div key={i} className="flex items-center gap-2 text-[10px]">
                <span className="w-1.5 h-1.5 rounded-full bg-red-500" />
                <span className="font-medium">{f.factor}</span>
                <span className="text-muted-foreground">{f.detail}</span>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}
