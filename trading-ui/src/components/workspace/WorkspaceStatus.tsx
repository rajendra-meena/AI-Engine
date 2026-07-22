"use client"

import { cn } from "@/lib/utils"
import { Wifi, WifiOff, Activity } from "lucide-react"
import { useRealtimeStore } from "@/store/useRealtimeStore"

interface WorkspaceStatusProps {
  chartCount: number
  className?: string
}

export function WorkspaceStatus({ chartCount, className }: WorkspaceStatusProps) {
  const connected = useRealtimeStore((s) => s.connection.state === "connected")

  return (
    <div className={cn("flex items-center gap-2 rounded-lg border bg-card px-2 py-1", className)}>
      {connected ? <Wifi className="w-3 h-3 text-emerald-500" /> : <WifiOff className="w-3 h-3 text-red-500" />}
      <span className="text-[8px] text-muted-foreground">{connected ? "Live" : "Offline"}</span>
      <div className="w-px h-3 bg-border" />
      <Activity className="w-3 h-3 text-muted-foreground" />
      <span className="text-[8px] text-muted-foreground">{chartCount} charts</span>
    </div>
  )
}
