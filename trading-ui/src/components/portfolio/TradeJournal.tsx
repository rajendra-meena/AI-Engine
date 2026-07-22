"use client"

import { cn } from "@/lib/utils"
import type { JournalEntry } from "@/store/usePortfolioStore"

interface TradeJournalProps {
  entries: JournalEntry[]
  className?: string
}

export function TradeJournal({ entries, className }: TradeJournalProps) {
  if (!entries.length) {
    return <div className={cn("rounded-lg border bg-card p-6 text-center text-[10px] text-muted-foreground", className)}>No journal entries yet</div>
  }

  return (
    <div className={cn("rounded-lg border bg-card", className)}>
      <div className="text-[9px] font-medium text-muted-foreground uppercase tracking-wider px-3 pt-2 pb-1">Trade Journal ({entries.length})</div>
      <div className="max-h-[400px] overflow-y-auto px-2 pb-2 space-y-1">
        {[...entries].reverse().map((entry) => (
          <div key={entry.id} className="rounded bg-muted/20 p-2 space-y-1">
            <div className="flex items-center justify-between">
              <span className="text-[9px] font-medium">{entry.symbol}</span>
              <span className={cn("text-[8px] px-1 py-0.5 rounded font-medium", entry.result === "win" ? "bg-emerald-500/10 text-emerald-500" : entry.result === "loss" ? "bg-red-500/10 text-red-500" : "bg-muted/30 text-muted-foreground")}>
                {entry.result || "open"}
              </span>
            </div>
            <div className="flex items-center gap-2 text-[8px] text-muted-foreground">
              <span className={entry.direction === "LONG" ? "text-emerald-500" : "text-red-500"}>{entry.direction}</span>
              <span>Entry: {entry.entry.toFixed(2)}</span>
              {entry.exit && <span>Exit: {entry.exit.toFixed(2)}</span>}
              {entry.aiScore != null && <span>Score: {entry.aiScore}</span>}
            </div>
            {entry.notes && <div className="text-[8px] text-muted-foreground/70">{entry.notes}</div>}
          </div>
        ))}
      </div>
    </div>
  )
}
