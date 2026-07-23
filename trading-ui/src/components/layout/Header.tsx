"use client"

import { useTheme } from "next-themes"
import { useEffect, useState } from "react"
import { useRouter } from "next/navigation"
import { Brain, Search, Sun, Moon, Bell, Settings, Menu, ChevronDown } from "lucide-react"
import { useLayoutStore } from "@/store/useLayoutStore"
import { useNotificationStore } from "@/store/useNotificationStore"
import { NotificationDrawer } from "@/components/notifications/NotificationDrawer"
import { ToastContainer } from "@/components/notifications/ToastContainer"
import { ConnectionBadge } from "@/components/live/ConnectionBadge"
import { ReplayBadge } from "@/components/live/ReplayBadge"
import { cn } from "@/lib/utils"

const SYMBOLS = [
  { label: "NIFTY 50", value: "NIFTY 50" },
  { label: "BANKNIFTY", value: "BANKNIFTY" },
  { label: "SENSEX", value: "SENSEX" },
]

const TIMEFRAMES = ["1m", "3m", "5m", "15m", "30m", "60m"]

export function Header() {
  const router = useRouter()
  const { theme, setTheme } = useTheme()
  const [mounted, setMounted] = useState(false)
  const toggleSidebar = useLayoutStore((s) => s.toggleSidebar)
  const toggleDrawer = useNotificationStore((s) => s.toggleDrawer)
  // eslint-disable-next-line react-hooks/set-state-in-effect
  useEffect(() => { setMounted(true) }, [])

  return (
    <header className="flex h-14 items-center gap-3 border-b bg-card px-4 shrink-0" role="banner">
      {/* Menu toggle */}
      <button
        onClick={toggleSidebar}
        className="rounded-md p-1.5 text-muted-foreground hover:bg-accent hover:text-accent-foreground transition-colors"
        aria-label="Toggle sidebar"
      >
        <Menu className="w-4 h-4" />
      </button>

      {/* Logo */}
      <div className="flex items-center gap-2 mr-4">
        <div className="w-7 h-7 rounded-md bg-gradient-to-br from-blue-600 to-indigo-600 flex items-center justify-center">
          <Brain className="w-4 h-4 text-white" />
        </div>
        <span className="font-bold text-sm hidden sm:inline">
          Market<span className="text-blue-500">Mind</span>
        </span>
      </div>

      {/* Search */}
      <div className="hidden md:flex items-center gap-1.5 rounded-md border bg-muted/50 px-2.5 py-1.5 text-xs text-muted-foreground flex-1 max-w-xs">
        <Search className="w-3.5 h-3.5" />
        <span>Search symbols...</span>
        <span className="ml-auto text-[10px] text-muted-foreground/50">Ctrl+K</span>
      </div>

      {/* Symbol select */}
      <select className="h-7 rounded-md border bg-muted/50 px-2 text-xs font-medium text-foreground focus:outline-none focus:ring-1 focus:ring-ring">
        {SYMBOLS.map((s) => (
          <option key={s.value} value={s.value}>{s.label}</option>
        ))}
      </select>

      {/* Timeframe buttons */}
      <div className="hidden sm:flex items-center rounded-md border overflow-hidden">
        {TIMEFRAMES.map((tf) => (
          <button
            key={tf}
            className={cn(
              "px-2 py-1 text-[11px] font-medium transition-colors",
              tf === "15m"
                ? "bg-primary text-primary-foreground"
                : "bg-card text-muted-foreground hover:bg-accent hover:text-accent-foreground"
            )}
          >
            {tf}
          </button>
        ))}
      </div>

      {/* Notification drawer + toast rendered here so the bell in Header works */}
      <NotificationDrawer />
      <ToastContainer />

      <div className="ml-auto flex items-center gap-1">
        {/* Connection badge */}
        <div className="hidden md:flex items-center">
          <ConnectionBadge />
        </div>

        {/* Replay badge */}
        <ReplayBadge />

        {/* Market status */}
        <div className="hidden lg:flex items-center gap-1.5 rounded-md bg-emerald-500/10 border border-emerald-500/20 px-2 py-1">
          <span className="w-1.5 h-1.5 rounded-full bg-emerald-500 animate-pulse" />
          <span className="text-[10px] font-medium text-emerald-500">Open</span>
        </div>

        {/* Notifications */}
        <button onClick={toggleDrawer} className="rounded-md p-1.5 text-muted-foreground hover:bg-accent hover:text-accent-foreground transition-colors" aria-label="Notifications">
          <Bell className="w-4 h-4" />
        </button>

        {/* Theme toggle */}
        {mounted && (
          <button
            onClick={() => setTheme(theme === "dark" ? "light" : "dark")}
            className="rounded-md p-1.5 text-muted-foreground hover:bg-accent hover:text-accent-foreground transition-colors"
            aria-label="Toggle theme"
          >
            {theme === "dark" ? <Sun className="w-4 h-4" /> : <Moon className="w-4 h-4" />}
          </button>
        )}

        {/* Settings */}
        <button onClick={() => router.push("/settings")} className="rounded-md p-1.5 text-muted-foreground hover:bg-accent hover:text-accent-foreground transition-colors" aria-label="Settings">
          <Settings className="w-4 h-4" />
        </button>

        {/* User */}
        <button className="flex items-center gap-1.5 rounded-md px-2 py-1 text-muted-foreground hover:bg-accent hover:text-accent-foreground transition-colors">
          <div className="w-6 h-6 rounded-full bg-muted-foreground/20 flex items-center justify-center text-[10px] font-medium">
            TR
          </div>
          <ChevronDown className="w-3 h-3" />
        </button>
      </div>
    </header>
  )
}
