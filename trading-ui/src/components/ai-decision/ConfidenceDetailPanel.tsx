"use client"

import type { DetailedConfidenceResponse } from "@/services/aiDecisionService"

export function ConfidenceDetailPanel({ data }: { data: DetailedConfidenceResponse | null }) {
  if (!data) {
    return <div className="p-8 text-center text-[10px] text-muted-foreground">No confidence data</div>
  }

  return (
    <div className="space-y-4">
      <div className="grid grid-cols-4 gap-3">
        <Metric label="Overall" value={`${data.overall_confidence}%`} color={data.overall_confidence >= 80 ? "text-emerald-500" : data.overall_confidence >= 60 ? "text-amber-500" : "text-red-500"} />
        <Metric label="Grade" value={data.grade.replace(/_/g, " ")} color={data.overall_confidence >= 60 ? "text-emerald-500" : "text-red-500"} />
        <Metric label="Factors" value={`${data.factor_breakdown.length}`} />
        <Metric label="Above 80" value={`${data.factor_breakdown.filter(f => f.score >= 80).length}`} color="text-emerald-500" />
      </div>

      <div className="space-y-2">
        {data.factor_breakdown.map((f) => (
          <div key={f.name} className="rounded-lg border bg-card p-3">
            <div className="flex items-center justify-between mb-1">
              <span className="text-[10px] font-medium">{f.name}</span>
              <span className={`text-[11px] font-mono font-bold ${f.score >= 80 ? "text-emerald-500" : f.score >= 60 ? "text-amber-500" : "text-red-500"}`}>
                {f.score}/100
              </span>
            </div>
            <div className="w-full h-1.5 rounded-full bg-muted/30 overflow-hidden">
              <div className="h-full rounded-full transition-all duration-500"
                style={{ width: `${f.score}%`, backgroundColor: f.score >= 80 ? "#22c55e" : f.score >= 60 ? "#f59e0b" : "#ef4444" }} />
            </div>
            <div className="text-[9px] text-muted-foreground mt-1">{f.detail}</div>
          </div>
        ))}
      </div>

      {data.reasoning.length > 0 && (
        <div className="rounded-lg border bg-card p-3">
          <div className="text-[9px] text-muted-foreground uppercase mb-1">Reasoning</div>
          <ul className="text-[10px] space-y-0.5">
            {data.reasoning.map((r, i) => <li key={i} className="text-muted-foreground">• {r}</li>)}
          </ul>
        </div>
      )}
    </div>
  )
}

function Metric({ label, value, color }: { label: string; value: string; color?: string }) {
  return (
    <div className="rounded-lg border bg-card p-3 text-center">
      <div className="text-[9px] text-muted-foreground uppercase">{label}</div>
      <div className={`text-lg font-bold font-mono mt-0.5 ${color || ""}`}>{value}</div>
    </div>
  )
}
