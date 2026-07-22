"use client"

import { useConnectionStatus } from "@/hooks/useConnectionStatus"
import { cn } from "@/lib/utils"

export function LatencyBadge() {
  const { latency, quality } = useConnectionStatus()

  const colorMap: Record<string, string> = {
    excellent: "text-emerald-500",
    good: "text-blue-500",
    fair: "text-amber-500",
    poor: "text-red-500",
    dead: "text-gray-500",
  }

  return (
    <span className={cn("text-[10px] font-mono font-medium", colorMap[quality] || "text-gray-500")} title={`Quality: ${quality}`}>
      {latency}ms
    </span>
  )
}
