"use client"

import { useLayoutStore } from "@/store/useLayoutStore"
import { cn } from "@/lib/utils"
import { motion } from "framer-motion"
import { useRouter } from "next/navigation"
import {
  LayoutDashboard, TrendingUp, History, Target, Wallet, BarChart3, Settings,
  GitBranch, Radio, Cpu, Lightbulb, Wifi, ChevronLeft, Shield, Brain, Activity,
} from "lucide-react"
import { useCallback, useEffect } from "react"

interface NavItem {
  id: string
  label: string
  icon: React.ReactNode
  href: string
  shortcut?: string
}

const NAV_ITEMS: NavItem[] = [
  { id: "dashboard", label: "Dashboard", icon: <LayoutDashboard className="w-4 h-4" />, href: "/dashboard" },
  { id: "live", label: "Live Trading", icon: <TrendingUp className="w-4 h-4" />, href: "/live" },
  { id: "replay", label: "Replay", icon: <History className="w-4 h-4" />, href: "/workspace" },
  { id: "backtest", label: "Backtest", icon: <Target className="w-4 h-4" />, href: "/backtest" },
  { id: "paper", label: "Paper Trading", icon: <Wallet className="w-4 h-4" />, href: "/portfolio" },
  { id: "strategy", label: "Strategies", icon: <GitBranch className="w-4 h-4" />, href: "/strategy" },
  { id: "intelligence", label: "Intelligence", icon: <Radio className="w-4 h-4" />, href: "/intelligence" },
  { id: "orchestrator", label: "Orchestrator", icon: <Activity className="w-4 h-4" />, href: "/orchestrator" },
  { id: "ml", label: "ML", icon: <Cpu className="w-4 h-4" />, href: "/ml" },
  { id: "learning", label: "AI Learning", icon: <Brain className="w-4 h-4" />, href: "/learning" },
  { id: "risk", label: "Risk Center", icon: <Shield className="w-4 h-4" />, href: "/risk" },
  { id: "command", label: "Command", icon: <Lightbulb className="w-4 h-4" />, href: "/command" },
  { id: "analytics", label: "Analytics", icon: <BarChart3 className="w-4 h-4" />, href: "/research" },
  { id: "settings", label: "Settings", icon: <Settings className="w-4 h-4" />, href: "/settings" },
]

export function Sidebar() {
  const router = useRouter()
  const { sidebarOpen, sidebarWidth, activeNav, setActiveNav, toggleSidebar, setSidebarWidth } = useLayoutStore()

  const handleKeyDown = useCallback(
    (e: KeyboardEvent) => {
      if (e.ctrlKey && e.key === "b") {
        e.preventDefault()
        toggleSidebar()
      }
    },
    [toggleSidebar]
  )

  useEffect(() => {
    window.addEventListener("keydown", handleKeyDown)
    return () => window.removeEventListener("keydown", handleKeyDown)
  }, [handleKeyDown])

  const handleNavClick = useCallback((item: NavItem) => {
    setActiveNav(item.id)
    router.push(item.href)
  }, [router, setActiveNav])

  return (
    <motion.aside
      animate={{ width: sidebarOpen ? sidebarWidth : 70 }}
      transition={{ duration: 0.25, ease: "easeInOut" }}
      className="relative flex flex-col border-r bg-card shrink-0 overflow-hidden"
      role="navigation"
      aria-label="Main navigation"
    >
      {/* Resize handle */}
      {sidebarOpen && (
        <div
          onMouseDown={(e) => {
            const startX = e.clientX
            const startW = sidebarWidth
            const onMouseMove = (ev: MouseEvent) => setSidebarWidth(startW + ev.clientX - startX)
            const onMouseUp = () => {
              document.removeEventListener("mousemove", onMouseMove)
              document.removeEventListener("mouseup", onMouseUp)
            }
            document.addEventListener("mousemove", onMouseMove)
            document.addEventListener("mouseup", onMouseUp)
          }}
          className="absolute right-0 top-0 bottom-0 w-1 cursor-col-resize hover:bg-primary/50 transition-colors z-10"
          role="separator"
          aria-orientation="vertical"
        />
      )}

      <div className="flex flex-col flex-1 py-2 overflow-y-auto">
        {NAV_ITEMS.map((item) => (
          <button
            key={item.id}
            onClick={() => handleNavClick(item)}
            className={cn(
              "flex items-center gap-3 mx-2 px-3 py-2 rounded-md text-sm transition-colors",
              activeNav === item.id
                ? "bg-primary/10 text-primary font-medium"
                : "text-muted-foreground hover:bg-accent hover:text-accent-foreground"
            )}
            aria-current={activeNav === item.id ? "page" : undefined}
            title={sidebarOpen ? undefined : item.label}
          >
            {item.icon}
            {sidebarOpen && (
              <motion.span
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                exit={{ opacity: 0 }}
                className="text-xs"
              >
                {item.label}
              </motion.span>
            )}
          </button>
        ))}
      </div>

      {/* Bottom section */}
      <div className="border-t p-3 space-y-2">
        <div className="flex items-center gap-2 text-[10px] text-muted-foreground">
          <Wifi className={cn("w-3 h-3", sidebarOpen ? "" : "mx-auto")} />
          {sidebarOpen && <span>Yahoo Finance • Connected</span>}
        </div>
        {sidebarOpen && (
          <div className="text-[9px] text-muted-foreground/50">v1.0.0</div>
        )}
      </div>

      {/* Collapse button */}
      <button
        onClick={toggleSidebar}
        className="absolute top-2 -right-3 w-6 h-6 rounded-full border bg-card flex items-center justify-center text-muted-foreground hover:text-foreground transition-colors shadow-sm z-20"
        aria-label={sidebarOpen ? "Collapse sidebar" : "Expand sidebar"}
      >
        <ChevronLeft className={cn("w-3 h-3 transition-transform", !sidebarOpen && "rotate-180")} />
      </button>
    </motion.aside>
  )
}
