"use client"

import { useEffect } from "react"
import { motion, AnimatePresence } from "framer-motion"
import { X } from "lucide-react"
import { cn } from "@/lib/utils"
import { EventBadge } from "./EventBadge"
import { useNotificationStore } from "@/store/useNotificationStore"

const CATEGORY_COLORS: Record<string, string> = {
  ai: "border-l-violet-500", indicators: "border-l-blue-500", structure: "border-l-amber-500",
  patterns: "border-l-cyan-500", sr: "border-l-red-500", portfolio: "border-l-emerald-500",
  replay: "border-l-purple-500", scanner: "border-l-orange-500", orders: "border-l-pink-500",
  warnings: "border-l-yellow-500", errors: "border-l-red-600", system: "border-l-gray-500",
}

export function ToastContainer() {
  const lastToast = useNotificationStore((s) => s.lastToast)
  const clearToast = useNotificationStore((s) => s.clearToast)
  const settings = useNotificationStore((s) => s.settings)

  useEffect(() => {
    if (lastToast && settings.autoDismiss) {
      const timer = setTimeout(clearToast, settings.autoDismissSeconds * 1000)
      return () => clearTimeout(timer)
    }
  }, [lastToast, settings.autoDismiss, settings.autoDismissSeconds, clearToast])

  return (
    <div className="fixed top-4 right-4 z-[60] space-y-2">
      <AnimatePresence>
        {lastToast && (
          <motion.div
            initial={{ opacity: 0, y: 20, scale: 0.95 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            exit={{ opacity: 0, y: -10, scale: 0.95 }}
            className={cn(
              "w-[360px] rounded-lg border bg-card shadow-xl p-3 space-y-1 border-l-4",
              CATEGORY_COLORS[lastToast.category] || "border-l-border",
            )}
          >
            <div className="flex items-start gap-2">
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-1.5 mb-0.5">
                  <span className="text-[10px] font-medium">{lastToast.title}</span>
                  <EventBadge priority={lastToast.priority} />
                </div>
                {lastToast.message && (
                  <div className="text-[9px] text-muted-foreground line-clamp-2">{lastToast.message}</div>
                )}
              </div>
              <button
                onClick={clearToast}
                className="rounded p-0.5 text-muted-foreground hover:text-foreground transition-colors shrink-0"
              >
                <X className="w-3 h-3" />
              </button>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  )
}
