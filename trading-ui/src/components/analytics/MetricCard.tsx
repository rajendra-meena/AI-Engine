"use client"

import { cn } from "@/lib/utils"
import { motion } from "framer-motion"

interface MetricCardProps {
  label: string
  value: string | number
  prefix?: string
  suffix?: string
  color?: "default" | "bullish" | "bearish" | "warning" | "neutral"
  delta?: number
  icon?: React.ReactNode
  className?: string
}

const COLOR_MAP = {
  default: "text-foreground",
  bullish: "text-emerald-500",
  bearish: "text-red-500",
  warning: "text-amber-500",
  neutral: "text-muted-foreground",
}

export function MetricCard({ label, value, prefix, suffix, color = "default", delta, icon, className }: MetricCardProps) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      className={cn("rounded-lg border bg-card p-3 space-y-1", className)}
    >
      <div className="flex items-center justify-between">
        <span className="text-[10px] text-muted-foreground uppercase tracking-wider">{label}</span>
        {icon && <span className="text-muted-foreground">{icon}</span>}
      </div>
      <div className={cn("text-xl font-bold font-mono tracking-tight", COLOR_MAP[color])}>
        {prefix}{typeof value === "number" ? value.toLocaleString("en-IN", { maximumFractionDigits: 2 }) : value}{suffix}
      </div>
      {delta != null && (
        <div className={cn("text-[10px]", delta >= 0 ? "text-emerald-500" : "text-red-500")}>
          {delta >= 0 ? "+" : ""}{delta.toFixed(2)}%
        </div>
      )}
    </motion.div>
  )
}
