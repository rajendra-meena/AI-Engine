"use client"

import { cn } from "@/lib/utils"
import type { ChecklistStatus } from "@/store/useTradePlannerStore"
import { CheckCircle2, XCircle, AlertTriangle } from "lucide-react"

interface ChecklistItemProps {
  label: string
  status: ChecklistStatus
  detail?: string
}

const STATUS_CONFIG: Record<ChecklistStatus, { icon: React.ReactNode; color: string }> = {
  PASS: {
    icon: <CheckCircle2 className="w-3 h-3" />,
    color: "text-emerald-500",
  },
  FAIL: {
    icon: <XCircle className="w-3 h-3" />,
    color: "text-red-500",
  },
  WARNING: {
    icon: <AlertTriangle className="w-3 h-3" />,
    color: "text-amber-500",
  },
}

export function ChecklistItem({ label, status, detail }: ChecklistItemProps) {
  const cfg = STATUS_CONFIG[status] || STATUS_CONFIG.WARNING

  return (
    <div className="flex items-center gap-2 py-1">
      <span className={cn("shrink-0", cfg.color)}>{cfg.icon}</span>
      <span className={cn("text-[10px] flex-1", cfg.color)}>{label}</span>
      {detail && <span className="text-[9px] text-muted-foreground truncate max-w-[100px]">{detail}</span>}
    </div>
  )
}
