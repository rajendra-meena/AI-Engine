"use client"

import type { SignalValidationResponse } from "@/services/aiDecisionService"

const STATUS_BG: Record<string, string> = {
  "PASS": "bg-emerald-500/10 text-emerald-500 border-emerald-500/20",
  "WARNING": "bg-amber-500/10 text-amber-500 border-amber-500/20",
  "BLOCK": "bg-red-500/10 text-red-500 border-red-500/20",
}

export function SignalValidationPanel({ data }: { data: SignalValidationResponse | null }) {
  if (!data) {
    return <div className="p-8 text-center text-[10px] text-muted-foreground">No signal validation data</div>
  }

  return (
    <div className="space-y-4">
      <div className="grid grid-cols-4 gap-3">
        <Metric label="Status" value={data.overall_status} color={data.overall_status === "PASS" ? "text-emerald-500" : data.overall_status === "WARNING" ? "text-amber-500" : "text-red-500"} />
        <Metric label="Pass" value={String(data.pass_count)} color="text-emerald-500" />
        <Metric label="Warning" value={String(data.warning_count)} color="text-amber-500" />
        <Metric label="Block" value={String(data.block_count)} color="text-red-500" />
      </div>

      <div className="space-y-1">
        {data.validations.map((v) => (
          <div key={v.signal} className="flex items-center gap-2 p-2 rounded-lg border bg-card text-[10px]">
            <span className={`px-1.5 py-0.5 rounded text-[8px] font-medium border ${STATUS_BG[v.status] || "bg-muted/30 text-muted-foreground"}`}>
              {v.status}
            </span>
            <span className="w-28 font-medium capitalize">{v.signal.replace(/_/g, " ")}</span>
            <span className="flex-1 text-muted-foreground truncate">{v.reason}</span>
          </div>
        ))}
      </div>
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
