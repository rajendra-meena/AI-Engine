"use client"

import { Bell } from "lucide-react"
import { cn } from "@/lib/utils"

interface NotificationBellProps {
  unreadCount: number
  onClick: () => void
  className?: string
}

export function NotificationBell({ unreadCount, onClick, className }: NotificationBellProps) {
  return (
    <button
      onClick={onClick}
      className={cn("relative rounded-md p-1.5 text-muted-foreground hover:text-foreground hover:bg-accent transition-colors", className)}
      aria-label={`Notifications${unreadCount > 0 ? ` (${unreadCount} unread)` : ""}`}
    >
      <Bell className="w-4 h-4" />
      {unreadCount > 0 && (
        <span className="absolute -top-0.5 -right-0.5 flex items-center justify-center min-w-[16px] h-4 rounded-full bg-red-500 text-[8px] font-bold text-white px-1 shadow-lg">
          {unreadCount > 99 ? "99+" : unreadCount}
        </span>
      )}
    </button>
  )
}
