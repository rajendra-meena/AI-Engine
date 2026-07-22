"use client"

import { cn } from "@/lib/utils"

interface MetricCardProps {
  label: string
  value: string | number | null | undefined
  trend?: "up" | "down" | "neutral"
  className?: string
  valueClass?: string
}

export function MetricCard({ label, value, trend, className, valueClass }: MetricCardProps) {
  const color = trend === "up" ? "text-emerald-500" : trend === "down" ? "text-red-500" : ""
  return (
    <div className={cn("flex items-center justify-between", className)}>
      <span className="text-[10px] text-muted-foreground">{label}</span>
      <span className={cn("text-[11px] font-mono font-medium", color, valueClass)}>
        {value ?? "--"}
      </span>
    </div>
  )
}
