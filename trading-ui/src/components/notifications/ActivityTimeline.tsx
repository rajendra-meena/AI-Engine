"use client"

import { useMemo, useState } from "react"
import { cn } from "@/lib/utils"
import type { AppNotification } from "@/store/useNotificationStore"

interface ActivityTimelineProps {
  notifications: AppNotification[]
  maxItems?: number
  className?: string
}

const CATEGORY_DOTS: Record<string, string> = {
  ai: "bg-violet-500", indicators: "bg-blue-500", structure: "bg-amber-500",
  patterns: "bg-cyan-500", sr: "bg-red-500", portfolio: "bg-emerald-500",
  replay: "bg-purple-500", scanner: "bg-orange-500", orders: "bg-pink-500",
  warnings: "bg-yellow-500", errors: "bg-red-600", system: "bg-gray-500",
}

export function ActivityTimeline({ notifications, maxItems = 50, className }: ActivityTimelineProps) {
  const [now] = useState(() => Date.now())
  const grouped = useMemo(() => {
    const today = new Date(now).toDateString()
    const yesterday = new Date(now - 86400000).toDateString()

    const groups: { label: string; items: AppNotification[] }[] = []
    const todayItems: AppNotification[] = []
    const yesterdayItems: AppNotification[] = []
    const olderItems: AppNotification[] = []

    for (const n of notifications.slice(0, maxItems)) {
      const d = new Date(n.timestamp).toDateString()
      if (d === today) todayItems.push(n)
      else if (d === yesterday) yesterdayItems.push(n)
      else olderItems.push(n)
    }

    if (todayItems.length) groups.push({ label: "Today", items: todayItems })
    if (yesterdayItems.length) groups.push({ label: "Yesterday", items: yesterdayItems })
    if (olderItems.length) groups.push({ label: "Older", items: olderItems })
    return groups
  }, [notifications, maxItems, now])

  if (!notifications.length) {
    return <div className="text-center text-[10px] text-muted-foreground/50 py-8">No activity yet</div>
  }

  return (
    <div className={cn("space-y-3", className)}>
      {grouped.map((group) => (
        <div key={group.label}>
          <div className="text-[9px] font-medium text-muted-foreground uppercase tracking-wider mb-1.5 px-1">
            {group.label}
          </div>
          <div className="relative">
            {/* Timeline line */}
            <div className="absolute left-[7px] top-2 bottom-2 w-px bg-border" />

            <div className="space-y-1.5">
              {group.items.map((n) => (
                <div key={n.id} className="flex items-start gap-2.5 relative pl-1">
                  {/* Dot */}
                  <div className={cn(
                    "w-3 h-3 rounded-full border-2 border-background mt-0.5 shrink-0 z-10",
                    CATEGORY_DOTS[n.category] || "bg-muted-foreground",
                    !n.read && "ring-2 ring-primary/30",
                  )} />

                  {/* Content */}
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-1.5">
                      <span className="text-[8px] text-muted-foreground font-mono">
                        {new Date(n.timestamp).toLocaleTimeString("en-IN", { hour: "2-digit", minute: "2-digit" })}
                      </span>
                      <span className={cn("text-[9px] font-medium", !n.read ? "text-foreground" : "text-muted-foreground")}>
                        {n.title}
                      </span>
                    </div>
                    {n.message && (
                      <div className="text-[8px] text-muted-foreground/70 line-clamp-1">{n.message}</div>
                    )}
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      ))}
    </div>
  )
}
