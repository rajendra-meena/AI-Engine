"use client"

import { useEffect, useCallback } from "react"
import { useNotifications } from "@/hooks/useNotifications"
import { NotificationBell } from "./NotificationBell"
import { NotificationDrawer } from "./NotificationDrawer"
import { ToastContainer } from "./ToastContainer"

/**
 * NotificationCenter — top-level component that wires together:
 * - The notification bell icon (rendered in navbar)
 * - The notification drawer (slide panel)
 * - The toast container (bottom-right popup)
 * - Keyboard shortcut Ctrl+N to toggle drawer
 *
 * Render this once at the app root (e.g., in layout or in each page shell).
 */
export function NotificationCenter() {
  const { unreadCount, toggleDrawer } = useNotifications()

  const handleKeyDown = useCallback((e: KeyboardEvent) => {
    if ((e.ctrlKey || e.metaKey) && e.key === "n") {
      e.preventDefault()
      toggleDrawer()
    }
  }, [toggleDrawer])

  useEffect(() => {
    window.addEventListener("keydown", handleKeyDown)
    return () => window.removeEventListener("keydown", handleKeyDown)
  }, [handleKeyDown])

  return (
    <>
      <NotificationBell unreadCount={unreadCount} onClick={toggleDrawer} />
      <NotificationDrawer />
      <ToastContainer />
    </>
  )
}
