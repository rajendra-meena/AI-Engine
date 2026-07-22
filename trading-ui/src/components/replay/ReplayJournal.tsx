"use client"

import { cn } from "@/lib/utils"
import type { ReplayJournalEntry } from "@/store/useReplayStore"

interface ReplayJournalProps {
  entries: ReplayJournalEntry[]
}

function DecisionBadge({ decision }: { decision: string }) {
  const color =
    decision === "HIGH_CONVICTION" ? "text-emerald-500 bg-emerald-500/10" :
    decision === "LOW_CONVICTION" ? "text-amber-500 bg-amber-500/10" :
    decision === "NO_TRADE" ? "text-red-500 bg-red-500/10" :
    "text-muted-foreground bg-muted/30"
  return (
    <span className={cn("inline-flex rounded px-1 py-0.5 text-[8px] font-medium", color)}>
      {decision.replace(/_/g, " ")}
    </span>
  )
}

export function ReplayJournal({ entries }: ReplayJournalProps) {
  if (!entries.length) {
    return (
      <div className="rounded-md border bg-card p-2 text-center">
        <div className="text-[9px] text-muted-foreground/50">No decisions recorded yet</div>
      </div>
    )
  }

  return (
    <div className="rounded-md border bg-card">
      <div className="text-[9px] font-medium text-muted-foreground uppercase tracking-wider px-2 pt-2 pb-1">
        Journal ({entries.length})
      </div>
      <div className="max-h-[240px] overflow-y-auto space-y-0.5 px-2 pb-2">
        {[...entries].reverse().map((entry, i) => (
          <div key={i} className="rounded bg-muted/20 p-1.5 space-y-0.5">
            <div className="flex items-center justify-between">
              <span className="text-[8px] text-muted-foreground font-mono">
                #{entry.index} {new Date(entry.timestamp).toLocaleTimeString("en-IN", { hour: "2-digit", minute: "2-digit" })}
              </span>
              <DecisionBadge decision={entry.decision} />
            </div>
            <div className="flex items-center gap-2 text-[8px] text-muted-foreground">
              <span>Score: {entry.score}</span>
              <span>Conf: {entry.confidence}%</span>
              <span>Risk: {entry.risk_level}</span>
              <span className={entry.direction === "LONG" ? "text-emerald-500" : entry.direction === "SHORT" ? "text-red-500" : ""}>
                {entry.direction}
              </span>
            </div>
            {entry.reasoning.length > 0 && (
              <div className="text-[8px] text-muted-foreground/70 line-clamp-1">
                {entry.reasoning[0]}
              </div>
            )}
          </div>
        ))}
      </div>
    </div>
  )
}
