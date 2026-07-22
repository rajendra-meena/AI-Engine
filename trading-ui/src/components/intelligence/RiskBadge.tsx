"use client"

import { cn } from "@/lib/utils"

const RISK_CONFIG: Record<string, { color: string; label: string }> = {
  LOW: { color: "text-emerald-500 bg-emerald-500/10 border-emerald-500/20", label: "Low Risk" },
  MEDIUM: { color: "text-amber-500 bg-amber-500/10 border-amber-500/20", label: "Medium Risk" },
  HIGH: { color: "text-red-500 bg-red-500/10 border-red-500/20", label: "High Risk" },
  VERY_HIGH: { color: "text-red-600 bg-red-600/10 border-red-600/20", label: "Very High Risk" },
  EXTREME: { color: "text-red-600 bg-red-600/10 border-red-600/20 animate-pulse", label: "Extreme Risk" },
}

export function RiskBadge({ level }: { level: string | null | undefined }) {
  if (!level) return null
  const cfg = RISK_CONFIG[level]
  if (!cfg) return <span className="text-[10px] text-muted-foreground">{level}</span>
  return (
    <span className={cn("inline-flex rounded-md border px-1.5 py-0.5 text-[9px] font-medium", cfg.color)}>
      {cfg.label}
    </span>
  )
}

const CONFIDENCE_COLOR = (v: number) =>
  v >= 80 ? "text-emerald-500" : v >= 60 ? "text-blue-500" : v >= 40 ? "text-amber-500" : "text-red-500"

export function ConfidenceBadge({ value }: { value: number | null | undefined }) {
  if (value == null) return null
  return (
    <span className={cn("text-[11px] font-bold font-mono", CONFIDENCE_COLOR(value))}>
      {value}%
    </span>
  )
}

export function ProgressBar({ value, className }: { value: number; className?: string }) {
  const color = value >= 80 ? "bg-emerald-500" : value >= 60 ? "bg-blue-500" : value >= 40 ? "bg-amber-500" : "bg-red-500"
  return (
    <div className={cn("h-1 rounded-full bg-muted overflow-hidden", className)}>
      <div className={cn("h-full transition-all duration-500", color)} style={{ width: `${Math.max(0, Math.min(100, value))}%` }} />
    </div>
  )
}

const DECISION_COLORS: Record<string, string> = {
  HIGH_CONVICTION: "text-emerald-500",
  MODERATE: "text-blue-500",
  LOW_CONVICTION: "text-amber-500",
  NO_TRADE: "text-red-500",
  WAIT: "text-amber-500",
}

export function DecisionBadge({ value }: { value: string | null | undefined }) {
  if (!value) return null
  return (
    <span className={cn("text-[11px] font-bold font-mono", DECISION_COLORS[value] || "text-muted-foreground")}>
      {value.replace(/_/g, " ")}
    </span>
  )
}
