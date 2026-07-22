"use client"

import { useMemo, useState } from "react"
import { cn } from "@/lib/utils"
import { motion } from "framer-motion"
import { X, Circle, CheckCircle2 } from "lucide-react"
import { EventBadge } from "./EventBadge"
import type { AppNotification } from "@/store/useNotificationStore"

interface NotificationCardProps {
  notification: AppNotification
  onMarkRead: (id: string) => void
  onDelete: (id: string) => void
}

const CATEGORY_COLORS: Record<string, string> = {
  ai: "text-violet-500", indicators: "text-blue-500", structure: "text-amber-500",
  patterns: "text-cyan-500", sr: "text-red-500", portfolio: "text-emerald-500",
  replay: "text-purple-500", scanner: "text-orange-500", orders: "text-pink-500",
  warnings: "text-yellow-500", errors: "text-red-600", system: "text-muted-foreground",
}

function formatTimeAgo(timestamp: string, now: number): string {
  const diff = now - new Date(timestamp).getTime()
  if (diff < 60000) return "just now"
  if (diff < 3600000) return `${Math.floor(diff / 60000)}m ago`
  if (diff < 86400000) return `${Math.floor(diff / 3600000)}h ago`
  return `${Math.floor(diff / 86400000)}d ago`
}

export function NotificationCard({ notification, onMarkRead, onDelete }: NotificationCardProps) {
  const [now] = useState(() => Date.now())
  const timeStr = useMemo(() => formatTimeAgo(notification.timestamp, now), [notification.timestamp, now])

  return (
    <motion.div
      initial={{ opacity: 0, y: -8 }}
      animate={{ opacity: 1, y: 0 }}
      className={cn(
        "group relative rounded-lg border p-2.5 transition-colors cursor-pointer",
        notification.read ? "bg-card border-border" : "bg-muted/30 border-primary/20",
      )}
      onClick={() => !notification.read && onMarkRead(notification.id)}
    >
      <div className="flex items-start gap-2">
        {/* Unread indicator */}
        {!notification.read && (
          <Circle className="w-2 h-2 fill-primary text-primary mt-1.5 shrink-0" />
        )}
        {notification.read && <div className="w-2 shrink-0" />}

        <div className="flex-1 min-w-0 space-y-1">
          {/* Header */}
          <div className="flex items-center gap-1.5 flex-wrap">
            <span className={cn("text-[9px] font-medium uppercase tracking-wider", CATEGORY_COLORS[notification.category] || "")}>
              {notification.category}
            </span>
            <EventBadge priority={notification.priority} />
            <span className="text-[8px] text-muted-foreground ml-auto">{timeStr}</span>
          </div>

          {/* Title */}
          <div className="text-[10px] font-medium leading-tight">{notification.title}</div>

          {/* Message */}
          {notification.message && (
            <div className="text-[9px] text-muted-foreground leading-tight line-clamp-2">{notification.message}</div>
          )}

          {/* Action */}
          {notification.action && (
            <button className="text-[9px] text-primary hover:text-primary/80 font-medium transition-colors">
              {notification.action.label}
            </button>
          )}
        </div>

        {/* Actions */}
        <div className="flex items-center gap-0.5 opacity-0 group-hover:opacity-100 transition-opacity shrink-0">
          {!notification.read && (
            <button
              onClick={(e) => { e.stopPropagation(); onMarkRead(notification.id) }}
              className="rounded p-0.5 text-muted-foreground hover:text-foreground transition-colors"
              title="Mark read"
            >
              <CheckCircle2 className="w-3 h-3" />
            </button>
          )}
          <button
            onClick={(e) => { e.stopPropagation(); onDelete(notification.id) }}
            className="rounded p-0.5 text-muted-foreground hover:text-red-500 transition-colors"
            title="Delete"
          >
            <X className="w-3 h-3" />
          </button>
        </div>
      </div>
    </motion.div>
  )
}
