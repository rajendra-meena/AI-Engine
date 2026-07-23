"use client"

import React, { useState } from "react"
import { ChevronDown, ChevronRight } from "lucide-react"
import { cn } from "@/lib/utils"

interface PanelSectionProps {
  icon?: React.ReactNode
  title: string
  defaultOpen?: boolean
  children: React.ReactNode
  className?: string
}

export function PanelSection({ icon, title, defaultOpen = true, children, className }: PanelSectionProps) {
  const [open, setOpen] = useState(defaultOpen)

  return (
    <div className={cn("rounded-lg border bg-card", className)}>
      <button
        onClick={() => setOpen(!open)}
        className="flex w-full items-center gap-2 px-3 py-2 text-xs font-medium text-muted-foreground hover:text-foreground transition-colors"
        aria-expanded={open}
      >
        {icon && <span className="shrink-0">{icon}</span>}
        <span className="flex-1 text-left">{title}</span>
        {open ? <ChevronDown className="w-3 h-3" /> : <ChevronRight className="w-3 h-3" />}
      </button>
      {open && (
        <div className="px-3 pb-3 pt-1 text-xs text-muted-foreground">{children}</div>
      )}
    </div>
  )
}
