"use client"

import { cn } from "@/lib/utils"
import { motion } from "framer-motion"

interface RiskGaugeProps {
  level: "LOW" | "MEDIUM" | "HIGH" | "EXTREME"
  score: number
  size?: "sm" | "md" | "lg"
}

const GAUGE_CONFIG: Record<string, { color: string; track: string; label: string }> = {
  LOW: { color: "#22c55e", track: "#22c55e20", label: "Low Risk" },
  MEDIUM: { color: "#f59e0b", track: "#f59e0b20", label: "Medium Risk" },
  HIGH: { color: "#ef4444", track: "#ef444420", label: "High Risk" },
  EXTREME: { color: "#dc2626", track: "#dc262620", label: "Extreme Risk" },
}

export function RiskGauge({ level, score, size = "md" }: RiskGaugeProps) {
  const cfg = GAUGE_CONFIG[level] || GAUGE_CONFIG.MEDIUM
  const dimensions = size === "lg" ? 120 : size === "sm" ? 64 : 88
  const strokeWidth = size === "lg" ? 10 : size === "sm" ? 6 : 8
  const radius = (dimensions - strokeWidth) / 2
  const circumference = 2 * Math.PI * radius
  const offset = circumference - (Math.min(score, 100) / 100) * circumference

  return (
    <div className="flex flex-col items-center gap-1">
      <svg width={dimensions} height={dimensions} className="transform -rotate-90">
        <circle cx={dimensions / 2} cy={dimensions / 2} r={radius} fill="none" stroke={cfg.track} strokeWidth={strokeWidth} />
        <motion.circle
          cx={dimensions / 2}
          cy={dimensions / 2}
          r={radius}
          fill="none"
          stroke={cfg.color}
          strokeWidth={strokeWidth}
          strokeLinecap="round"
          strokeDasharray={circumference}
          initial={{ strokeDashoffset: circumference }}
          animate={{ strokeDashoffset: offset }}
          transition={{ duration: 1, ease: "easeOut" }}
        />
      </svg>
      <span className={cn("text-[9px] font-medium", level === "LOW" ? "text-emerald-500" : level === "MEDIUM" ? "text-amber-500" : "text-red-500")}>
        {cfg.label}
      </span>
      <span className="text-[18px] font-bold font-mono">{score}</span>
    </div>
  )
}
