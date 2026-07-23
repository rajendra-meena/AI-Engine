"use client"

import { useMemo, useCallback } from "react"
import { motion, AnimatePresence } from "framer-motion"
import { X, CheckCheck, Trash2, Bell, Settings } from "lucide-react"
import { cn } from "@/lib/utils"
import { NotificationCard } from "./NotificationCard"
import { NotificationFilter } from "./NotificationFilter"
import { NotificationSettingsPanel } from "./NotificationSettings"
import { useNotifications } from "@/hooks/useNotifications"
import { useState } from "react"

interface NotificationDrawerProps {
  className?: string
}

export function NotificationDrawer({ className }: NotificationDrawerProps) {
  const notif = useNotifications()
  const [showSettings, setShowSettings] = useState(false)

  const filteredNotifications = useMemo(() => {
    let result = notif.notifications.filter((n) => !n.dismissed)

    if (notif.filterCategory) {
      result = result.filter((n) => n.category === notif.filterCategory)
    }
    if (notif.filterPriority) {
      result = result.filter((n) => n.priority === notif.filterPriority)
    }
    if (notif.searchQuery) {
      const q = notif.searchQuery.toLowerCase()
      result = result.filter(
        (n) => n.title.toLowerCase().includes(q) || n.message.toLowerCase().includes(q)
      )
    }
    return result
  }, [notif.notifications, notif.filterCategory, notif.filterPriority, notif.searchQuery])

  const handleKeyDown = useCallback((e: React.KeyboardEvent) => {
    if (e.key === "Escape") notif.setDrawerOpen(false)
  }, [notif])

  return (
    <AnimatePresence>
      {notif.drawerOpen && (
        <>
          {/* Backdrop */}
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="fixed inset-0 z-50 bg-black/20"
            onClick={() => notif.setDrawerOpen(false)}
          />

          {/* Drawer */}
          <motion.div
            initial={{ x: "100%" }}
            animate={{ x: 0 }}
            exit={{ x: "100%" }}
            transition={{ type: "spring", damping: 25, stiffness: 300 }}
            className={cn(
              "fixed right-0 top-0 bottom-0 z-50 w-[420px] max-w-[95vw] bg-card border-l shadow-2xl flex flex-col h-screen",
              className,
            )}
            onKeyDown={handleKeyDown}
          >
            {/* Header */}
            <div className="flex items-center justify-between px-4 py-3 border-b shrink-0">
              <div className="flex items-center gap-2">
                <Bell className="w-4 h-4 text-primary" />
                <span className="text-sm font-bold">Notifications</span>
                {notif.unreadCount > 0 && (
                  <span className="rounded-full bg-primary/20 text-primary text-[9px] font-medium px-1.5 py-0.5">
                    {notif.unreadCount} new
                  </span>
                )}
              </div>
              <div className="flex items-center gap-1">
                <button
                  onClick={() => setShowSettings(!showSettings)}
                  className={cn("rounded p-1.5 transition-colors", showSettings ? "text-primary bg-primary/10" : "text-muted-foreground hover:text-foreground hover:bg-accent")}
                  title="Settings"
                >
                  <Settings className="w-3.5 h-3.5" />
                </button>
                <button
                  onClick={notif.markAllAsRead}
                  className="rounded p-1.5 text-muted-foreground hover:text-foreground hover:bg-accent transition-colors"
                  title="Mark all read"
                  disabled={notif.unreadCount === 0}
                >
                  <CheckCheck className="w-3.5 h-3.5" />
                </button>
                <button
                  onClick={notif.clearAll}
                  className="rounded p-1.5 text-muted-foreground hover:text-red-500 hover:bg-accent transition-colors"
                  title="Clear all"
                >
                  <Trash2 className="w-3.5 h-3.5" />
                </button>
                <button
                  onClick={() => notif.setDrawerOpen(false)}
                  className="rounded p-1.5 text-muted-foreground hover:text-foreground hover:bg-accent transition-colors"
                >
                  <X className="w-3.5 h-3.5" />
                </button>
              </div>
            </div>

            {/* Settings or Filters */}
            {showSettings ? (
              <div className="px-3 py-2 border-b overflow-y-auto max-h-[40vh]">
                <NotificationSettingsPanel
                  settings={notif.settings}
                  onUpdate={notif.updateSettings}
                  onToggleCategory={notif.toggleCategory}
                  onTogglePriority={notif.togglePriority}
                />
              </div>
            ) : (
              <div className="px-3 py-2 border-b shrink-0">
                <NotificationFilter
                  filterCategory={notif.filterCategory}
                  filterPriority={notif.filterPriority}
                  searchQuery={notif.searchQuery}
                  onCategoryChange={notif.setFilterCategory}
                  onPriorityChange={notif.setFilterPriority}
                  onSearchChange={notif.setSearchQuery}
                  onClear={() => {
                    notif.setFilterCategory(null)
                    notif.setFilterPriority(null)
                    notif.setSearchQuery("")
                  }}
                />
              </div>
            )}

            {/* Notification list */}
            <div className="flex-1 overflow-y-auto p-2 space-y-1.5">
              {filteredNotifications.length === 0 ? (
                <div className="flex flex-col items-center justify-center h-full text-center">
                  <Bell className="w-8 h-8 text-muted-foreground/20 mb-2" />
                  <div className="text-[10px] text-muted-foreground/50">No notifications</div>
                </div>
              ) : (
                filteredNotifications.map((n) => (
                  <NotificationCard
                    key={n.id}
                    notification={n}
                    onMarkRead={notif.markAsRead}
                    onDelete={notif.deleteNotification}
                  />
                ))
              )}
            </div>

            {/* Footer */}
            <div className="px-3 py-1.5 border-t text-[8px] text-muted-foreground text-center shrink-0">
              {notif.notifications.length} notifications · {notif.unreadCount} unread · Press Esc to close
            </div>
          </motion.div>
        </>
      )}
    </AnimatePresence>
  )
}
