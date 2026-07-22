"use client"

import Link from "next/link"
import { usePathname } from "next/navigation"
import { useTheme } from "next-themes"
import { useEffect, useState } from "react"
import { Brain, BarChart3, Activity, Target, Settings, Briefcase, BrainCircuit, LayoutDashboard, GitBranch, FlaskConical, Cpu, Sun, Moon } from "lucide-react"
import { NotificationCenter } from "@/components/notifications/NotificationCenter"
import { cn } from "@/lib/utils"
import { Button } from "@/components/ui/button"

const NAV_ITEMS = [
  { href: "/dashboard", label: "Dashboard", icon: BarChart3 },
  { href: "/live", label: "Live", icon: Activity },
  { href: "/workspace", label: "Charts", icon: LayoutDashboard },
  { href: "/command", label: "Command", icon: Cpu },
  { href: "/strategy", label: "Strategies", icon: GitBranch },
  { href: "/portfolio", label: "Portfolio", icon: Briefcase },
  { href: "/settings", label: "Settings", icon: Settings },
]

export function Navbar() {
  const pathname = usePathname()
  const { theme, setTheme } = useTheme()
  const [mounted, setMounted] = useState(false)
  // eslint-disable-next-line react-hooks/set-state-in-effect
  useEffect(() => { setMounted(true) }, [])

  return (
    <header className="sticky top-0 z-50 w-full border-b bg-background/80 backdrop-blur-xl">
      <div className="flex h-14 items-center px-4 gap-4 max-w-[1580px] mx-auto">
        <Link href="/dashboard" className="flex items-center gap-2 mr-4">
          <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-blue-600 to-indigo-600 flex items-center justify-center shadow-lg shadow-blue-200/20">
            <Brain className="w-4 h-4 text-white" />
          </div>
          <span className="font-bold text-sm hidden sm:inline">
            Market<span className="text-blue-600 dark:text-blue-400">Mind</span> AI
          </span>
        </Link>

        <nav className="flex items-center gap-1">
          {NAV_ITEMS.map((item) => (
            <Link key={item.href} href={item.href}>
              <Button
                variant={pathname.startsWith(item.href) ? "secondary" : "ghost"}
                size="sm"
                className="gap-1.5"
              >
                <item.icon className="w-4 h-4" />
                <span className="hidden sm:inline text-xs">{item.label}</span>
              </Button>
            </Link>
          ))}
        </nav>

        <div className="ml-auto flex items-center gap-1">
          <NotificationCenter />
          {mounted && (
            <Button variant="ghost" size="icon" onClick={() => setTheme(theme === "dark" ? "light" : "dark")}>
              {theme === "dark" ? <Sun className="w-4 h-4" /> : <Moon className="w-4 h-4" />}
            </Button>
          )}
        </div>
      </div>
    </header>
  )
}
