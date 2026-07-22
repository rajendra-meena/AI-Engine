"use client"

import { motion } from "framer-motion"

interface RewardGaugeProps {
  expectedRR: number
  netRR: number
  size?: "sm" | "md" | "lg"
}

function rrColor(rr: number): string {
  if (rr >= 3) return "#22c55e"
  if (rr >= 2) return "#16a34a"
  if (rr >= 1) return "#f59e0b"
  if (rr >= 0.5) return "#f97316"
  return "#ef4444"
}

export function RewardGauge({ expectedRR, netRR, size = "md" }: RewardGaugeProps) {
  const dimensions = size === "lg" ? 120 : size === "sm" ? 64 : 88
  const strokeWidth = size === "lg" ? 10 : size === "sm" ? 6 : 8
  const radius = (dimensions - strokeWidth) / 2
  const circumference = 2 * Math.PI * radius

  // Map RR to percentage (1:1 scale, capped at 5:1)
  const rrPercent = Math.min((expectedRR / 5) * 100, 100)
  const offset = circumference - (rrPercent / 100) * circumference
  const color = rrColor(expectedRR)
  const track = color + "20"

  return (
    <div className="flex flex-col items-center gap-1">
      <svg width={dimensions} height={dimensions} className="transform -rotate-90">
        <circle cx={dimensions / 2} cy={dimensions / 2} r={radius} fill="none" stroke={track} strokeWidth={strokeWidth} />
        <motion.circle
          cx={dimensions / 2}
          cy={dimensions / 2}
          r={radius}
          fill="none"
          stroke={color}
          strokeWidth={strokeWidth}
          strokeLinecap="round"
          strokeDasharray={circumference}
          initial={{ strokeDashoffset: circumference }}
          animate={{ strokeDashoffset: offset }}
          transition={{ duration: 1, ease: "easeOut" }}
        />
      </svg>
      <span className="text-[18px] font-bold font-mono" style={{ color }}>
        {expectedRR.toFixed(1)}R
      </span>
      <span className="text-[9px] text-muted-foreground">Net: {netRR.toFixed(1)}R</span>
    </div>
  )
}
