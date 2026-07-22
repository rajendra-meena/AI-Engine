"use client"

import { cn } from "@/lib/utils"
import type { TradeStatus } from "@/store/useTradePlannerStore"

interface ExecutionStatusProps {
  status: TradeStatus
}

const STATUS_CONFIG: Record<TradeStatus, { color: string; bg: string; label: string }> = {
  WAIT: { color: "text-amber-500", bg: "bg-amber-500/10", label: "WAIT" },
  READY: { color: "text-blue-500", bg: "bg-blue-500/10", label: "READY" },
  HIGH_CONVICTION: { color: "text-emerald-500", bg: "bg-emerald-500/10", label: "HIGH CONVICTION" },
  LOW_CONVICTION: { color: "text-amber-500", bg: "bg-amber-500/10", label: "LOW CONVICTION" },
  NO_TRADE: { color: "text-red-500", bg: "bg-red-500/10", label: "NO TRADE" },
}

export function ExecutionStatus({ status }: ExecutionStatusProps) {
  const cfg = STATUS_CONFIG[status] || STATUS_CONFIG.WAIT

  return (
    <div className={cn("rounded-md border px-3 py-2 text-center", cfg.bg, status === "HIGH_CONVICTION" && "border-emerald-500/30")}>
      <div className="text-[10px] text-muted-foreground uppercase tracking-wider mb-0.5">Status</div>
      <div className={cn("text-sm font-bold tracking-wide", cfg.color)}>
        {cfg.label}
      </div>
    </div>
  )
}
