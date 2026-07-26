"use client"

import { useTheme } from "next-themes"
import { useEffect, useState } from "react"
import { useRouter, usePathname } from "next/navigation"
import { Brain, Search, Sun, Moon, Settings, Menu, ChevronDown } from "lucide-react"
import { useLayoutStore } from "@/store/useLayoutStore"
import { useMarketStore } from "@/store/useMarketStore"
import { useChartStore } from "@/store/useChartStore"
import { useNotificationStore } from "@/store/useNotificationStore"
import { useBrokerStore } from "@/store/useBrokerStore"
import { NotificationBell } from "@/components/notifications/NotificationBell"
import { NotificationDrawer } from "@/components/notifications/NotificationDrawer"
import { ToastContainer } from "@/components/notifications/ToastContainer"
import { ConnectionBadge } from "@/components/live/ConnectionBadge"
import { BrokerConnectionBadge } from "@/components/live/BrokerConnectionBadge"
import { ReplayBadge } from "@/components/live/ReplayBadge"
const SYMBOLS = [
  { label: "NIFTY 50", value: "NIFTY 50" },
  { label: "BANKNIFTY", value: "BANKNIFTY" },
  { label: "SENSEX", value: "SENSEX" },
]

export function Header() {
  const router = useRouter()
  const pathname = usePathname()
  const { theme, setTheme } = useTheme()
  const [mounted, setMounted] = useState(false)
  const toggleSidebar = useLayoutStore((s) => s.toggleSidebar)
  const unreadCount = useNotificationStore((s) => s.unreadCount)
  const toggleDrawer = useNotificationStore((s) => s.toggleDrawer)
  const selectedSymbol = useMarketStore((s) => s.selectedSymbol)
  const setSelectedSymbol = useMarketStore((s) => s.setSelectedSymbol)
  const setChartSymbol = useChartStore((s) => s.setSymbol)
  const userId = useBrokerStore((s) => s.user_id)
  const userName = useBrokerStore((s) => s.user_name)
  const displayLabel = userId || userName
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

      {/* Symbol — Dashboard only */}
      <div style={{ display: pathname === "/dashboard" ? "contents" : "none" }}>
        <select
          value={selectedSymbol}
          onChange={(e) => {
            setSelectedSymbol(e.target.value)
            setChartSymbol(e.target.value)
          }}
          className="h-7 rounded-md border bg-muted/50 px-2 text-xs font-medium text-foreground focus:outline-none focus:ring-1 focus:ring-ring"
        >
          {SYMBOLS.map((s) => (
            <option key={s.value} value={s.value}>{s.label}</option>
          ))}
        </select>
      </div>

      {/* Notification drawer + toast rendered here so the bell in Header works */}
      <NotificationDrawer />
      <ToastContainer />

      <div className="ml-auto flex items-center gap-1">
        {/* Connection badge */}
        <div className="hidden md:flex items-center">
          <ConnectionBadge />
        </div>

        {/* Broker connection badge */}
        <BrokerConnectionBadge />

        {/* Replay badge */}
        <ReplayBadge />

        {/* Market status */}
        <div className="hidden lg:flex items-center gap-1.5 rounded-md bg-emerald-500/10 border border-emerald-500/20 px-2 py-1">
          <span className="w-1.5 h-1.5 rounded-full bg-emerald-500 animate-pulse" />
          <span className="text-[10px] font-medium text-emerald-500">Open</span>
        </div>

        {/* Notifications */}
        <NotificationBell unreadCount={unreadCount} onClick={toggleDrawer} />

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
          <div className="w-6 h-6 rounded-full bg-gradient-to-br from-blue-500 to-indigo-600 flex items-center justify-center text-[10px] font-medium text-white">
            {displayLabel ? displayLabel.charAt(0).toUpperCase() : "U"}
          </div>
          <span className="text-[10px] font-medium hidden sm:inline">{displayLabel || "User"}</span>
          <ChevronDown className="w-3 h-3" />
        </button>
      </div>
    </header>
  )
}
