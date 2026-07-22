"use client"

import { cn } from "@/lib/utils"

interface ContributionBarProps {
  label: string
  value: number
  max?: number
  color?: string
  detail?: string
  size?: "sm" | "md" | "lg"
}

export function ContributionBar({ label, value, max = 100, color = "#6366f1", detail, size = "sm" }: ContributionBarProps) {
  const pct = Math.min(100, (value / max) * 100)

  return (
    <div className="space-y-0.5">
      <div className="flex items-center justify-between">
        <span className={cn("text-muted-foreground", size === "sm" ? "text-[9px]" : "text-[10px]")}>{label}</span>
        <span className={cn("font-mono font-medium", size === "sm" ? "text-[9px]" : "text-[10px]")} style={{ color }}>{value}{detail ?? ""}</span>
      </div>
      <div className="h-1.5 rounded-full bg-muted overflow-hidden">
        <div className="h-full rounded-full transition-all duration-500" style={{ width: `${pct}%`, backgroundColor: color }} />
      </div>
    </div>
  )
}
