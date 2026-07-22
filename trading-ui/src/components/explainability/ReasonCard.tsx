"use client"

import { cn } from "@/lib/utils"

interface ReasonCardProps {
  label: string
  value: string | number
  status?: "positive" | "negative" | "neutral"
  detail?: string
}

const STATUS_COLORS = {
  positive: "border-l-emerald-500 bg-emerald-500/5",
  negative: "border-l-red-500 bg-red-500/5",
  neutral: "border-l-muted bg-muted/10",
}

export function ReasonCard({ label, value, status = "neutral", detail }: ReasonCardProps) {
  return (
    <div className={cn("rounded-md border border-l-4 p-2", STATUS_COLORS[status])}>
      <div className="flex items-center justify-between">
        <span className="text-[9px] text-muted-foreground">{label}</span>
        <span className={cn("text-[10px] font-mono font-bold", status === "positive" ? "text-emerald-500" : status === "negative" ? "text-red-500" : "")}>{value}</span>
      </div>
      {detail && <div className="text-[8px] text-muted-foreground mt-0.5">{detail}</div>}
    </div>
  )
}
