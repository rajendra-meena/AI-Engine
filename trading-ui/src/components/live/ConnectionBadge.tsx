"use client"

import { useConnectionStatus } from "@/hooks/useConnectionStatus"
import { cn } from "@/lib/utils"

export function ConnectionBadge() {
  const { state, latency, quality } = useConnectionStatus()

  const colorMap: Record<string, string> = {
    connected: "bg-emerald-500",
    reconnecting: "bg-amber-500",
    connecting: "bg-amber-500",
    disconnected: "bg-red-500",
  }

  const labelMap: Record<string, string> = {
    connected: "Connected",
    reconnecting: "Reconnecting",
    connecting: "Connecting",
    disconnected: "Disconnected",
  }

  return (
    <div className="flex items-center gap-1.5" title={`${state} · ${latency}ms · ${quality}`}>
      <span className={cn("w-1.5 h-1.5 rounded-full animate-pulse", colorMap[state] || "bg-gray-500")} />
      <span className="text-[10px] text-muted-foreground hidden sm:inline">
        {labelMap[state] || state}
      </span>
      {state === "connected" && (
        <span className="text-[9px] text-muted-foreground/50">{latency}ms</span>
      )}
    </div>
  )
}
