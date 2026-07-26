"use client"

import type { TradeQualityResponse } from "@/services/aiDecisionService"

const GRADE_COLORS: Record<string, string> = {
  "A+": "text-emerald-400",
  "A": "text-emerald-500",
  "B": "text-blue-500",
  "C": "text-amber-500",
  "D": "text-orange-500",
  "REJECT": "text-red-500",
}

const GRADE_BG: Record<string, string> = {
  "A+": "bg-emerald-500/10 border-emerald-500/20",
  "A": "bg-emerald-500/10 border-emerald-500/20",
  "B": "bg-blue-500/10 border-blue-500/20",
  "C": "bg-amber-500/10 border-amber-500/20",
  "D": "bg-orange-500/10 border-orange-500/20",
  "REJECT": "bg-red-500/10 border-red-500/20",
}

export function QualityGradePanel({ data }: { data: TradeQualityResponse | null }) {
  if (!data) {
    return <div className="p-8 text-center text-[10px] text-muted-foreground">No quality data</div>
  }

  const isRejected = data.grade === "REJECT"

  return (
    <div className="space-y-4">
      {/* Grade Display */}
      <div className="flex items-center gap-4">
        <div className={`rounded-xl border-2 p-4 text-center min-w-[120px] ${GRADE_BG[data.grade] || "bg-card"}`}>
          <div className={`text-4xl font-black ${GRADE_COLORS[data.grade] || "text-muted-foreground"}`}>{data.grade}</div>
          <div className="text-[10px] text-muted-foreground mt-1">Grade</div>
        </div>
        <div className="space-y-1">
          <div className={`text-2xl font-bold font-mono ${isRejected ? "text-red-500" : "text-emerald-500"}`}>
            {data.total_score}/100
          </div>
          <div className="text-[10px] text-muted-foreground">{isRejected ? "Not eligible" : "Trade eligible"}</div>
        </div>
      </div>

      {/* Factor Bars */}
      <div className="space-y-2">
        {data.factor_scores.map((f) => (
          <div key={f.name} className="rounded-lg border bg-card p-3">
            <div className="flex items-center justify-between mb-1">
              <span className="text-[10px] font-medium">{f.name}</span>
              <span className="text-[11px] font-mono font-bold">{f.score}</span>
            </div>
            <div className="w-full h-2 rounded-full bg-muted/30 overflow-hidden">
              <div className="h-full rounded-full transition-all" style={{ width: `${f.score}%`, backgroundColor: f.score >= 70 ? "#22c55e" : f.score >= 50 ? "#f59e0b" : "#ef4444" }} />
            </div>
            <div className="text-[9px] text-muted-foreground mt-0.5">Weight: {f.weight}% — {f.detail}</div>
          </div>
        ))}
      </div>

      {data.warnings.length > 0 && (
        <div className="rounded-lg border border-amber-500/20 bg-amber-500/5 p-3">
          <div className="text-[9px] text-amber-500 uppercase font-medium mb-1">Warnings</div>
          {data.warnings.map((w, i) => <div key={i} className="text-[10px] text-amber-600">• {w}</div>)}
        </div>
      )}
    </div>
  )
}
