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
    // (single subscription avoids duplicate notifications from per-type listeners)
    const unsubAll = ws.onEvent("*", (payload: any) => {
      const eventType = payload?.type || payload?.event || "unknown"
      if (eventType === "pong" || eventType === "welcome") return

      const notification = notificationService.eventToNotification({
        type: eventType,
        payload: payload?.payload || payload,
      })
      useNotificationStore.getState().addNotification(notification)
    })

    wsCleanup.current = [unsubAll]

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
        useNotificationStore.getState().addNotification(
          notificationService.createNotification("connection_restored")
        )
      } else if (state === "disconnected" || state === "reconnecting") {
        useNotificationStore.getState().addNotification(
          notificationService.createNotification("connection_lost")
        )
      }
    })
    return () => {
      unsubState()
    }
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
