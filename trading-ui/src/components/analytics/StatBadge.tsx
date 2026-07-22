"use client"

import { cn } from "@/lib/utils"

interface StatBadgeProps {
  label: string
  value: string | number
  color?: "emerald" | "red" | "amber" | "blue" | "violet" | "neutral"
  size?: "sm" | "md"
}

const COLOR_CONFIG = {
  emerald: "text-emerald-500 bg-emerald-500/10 border-emerald-500/20",
  red: "text-red-500 bg-red-500/10 border-red-500/20",
  amber: "text-amber-500 bg-amber-500/10 border-amber-500/20",
  blue: "text-blue-500 bg-blue-500/10 border-blue-500/20",
  violet: "text-violet-500 bg-violet-500/10 border-violet-500/20",
  neutral: "text-muted-foreground bg-muted/30 border-border",
}

export function StatBadge({ label, value, color = "neutral", size = "sm" }: StatBadgeProps) {
  return (
    <div className={cn(
      "rounded-md border inline-flex items-center gap-1.5",
      COLOR_CONFIG[color],
      size === "sm" ? "px-1.5 py-0.5" : "px-2 py-1",
    )}>
      <span className={cn("text-muted-foreground/70", size === "sm" ? "text-[8px]" : "text-[9px]")}>{label}</span>
      <span className={cn("font-mono font-bold", size === "sm" ? "text-[10px]" : "text-xs")}>{value}</span>
    </div>
  )
}
