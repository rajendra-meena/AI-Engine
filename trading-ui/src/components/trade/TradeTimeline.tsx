"use client"

import { cn } from "@/lib/utils"
import { motion } from "framer-motion"
import { CheckCircle2, Clock, Circle } from "lucide-react"
import type { TimelineEvent } from "@/store/useTradePlannerStore"

interface TradeTimelineProps {
  events: TimelineEvent[]
}

export function TradeTimeline({ events }: TradeTimelineProps) {
  if (!events.length) return null

  return (
    <div className="space-y-0">
      {events.map((event, i) => (
        <div key={event.id} className="flex items-start gap-2 relative pb-2 last:pb-0">
          {/* Connector line */}
          {i < events.length - 1 && (
            <div className={cn(
              "absolute left-[7px] top-4 w-px h-full",
              event.completed ? "bg-emerald-500/30" : "bg-border"
            )} />
          )}

          {/* Icon */}
          <div className="shrink-0 mt-0.5">
            {event.completed ? (
              <CheckCircle2 className="w-3.5 h-3.5 text-emerald-500" />
            ) : event.active ? (
              <motion.div
                animate={{ opacity: [1, 0.4, 1] }}
                transition={{ duration: 2, repeat: Infinity }}
              >
                <Clock className="w-3.5 h-3.5 text-amber-500" />
              </motion.div>
            ) : (
              <Circle className="w-3.5 h-3.5 text-muted-foreground/30" />
            )}
          </div>

          {/* Content */}
          <div className="flex-1 min-w-0">
            <div className={cn(
              "text-[10px] font-medium",
              event.completed ? "text-emerald-500" : event.active ? "text-foreground" : "text-muted-foreground/50"
            )}>
              {event.label}
            </div>
            {event.timestamp && (
              <div className="text-[8px] text-muted-foreground">
                {new Date(event.timestamp).toLocaleTimeString("en-IN", { hour: "2-digit", minute: "2-digit" })}
              </div>
            )}
          </div>
        </div>
      ))}
    </div>
  )
}
