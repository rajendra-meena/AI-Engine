"use client"

import type { FalseSignalResponse } from "@/services/aiDecisionService"

export function FalseSignalPanel({ data }: { data: FalseSignalResponse | null }) {
  if (!data) {
    return <div className="p-8 text-center text-[10px] text-muted-foreground">No false signal data</div>
  }

  return (
    <div className="space-y-4">
      <div className={`rounded-lg border p-4 text-center ${data.is_false_signal ? "bg-red-500/10 border-red-500/20" : "bg-emerald-500/10 border-emerald-500/20"}`}>
        <div className={`text-lg font-bold ${data.is_false_signal ? "text-red-500" : "text-emerald-500"}`}>
          {data.is_false_signal ? "⚠ FALSE SIGNAL DETECTED" : "✓ Clean Signal"}
        </div>
        <div className="text-[10px] text-muted-foreground mt-1">
          {data.is_false_signal
            ? `${data.detections.filter(d => d.detected).length} pattern(s) detected`
            : "No false signal patterns found"}
        </div>
      </div>

      <div className="space-y-1">
        {data.detections.map((d) => (
          <div key={d.type} className={`flex items-center gap-2 p-2 rounded-lg border text-[10px] ${d.detected ? "bg-red-500/5 border-red-500/20" : "bg-card"}`}>
            <span className={`w-1.5 h-1.5 rounded-full ${d.detected ? "bg-red-500" : "bg-muted-foreground"}`} />
            <span className="w-36 font-medium capitalize">{d.type.replace(/_/g, " ")}</span>
            <span className="flex-1 text-muted-foreground truncate">{d.reason}</span>
            {d.confidence > 0 && (
              <span className="font-mono text-muted-foreground">{d.confidence}%</span>
            )}
          </div>
        ))}
      </div>
    </div>
  )
}
