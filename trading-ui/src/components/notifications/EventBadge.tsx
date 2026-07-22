"use client"

import { cn } from "@/lib/utils"
import type { NotificationPriority } from "@/store/useNotificationStore"

interface EventBadgeProps {
  priority: NotificationPriority
}

const CONFIG: Record<NotificationPriority, { color: string; dot: string }> = {
  INFO: { color: "bg-blue-500/20 text-blue-500 border-blue-500/30", dot: "bg-blue-500" },
  SUCCESS: { color: "bg-emerald-500/20 text-emerald-500 border-emerald-500/30", dot: "bg-emerald-500" },
  WARNING: { color: "bg-amber-500/20 text-amber-500 border-amber-500/30", dot: "bg-amber-500" },
  CRITICAL: { color: "bg-red-500/20 text-red-500 border-red-500/30", dot: "bg-red-500" },
}

export function EventBadge({ priority }: EventBadgeProps) {
  const cfg = CONFIG[priority]
  return (
    <span className={cn("inline-flex items-center gap-1 rounded-md border px-1.5 py-0.5 text-[8px] font-medium", cfg.color)}>
      <span className={cn("w-1.5 h-1.5 rounded-full", cfg.dot)} />
      {priority}
    </span>
  )
}
