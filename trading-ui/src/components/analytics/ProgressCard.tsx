"use client"

import { cn } from "@/lib/utils"

interface ProgressCardProps {
  label: string
  value: number
  max: number
  suffix?: string
  color?: "emerald" | "amber" | "red" | "blue"
  showPercent?: boolean
}

const BAR_COLORS = {
  emerald: "bg-emerald-500",
  amber: "bg-amber-500",
  red: "bg-red-500",
  blue: "bg-blue-500",
}

export function ProgressCard({ label, value, max, suffix = "", color = "blue", showPercent = true }: ProgressCardProps) {
  const pct = max > 0 ? (value / max) * 100 : 0

  return (
    <div className="rounded-lg border bg-card p-2 space-y-1">
      <div className="flex items-center justify-between">
        <span className="text-[9px] text-muted-foreground uppercase tracking-wider">{label}</span>
        <span className={cn("text-[10px] font-mono font-medium", BAR_COLORS[color].replace("bg-", "text-"))}>
          {value}{suffix}
        </span>
      </div>
      <div className="h-1.5 rounded-full bg-muted overflow-hidden">
        <div
          className={cn("h-full rounded-full transition-all duration-500", BAR_COLORS[color])}
          style={{ width: `${Math.min(pct, 100)}%` }}
        />
      </div>
      {showPercent && <div className="text-[8px] text-muted-foreground text-right">{pct.toFixed(1)}%</div>}
    </div>
  )
}
