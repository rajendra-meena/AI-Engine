import { create } from "zustand"
import { persist } from "zustand/middleware"

/* ─── Types ─── */

export type NotificationPriority = "INFO" | "SUCCESS" | "WARNING" | "CRITICAL"
export type NotificationCategory =
  | "ai" | "indicators" | "structure" | "patterns" | "sr"
  | "portfolio" | "replay" | "scanner" | "orders"
  | "warnings" | "errors" | "system"

export interface AppNotification {
  id: string
  title: string
  message: string
  timestamp: string
  category: NotificationCategory
  priority: NotificationPriority
  read: boolean
  dismissed: boolean
  action?: { label: string; href?: string; onClick?: () => void }
  source?: string
}

export interface NotificationSettings {
  enabled: boolean
  sound: boolean
  desktop: boolean
  autoDismiss: boolean
  autoDismissSeconds: number
  maxHistory: number
  categories: Record<NotificationCategory, boolean>
  priorities: Record<NotificationPriority, boolean>
}

/* ─── Store ─── */

interface NotificationState {
  notifications: AppNotification[]
  unreadCount: number
  settings: NotificationSettings
  drawerOpen: boolean
  filterCategory: NotificationCategory | null
  filterPriority: NotificationPriority | null
  searchQuery: string
  lastToast: AppNotification | null

  /* Actions */
  addNotification: (notification: Omit<AppNotification, "id" | "timestamp" | "read" | "dismissed">) => void
  markAsRead: (id: string) => void
  markAllAsRead: () => void
  dismissNotification: (id: string) => void
  dismissAll: () => void
  deleteNotification: (id: string) => void
  clearAll: () => void
  setDrawerOpen: (open: boolean) => void
  toggleDrawer: () => void
  setFilterCategory: (category: NotificationCategory | null) => void
  setFilterPriority: (priority: NotificationPriority | null) => void
  setSearchQuery: (query: string) => void
  updateSettings: (partial: Partial<NotificationSettings>) => void
  toggleCategory: (category: NotificationCategory) => void
  togglePriority: (priority: NotificationPriority) => void
  clearToast: () => void
  reset: () => void
}

const DEFAULT_SETTINGS: NotificationSettings = {
  enabled: true,
  sound: false,
  desktop: false,
  autoDismiss: true,
  autoDismissSeconds: 5,
  maxHistory: 500,
  categories: {
    ai: true, indicators: true, structure: true, patterns: true, sr: true,
    portfolio: true, replay: true, scanner: true, orders: true,
    warnings: true, errors: true, system: true,
  },
  priorities: { INFO: true, SUCCESS: true, WARNING: true, CRITICAL: true },
}

let _notifId = 0
const genId = () => `notif_${++_notifId}_${Date.now()}`

export const useNotificationStore = create<NotificationState>()(
  persist(
    (set, get) => ({
      notifications: [],
      unreadCount: 0,
      settings: { ...DEFAULT_SETTINGS },
      drawerOpen: false,
      filterCategory: null,
      filterPriority: null,
      searchQuery: "",
      lastToast: null,

      addNotification: (partial) => {
        const state = get()
        if (!state.settings.enabled) return
        if (!state.settings.categories[partial.category]) return
        if (!state.settings.priorities[partial.priority]) return

        const notification: AppNotification = {
          ...partial,
          id: genId(),
          timestamp: new Date().toISOString(),
          read: false,
          dismissed: false,
        }

        set((s) => {
          const updated = [notification, ...s.notifications].slice(0, s.settings.maxHistory)
          const unreadCount = updated.filter((n) => !n.read).length
          return { notifications: updated, unreadCount, lastToast: notification }
        })

        // Desktop notification
        if (state.settings.desktop && "Notification" in window && Notification.permission === "granted") {
          new Notification(notification.title, { body: notification.message })
        }
      },

      markAsRead: (id) =>
        set((s) => {
          const notifications = s.notifications.map((n) => (n.id === id ? { ...n, read: true } : n))
          return { notifications, unreadCount: notifications.filter((n) => !n.read).length }
        }),

      markAllAsRead: () =>
        set((s) => ({
          notifications: s.notifications.map((n) => ({ ...n, read: true })),
          unreadCount: 0,
        })),

      dismissNotification: (id) =>
        set((s) => ({
          notifications: s.notifications.map((n) => (n.id === id ? { ...n, dismissed: true } : n)),
        })),

      dismissAll: () =>
        set((s) => ({
          notifications: s.notifications.map((n) => ({ ...n, dismissed: true })),
        })),

      deleteNotification: (id) =>
        set((s) => {
          const notifications = s.notifications.filter((n) => n.id !== id)
          return { notifications, unreadCount: notifications.filter((n) => !n.read).length }
        }),

      clearAll: () => set({ notifications: [], unreadCount: 0 }),

      setDrawerOpen: (drawerOpen) => set({ drawerOpen }),
      toggleDrawer: () => set((s) => ({ drawerOpen: !s.drawerOpen })),
      setFilterCategory: (filterCategory) => set({ filterCategory }),
      setFilterPriority: (filterPriority) => set({ filterPriority }),
      setSearchQuery: (searchQuery) => set({ searchQuery }),

      updateSettings: (partial) =>
        set((s) => ({ settings: { ...s.settings, ...partial } })),

      toggleCategory: (category) =>
        set((s) => ({
          settings: {
            ...s.settings,
            categories: { ...s.settings.categories, [category]: !s.settings.categories[category] },
          },
        })),

      togglePriority: (priority) =>
        set((s) => ({
          settings: {
            ...s.settings,
            priorities: { ...s.settings.priorities, [priority]: !s.settings.priorities[priority] },
          },
        })),

      clearToast: () => set({ lastToast: null }),

      reset: () => set({ notifications: [], unreadCount: 0, lastToast: null }),
    }),
    {
      name: "marketmind-notifications",
      partialize: (state) => ({
        notifications: state.notifications.slice(0, 200),
        unreadCount: state.unreadCount,
        settings: state.settings,
      }),
    }
  )
)
