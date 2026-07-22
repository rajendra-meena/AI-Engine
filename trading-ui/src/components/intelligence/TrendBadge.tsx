"use client"
/* eslint-disable @typescript-eslint/no-explicit-any */

import { cn } from "@/lib/utils"
import { TrendingUp, TrendingDown, Minus } from "lucide-react"

const TREND_CONFIG: Record<string, { icon: any; color: string; label: string }> = {
  UPTREND: { icon: TrendingUp, color: "text-emerald-500 bg-emerald-500/10 border-emerald-500/20", label: "Uptrend" },
  DOWNTREND: { icon: TrendingDown, color: "text-red-500 bg-red-500/10 border-red-500/20", label: "Downtrend" },
  BULLISH: { icon: TrendingUp, color: "text-emerald-500 bg-emerald-500/10 border-emerald-500/20", label: "Bullish" },
  BEARISH: { icon: TrendingDown, color: "text-red-500 bg-red-500/10 border-red-500/20", label: "Bearish" },
}

export function TrendBadge({ value }: { value: string | null | undefined }) {
  if (!value) return null
  const cfg = TREND_CONFIG[value] || { icon: Minus, color: "text-muted-foreground bg-muted/30", label: value }
  const Icon = cfg.icon
  return (
    <span className={cn("inline-flex items-center gap-1 rounded-md border px-1.5 py-0.5 text-[9px] font-medium", cfg.color)}>
      <Icon className="w-2.5 h-2.5" />
      {cfg.label}
    </span>
  )
}

const STRENGTH_COLORS: Record<string, string> = {
  STRONG: "text-emerald-500", VERY_STRONG: "text-emerald-400",
  MODERATE: "text-amber-500", NORMAL: "text-blue-500",
  WEAK: "text-red-500", VERY_WEAK: "text-red-400",
}

export function StrengthBadge({ value }: { value: string | null | undefined }) {
  if (!value) return null
  return (
    <span className={cn("text-[10px] font-semibold font-mono", STRENGTH_COLORS[value] || "text-muted-foreground")}>
      {value}
    </span>
  )
}
