"use client"

import { useEffect, type ReactNode } from "react"
import { usePathname } from "next/navigation"
import { Header } from "@/components/layout/Header"
import { Sidebar } from "@/components/layout/Sidebar"
import { useLayoutStore } from "@/store/useLayoutStore"
import { useRealtime } from "@/hooks/useRealtime"
import { cn } from "@/lib/utils"

interface AppLayoutProps {
  children: ReactNode
  /** Optional content rendered below the main row (e.g. Dashboard BottomPanel) */
  bottom?: ReactNode
  /** Additional classes on the flex-1 content area (the row beside Sidebar) */
  className?: string
}

/**
 * AppLayout — shared application shell that wraps every page with the
 * Dashboard-style Header + Sidebar and auto-detects the active nav item
 * from the current pathname.
 *
 * Children render directly beside the sidebar — no padding/max-width wrapper.
 * Use <PageContent /> inside children for standard page padding, or pass a
 * `bottom` slot for content below the main row (e.g. BottomPanel).
 */
export function AppLayout({ children, bottom, className }: AppLayoutProps) {
  const pathname = usePathname()
  const setActiveNav = useLayoutStore((s) => s.setActiveNav)

  // Auto-detect active nav from the current route
  useEffect(() => {
    const segment = pathname?.split("/")[1] ?? ""
    setActiveNav(segment === "" ? "dashboard" : segment)
  }, [pathname, setActiveNav])

  // Standard realtime hook (safe to call unconditionally — idempotent)
  useRealtime()

  return (
    <div className="h-screen flex flex-col bg-background overflow-hidden">
      <Header />
      <div className="flex flex-1 overflow-hidden">
        <Sidebar />
        <div className={cn("flex-1 overflow-auto", className)}>
          {children}
        </div>
      </div>
      {bottom}
    </div>
  )
}

/**
 * PageContent — standard padded content wrapper for most pages.
 * Provides consistent max-width and padding.
 */
export function PageContent({ children, className }: { children: ReactNode; className?: string }) {
  return (
    <div
      className={cn("p-4 md:p-6 w-full", className)}
      style={{ maxWidth: "1580px", marginLeft: "auto", marginRight: "auto" }}
    >
      {children}
    </div>
  )
}
