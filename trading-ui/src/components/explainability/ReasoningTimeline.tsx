"use client"

import { cn } from "@/lib/utils"
import { ArrowDown, AlertTriangle, CheckCircle2, Info } from "lucide-react"
import type { ReasoningEvent } from "@/services/explainabilityService"

interface ReasoningTimelineProps {
  events: ReasoningEvent[]
}

const EVENT_ICONS = {
  info: <Info className="w-3 h-3" />,
  change: <ArrowDown className="w-3 h-3" />,
  warning: <AlertTriangle className="w-3 h-3" />,
  positive: <CheckCircle2 className="w-3 h-3" />,
}

const EVENT_COLORS = {
  info: "text-blue-500 border-blue-500/30",
  change: "text-amber-500 border-amber-500/30",
  warning: "text-red-500 border-red-500/30",
  positive: "text-emerald-500 border-emerald-500/30",
}

export function ReasoningTimeline({ events }: ReasoningTimelineProps) {
  if (!events.length) return <div className="rounded-lg border bg-card p-3 text-[10px] text-muted-foreground text-center">No reasoning events</div>

  return (
    <div className="rounded-lg border bg-card p-3 space-y-1">
      <div className="text-[9px] font-medium text-muted-foreground uppercase tracking-wider">Reasoning Timeline</div>
      <div className="relative">
        <div className="absolute left-[11px] top-3 bottom-3 w-px bg-border" />
        <div className="space-y-2">
          {events.map((ev, i) => (
            <div key={i} className="flex items-start gap-2.5 pl-1">
              <div className={cn("w-5 h-5 rounded-full border flex items-center justify-center bg-card shrink-0 z-10", EVENT_COLORS[ev.type])}>
                {EVENT_ICONS[ev.type]}
              </div>
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-1.5">
                  <span className="text-[8px] text-muted-foreground font-mono">{new Date(ev.timestamp).toLocaleTimeString("en-IN", { hour: "2-digit", minute: "2-digit" })}</span>
                  <span className="text-[10px] font-medium">{ev.event}</span>
                </div>
                <div className="text-[9px] text-muted-foreground">{ev.detail}</div>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}
