"use client"

import type { MTFAgreementResponse } from "@/services/aiDecisionService"

const STATUS_COLORS: Record<string, string> = {
  "STRONG": "text-emerald-500",
  "MODERATE": "text-amber-500",
  "WEAK": "text-orange-500",
  "CONFLICT": "text-red-500",
  "NO_DATA": "text-muted-foreground",
}

export function AgreementBreakdownPanel({ data }: { data: MTFAgreementResponse | null }) {
  if (!data) {
    return <div className="p-8 text-center text-[10px] text-muted-foreground">No MTF agreement data</div>
  }

  return (
    <div className="space-y-4">
      <div className="grid grid-cols-3 gap-3">
        <Metric label="Agreement" value={`${data.agreement_percent}%`} color={data.agreement_percent >= 80 ? "text-emerald-500" : data.agreement_percent >= 60 ? "text-amber-500" : "text-red-500"} />
        <Metric label="Weighted" value={`${data.weighted_agreement}%`} />
        <Metric label="Status" value={data.status} color={STATUS_COLORS[data.status] || ""} />
      </div>

      <div className="space-y-1.5">
        {data.breakdown.map((tf) => (
          <div key={tf.timeframe} className="flex items-center gap-2 p-2 rounded-lg border bg-card text-[10px]">
            <span className="w-10 font-medium">{tf.timeframe}</span>
            <span className={`flex-1 font-mono ${tf.agrees ? "text-emerald-500" : "text-red-500"}`}>
              {tf.bias}
            </span>
            <div className="w-24 h-1.5 rounded-full bg-muted/30 overflow-hidden">
              <div className={`h-full rounded-full ${tf.agrees ? "bg-emerald-500" : "bg-red-500"}`}
                style={{ width: `${Math.round(tf.weight * 100)}%` }} />
            </div>
            <span className="w-16 text-right text-muted-foreground">{Math.round(tf.weight * 100)}% wt</span>
          </div>
        ))}
      </div>

      {data.conflicts_found.length > 0 && (
        <div className="rounded-lg border border-red-500/20 bg-red-500/5 p-3">
          <div className="text-[9px] text-red-500 uppercase font-medium mb-1">Conflicts</div>
          {data.conflicts_found.map((c, i) => (
            <div key={i} className="text-[10px] text-red-600">• {c.timeframe}: {c.bias} conflicts</div>
          ))}
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
