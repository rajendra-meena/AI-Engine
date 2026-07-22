"use client"

import { cn } from "@/lib/utils"
import { TrendingUp, TrendingDown, Minus } from "lucide-react"

interface PerformanceBadgeProps {
  value: number
  label?: string
  invert?: boolean
}

export function PerformanceBadge({ value, label, invert = false }: PerformanceBadgeProps) {
  const isPositive = invert ? value < 0 : value > 0
  const isNegative = invert ? value > 0 : value < 0
  const Icon = isPositive ? TrendingUp : isNegative ? TrendingDown : Minus

  return (
    <span className={cn(
      "inline-flex items-center gap-1 rounded-md border px-1.5 py-0.5 text-[10px] font-medium",
      isPositive ? "text-emerald-500 bg-emerald-500/10 border-emerald-500/20" :
      isNegative ? "text-red-500 bg-red-500/10 border-red-500/20" :
      "text-muted-foreground bg-muted/30 border-border",
    )}>
      <Icon className="w-3 h-3" />
      {label && <span>{label}</span>}
      {value > 0 ? "+" : ""}{value.toFixed(2)}%
    </span>
  )
}
