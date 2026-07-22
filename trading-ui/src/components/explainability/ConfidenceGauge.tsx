"use client"

import { motion } from "framer-motion"

interface ConfidenceGaugeProps {
  confidence: number
  label?: string
}

export function ConfidenceGauge({ confidence, label = "Confidence" }: ConfidenceGaugeProps) {
  const color = confidence >= 80 ? "#22c55e" : confidence >= 60 ? "#3b82f6" : confidence >= 40 ? "#f59e0b" : "#ef4444"
  const strokeWidth = 8
  const radius = 36
  const circumference = 2 * Math.PI * radius
  const offset = circumference - (confidence / 100) * circumference

  return (
    <div className="flex flex-col items-center gap-1">
      <svg width={88} height={88} className="transform -rotate-90">
        <circle cx={44} cy={44} r={radius} fill="none" stroke="hsl(var(--muted))" strokeWidth={strokeWidth} />
        <motion.circle
          cx={44} cy={44} r={radius} fill="none" stroke={color}
          strokeWidth={strokeWidth} strokeLinecap="round"
          strokeDasharray={circumference}
          initial={{ strokeDashoffset: circumference }}
          animate={{ strokeDashoffset: offset }}
          transition={{ duration: 1, ease: "easeOut" }}
        />
      </svg>
      <span className="text-xl font-bold font-mono" style={{ color }}>{confidence}%</span>
      <span className="text-[9px] text-muted-foreground">{label}</span>
    </div>
  )
}
