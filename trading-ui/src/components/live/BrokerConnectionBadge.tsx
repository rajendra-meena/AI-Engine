"use client"

import { useState, useEffect } from "react"
import { Wifi, WifiOff, Loader2 } from "lucide-react"

type BrokerStatus = "disconnected" | "connecting" | "connected" | "error"

export function BrokerConnectionBadge() {
  const [status, setStatus] = useState<BrokerStatus>("disconnected")
  const [label, setLabel] = useState("")
  const apiBase = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"

  useEffect(() => {
    let mounted = true
    const check = async () => {
      try {
        const res = await fetch(`${apiBase}/api/kite/auth-status`)
        if (!mounted) return
        if (res.ok) {
          const data = await res.json()
          if (data.authenticated) {
            const statusRes = await fetch(`${apiBase}/api/kite/status`)
            if (!mounted) return
            if (statusRes.ok) {
              const statusData = await statusRes.json()
              if (statusData.connected) {
                setStatus("connected")
                setLabel("Zerodha Live")
              } else {
                setStatus("disconnected")
                setLabel("Zerodha Auth")
              }
            } else {
              setStatus("disconnected")
              setLabel(data.user_id || "Zerodha")
            }
          } else {
            setStatus("disconnected")
            setLabel("")
          }
        } else {
          setStatus("disconnected")
          setLabel("")
        }
      } catch {
        if (!mounted) return
        setStatus("disconnected")
        setLabel("")
      }
    }
    check()
    const interval = setInterval(check, 15000)
    return () => {
      mounted = false
      clearInterval(interval)
    }
  }, [apiBase])

  if (status === "disconnected" && !label) return null

  const statusColors = {
    disconnected: "bg-muted-foreground/20 text-muted-foreground border-muted-foreground/20",
    connecting: "bg-amber-500/10 text-amber-500 border-amber-500/20",
    connected: "bg-emerald-500/10 text-emerald-500 border-emerald-500/20",
    error: "bg-red-500/10 text-red-500 border-red-500/20",
  }

  const StatusIcon = status === "connected" ? Wifi : status === "connecting" ? Loader2 : WifiOff

  return (
    <div className={`hidden lg:flex items-center gap-1 rounded-md border px-2 py-1 ${statusColors[status]}`}>
      <StatusIcon className={`w-3 h-3 ${status === "connecting" ? "animate-spin" : ""}`} />
      <span className="text-[9px] font-medium whitespace-nowrap">{label}</span>
    </div>
  )
}
