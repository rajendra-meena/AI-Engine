"use client"

// WebSocket event payloads are loosely typed
/* eslint-disable @typescript-eslint/no-explicit-any */

import { useCallback, useEffect, useRef } from "react"
import { useNotificationStore, type NotificationCategory, type NotificationPriority } from "@/store/useNotificationStore"
import { notificationService } from "@/services/notificationService"
import { getWSManager } from "@/services/websocketManager"

/**
 * useNotifications — connects the WebSocket event stream to the notification store.
 *
 * Subscribes to all backend event types and maps them to structured notifications.
 * Also handles synthetic events (connection status, errors).
 */
export function useNotifications() {
  const store = useNotificationStore()
  const wsCleanup = useRef<(() => void)[]>([])

  /* ── Subscribe to all WebSocket events ── */
  useEffect(() => {
    const ws = getWSManager()

    // Listen for all events via the wildcard dispatcher
    const unsubAll = ws.onEvent("*", (payload: any) => {
      const eventType = payload?.type || payload?.event || "unknown"
      if (eventType === "pong" || eventType === "welcome") return

      const notification = notificationService.eventToNotification({
        type: eventType,
        payload: payload?.payload || payload,
      })
      store.addNotification(notification)
    })

    // Specific backend event types to subscribe to
    const BACKEND_EVENTS = [
      "ai_decision_updated",
      "indicator_updated", "indicators_updated",
      "structure_updated", "bos_detected", "choch_detected",
      "pattern_detected", "breakout_detected",
      "sr_updated", "sr_supply_zone_created", "sr_demand_zone_created",
      "replay_started", "replay_stopped", "replay_paused",
      "replay_resumed", "replay_finished", "replay_seek",
      "scanner_alert",
      "trade_executed", "position_closed", "order_filled",
      "system_status", "provider_status",
    ]

    const unsubs = BACKEND_EVENTS.map((eventType) =>
      ws.onEvent(eventType, (payload: any) => {
        store.addNotification(
          notificationService.eventToNotification({ type: eventType, payload })
        )
      })
    )

    wsCleanup.current = [unsubAll, ...unsubs]

    // Request notification permission
    if (typeof window !== "undefined" && "Notification" in window && Notification.permission === "default") {
      Notification.requestPermission()
    }

    return () => {
      wsCleanup.current.forEach((fn) => fn())
    }
  }, [])

  /* ── Connection status monitoring ── */
  useEffect(() => {
    const ws = getWSManager()
    const unsubState = ws.onState((state) => {
      if (state === "connected") {
        store.addNotification(
          notificationService.createNotification("connection_restored")
        )
      } else if (state === "disconnected" || state === "reconnecting") {
        store.addNotification(
          notificationService.createNotification("connection_lost")
        )
      }
    })
    wsCleanup.current.push(unsubState)
    return () => {
      wsCleanup.current.forEach((fn) => { void fn() })
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  const markAsRead = useCallback((id: string) => store.markAsRead(id), [store])
  const markAllAsRead = useCallback(() => store.markAllAsRead(), [store])
  const dismissNotification = useCallback((id: string) => store.dismissNotification(id), [store])
  const deleteNotification = useCallback((id: string) => store.deleteNotification(id), [store])
  const clearAll = useCallback(() => store.clearAll(), [store])
  const toggleDrawer = useCallback(() => store.toggleDrawer(), [store])
  const setDrawerOpen = useCallback((open: boolean) => store.setDrawerOpen(open), [store])
  const setFilterCategory = useCallback((cat: NotificationCategory | null) => store.setFilterCategory(cat), [store])
  const setFilterPriority = useCallback((pri: NotificationPriority | null) => store.setFilterPriority(pri), [store])
  const setSearchQuery = useCallback((q: string) => store.setSearchQuery(q), [store])
  const updateSettings = useCallback((s: Partial<typeof store.settings>) => store.updateSettings(s), [store])

  return {
    notifications: store.notifications,
    unreadCount: store.unreadCount,
    settings: store.settings,
    drawerOpen: store.drawerOpen,
    filterCategory: store.filterCategory,
    filterPriority: store.filterPriority,
    searchQuery: store.searchQuery,
    lastToast: store.lastToast,

    markAsRead,
    markAllAsRead,
    dismissNotification,
    deleteNotification,
    clearAll,
    toggleDrawer,
    setDrawerOpen,
    setFilterCategory,
    setFilterPriority,
    setSearchQuery,
    updateSettings,
    toggleCategory: store.toggleCategory,
    togglePriority: store.togglePriority,
    clearToast: store.clearToast,
  }
}
