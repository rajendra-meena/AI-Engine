"use client"

import { cn } from "@/lib/utils"

const REGIME_CONFIG: Record<string, { color: string; bg: string; label: string }> = {
  STRONG_BULL_TREND: { color: "text-emerald-500", bg: "bg-emerald-500/10 border-emerald-500/20", label: "Strong Bull Trend" },
  STRONG_BEAR_TREND: { color: "text-red-500", bg: "bg-red-500/10 border-red-500/20", label: "Strong Bear Trend" },
  WEAK_BULL_TREND: { color: "text-emerald-400", bg: "bg-emerald-400/10 border-emerald-400/20", label: "Weak Bull Trend" },
  WEAK_BEAR_TREND: { color: "text-red-400", bg: "bg-red-400/10 border-red-400/20", label: "Weak Bear Trend" },
  SIDEWAYS_RANGE: { color: "text-amber-500", bg: "bg-amber-500/10 border-amber-500/20", label: "Sideways Range" },
  HIGH_VOLATILITY: { color: "text-orange-500", bg: "bg-orange-500/10 border-orange-500/20", label: "High Volatility" },
  LOW_VOLATILITY: { color: "text-blue-300", bg: "bg-blue-300/10 border-blue-300/20", label: "Low Volatility" },
  BREAKOUT: { color: "text-violet-500", bg: "bg-violet-500/10 border-violet-500/20", label: "Breakout" },
  FAKE_BREAKOUT: { color: "text-rose-500", bg: "bg-rose-500/10 border-rose-500/20", label: "Fake Breakout" },
  MEAN_REVERSION: { color: "text-cyan-500", bg: "bg-cyan-500/10 border-cyan-500/20", label: "Mean Reversion" },
  NEWS_DRIVEN: { color: "text-pink-500", bg: "bg-pink-500/10 border-pink-500/20", label: "News Driven" },
  OPENING_AUCTION: { color: "text-yellow-500", bg: "bg-yellow-500/10 border-yellow-500/20", label: "Opening Auction" },
  CLOSING_SESSION: { color: "text-orange-400", bg: "bg-orange-400/10 border-orange-400/20", label: "Closing Session" },
  ILLIQUID_MARKET: { color: "text-gray-500", bg: "bg-gray-500/10 border-gray-500/20", label: "Illiquid Market" },
}

export function RegimeBadge({ regime, className }: { regime: string | null | undefined; className?: string }) {
  if (!regime) return null
  const cfg = REGIME_CONFIG[regime]
  if (!cfg) {
    return <span className={cn("text-[10px] text-muted-foreground", className)}>{regime.replace(/_/g, " ")}</span>
  }
  return (
    <span className={cn("inline-flex items-center gap-1 rounded-md border px-1.5 py-0.5 text-[9px] font-medium", cfg.bg, cfg.color, className)}>
      {cfg.label}
    </span>
  )
}

export function StabilityMeter({ value }: { value: number | null | undefined }) {
  const pct = value != null ? Math.round(value * 100) : 0
  return (
    <div className="space-y-0.5">
      <div className="flex justify-between text-[9px]">
        <span className="text-muted-foreground">Stability</span>
        <span className={cn("font-mono font-medium", pct >= 70 ? "text-emerald-500" : pct >= 40 ? "text-amber-500" : "text-red-500")}>
          {pct}%
        </span>
      </div>
      <div className="w-full h-1.5 rounded-full bg-muted/30 overflow-hidden">
        <div className="h-full rounded-full transition-all" style={{ width: `${pct}%`, backgroundColor: pct >= 70 ? "#22c55e" : pct >= 40 ? "#f59e0b" : "#ef4444" }} />
      </div>
    </div>
  )
}

export function ConfidenceGauge({ value, label }: { value: number; label?: string }) {
  return (
    <div className="space-y-0.5">
      {label && <div className="text-[9px] text-muted-foreground uppercase">{label}</div>}
      <div className="flex items-center gap-2">
        <div className="flex-1 h-2 rounded-full bg-muted/30 overflow-hidden">
          <div className="h-full rounded-full transition-all" style={{ width: `${value}%`, backgroundColor: value >= 80 ? "#22c55e" : value >= 60 ? "#3b82f6" : value >= 40 ? "#f59e0b" : "#ef4444" }} />
        </div>
        <span className={cn("text-xs font-bold font-mono", value >= 80 ? "text-emerald-500" : value >= 60 ? "text-blue-500" : value >= 40 ? "text-amber-500" : "text-red-500")}>
          {value}%
        </span>
      </div>
    </div>
  )
}

export function StrategyScore({ primary, secondary, avoid }: { primary?: string; secondary?: string; avoid?: string[] }) {
  return (
    <div className="space-y-1 text-[10px]">
      {primary && <div className="flex items-center gap-1"><span className="w-1.5 h-1.5 rounded-full bg-emerald-500" /><span className="font-medium text-emerald-500">Primary: {primary.replace(/_/g, " ")}</span></div>}
      {secondary && <div className="flex items-center gap-1"><span className="w-1.5 h-1.5 rounded-full bg-blue-500" /><span className="text-muted-foreground">Secondary: {secondary.replace(/_/g, " ")}</span></div>}
      {avoid && avoid.length > 0 && (
        <div className="flex items-center gap-1">
          <span className="w-1.5 h-1.5 rounded-full bg-red-500" />
          <span className="text-red-500">Avoid: {avoid.map(s => s.replace(/_/g, " ")).join(", ")}</span>
        </div>
      )}
    </div>
  )
}

export function MetricCard({ label, value, color }: { label: string; value: string; color?: string }) {
  return (
    <div className="rounded-lg border bg-card p-3 text-center">
      <div className="text-[9px] text-muted-foreground uppercase tracking-wider">{label}</div>
      <div className={cn("text-lg font-bold font-mono mt-0.5", color || "")}>{value}</div>
    </div>
  )
}
