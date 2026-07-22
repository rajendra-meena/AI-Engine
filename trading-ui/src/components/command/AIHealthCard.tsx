"use client"

import { motion } from "framer-motion"
import { cn } from "@/lib/utils"

interface AIHealthCardProps {
  label: string
  value: string | number
  status: "healthy" | "degraded" | "down" | "warning"
  detail?: string
}

const STATUS_CONFIG = {
  healthy: { dot: "bg-emerald-500", text: "text-emerald-500", bg: "bg-emerald-500/5" },
  degraded: { dot: "bg-amber-500", text: "text-amber-500", bg: "bg-amber-500/5" },
  down: { dot: "bg-red-500", text: "text-red-500", bg: "bg-red-500/5" },
  warning: { dot: "bg-amber-500", text: "text-amber-500", bg: "bg-amber-500/5" },
}

export function AIHealthCard({ label, value, status, detail }: AIHealthCardProps) {
  const cfg = STATUS_CONFIG[status]
  return (
    <motion.div initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} className={cn("rounded-lg border bg-card p-3 space-y-1", cfg.bg)}>
      <div className="flex items-center justify-between">
        <span className="text-[9px] text-muted-foreground uppercase tracking-wider">{label}</span>
        <span className={cn("w-2 h-2 rounded-full", cfg.dot)} />
      </div>
      <div className={cn("text-lg font-bold font-mono", cfg.text)}>{value}</div>
      {detail && <div className="text-[8px] text-muted-foreground">{detail}</div>}
    </motion.div>
  )
}
