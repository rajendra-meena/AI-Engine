"use client"

import { Wifi, WifiOff } from "lucide-react"
import { useBrokerStore } from "@/store/useBrokerStore"

export function BrokerConnectionBadge() {
  const authenticated = useBrokerStore((s) => s.authenticated)
  const connected = useBrokerStore((s) => s.connected)
  const userName = useBrokerStore((s) => s.user_name || s.user_id)

  if (!authenticated) return null

  const color = connected ? "text-emerald-500 border-emerald-500/20 bg-emerald-500/10" : "text-amber-500 border-amber-500/20 bg-amber-500/10"
  const StatusIcon = connected ? Wifi : WifiOff

  return (
    <div className={`hidden lg:flex items-center gap-1 rounded-md border px-2 py-1 ${color}`}>
      <StatusIcon className="w-3 h-3" />
      <span className="text-[9px] font-medium whitespace-nowrap">{userName || "Zerodha"}</span>
    </div>
  )
}
