"use client"

import { useState, useEffect, useCallback } from "react"
import { SettingsSection } from "./SettingsSection"
import { Wifi, WifiOff, RefreshCw, LogIn, LogOut, ExternalLink, Plug, PlugZap } from "lucide-react"

interface BrokerState {
  authenticated: boolean
  connected: boolean
  configured: boolean
  user_id: string
  user_name: string
  broker: string
  exchange: string
  instruments_loaded: boolean
  instruments_count: number
  websocket: {
    connected: boolean
    ticks_received: number
    subscribed_tokens: number
    reconnect_attempts: number
  }
  login_url: string
}

type ConnectionStatus = "disconnected" | "connecting" | "connected" | "error"

export function BrokerSettingsPanel() {
  const [state, setState] = useState<BrokerState>({
    authenticated: false, connected: false, configured: false,
    user_id: "", user_name: "", broker: "ZERODHA", exchange: "NSE",
    instruments_loaded: false, instruments_count: 0,
    websocket: { connected: false, ticks_received: 0, subscribed_tokens: 0, reconnect_attempts: 0 },
    login_url: "",
  })
  const [status, setStatus] = useState<ConnectionStatus>("disconnected")
  const [error, setError] = useState<string | null>(null)
  const [requestToken, setRequestToken] = useState("")

  const apiBase = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"

  const fetchStatus = useCallback(async () => {
    try {
      const res = await fetch(`${apiBase}/api/kite/auth-status`)
      if (res.ok) {
        const data = await res.json()
        setState((s) => ({ ...s, ...data }))
        if (data.authenticated) setStatus("connected")
      }
    } catch {
      // Server not available
    }

    try {
      const res = await fetch(`${apiBase}/api/kite/status`)
      if (res.ok) {
        const data = await res.json()
        setState((s) => ({ ...s, ...data }))
        if (data.connected) {
          setStatus("connected")
          if (data.websocket) {
            setState((s) => ({ ...s, websocket: data.websocket }))
          }
        }
      }
    } catch {
      // ignore
    }
  }, [apiBase])

  useEffect(() => {
    const id = setTimeout(() => fetchStatus(), 0)
    const interval = setInterval(fetchStatus, 10000)
    return () => {
      clearTimeout(id)
      clearInterval(interval)
    }
  }, [fetchStatus])

  const handleGetLoginUrl = async () => {
    try {
      setStatus("connecting")
      setError(null)
      const res = await fetch(`${apiBase}/api/kite/login-url`)
      if (res.ok) {
        const data = await res.json()
        if (data.success) {
          setState((s) => ({ ...s, login_url: data.login_url }))
          window.open(data.login_url, "_blank", "noopener,noreferrer")
        } else {
          setError(data.detail || "Failed to generate login URL")
        }
      } else {
        const err = await res.json().catch(() => ({ detail: `HTTP ${res.status}` }))
        setError(err.detail || "Failed to generate login URL")
      }
    } catch {
      setError("Connection failed")
    } finally {
      setStatus("disconnected")
    }
  }

  const handleSubmitToken = async () => {
    if (!requestToken.trim()) return
    try {
      setStatus("connecting")
      setError(null)
      const res = await fetch(`${apiBase}/api/kite/session?request_token=${encodeURIComponent(requestToken.trim())}`, {
        method: "POST",
      })
      if (res.ok) {
        const data = await res.json()
        if (data.success) {
          setStatus("connected")
          setRequestToken("")
          await handleConnect()
        } else {
          setError("Authentication failed")
          setStatus("error")
        }
      } else {
        const err = await res.json()
        setError(err.detail || "Authentication failed")
        setStatus("error")
      }
    } catch {
      setError("Connection error")
      setStatus("error")
    }
  }

  const handleConnect = async () => {
    try {
      setStatus("connecting")
      setError(null)
      const res = await fetch(`${apiBase}/api/kite/connect`, { method: "POST" })
      if (res.ok) {
        setStatus("connected")
        await fetchStatus()
        await fetch(`${apiBase}/api/kite/ws/start`, { method: "POST" })
      } else {
        const err = await res.json()
        setError(err.detail || "Connection failed")
        setStatus("error")
      }
    } catch {
      setError("Connection error")
      setStatus("error")
    }
  }

  const handleDisconnect = async () => {
    try {
      await fetch(`${apiBase}/api/kite/ws/stop`, { method: "POST" })
      await fetch(`${apiBase}/api/kite/disconnect`, { method: "POST" })
      setStatus("disconnected")
      setError(null)
    } catch {
      // ignore
    }
  }

  const handleLogout = async () => {
    try {
      await handleDisconnect()
      await fetch(`${apiBase}/api/kite/logout`, { method: "POST" })
      setState((s) => ({ ...s, authenticated: false, connected: false, user_id: "" }))
      setStatus("disconnected")
    } catch {
      // ignore
    }
  }

  const statusColor = status === "connected" ? "text-emerald-500" : status === "connecting" ? "text-amber-500" : status === "error" ? "text-red-500" : "text-muted-foreground"
  const StatusIcon = status === "connected" ? Wifi : status === "connecting" ? RefreshCw : WifiOff

  return (
    <div className="space-y-6">
      {/* Connection Status */}
      <SettingsSection title="Connection">
        <div className="space-y-3">
          <div className="flex items-center justify-between p-3 rounded-lg border bg-muted/20">
            <div className="flex items-center gap-2">
              <StatusIcon className={`w-4 h-4 ${statusColor} ${status === "connecting" ? "animate-spin" : ""}`} />
              <div>
                <div className="text-xs font-medium capitalize">{status}</div>
                <div className="text-[10px] text-muted-foreground">
                  {state.broker} · {state.exchange}
                </div>
              </div>
            </div>
            <div className="flex gap-1">
              {status === "connected" ? (
                <>
                  <button onClick={handleDisconnect} className="flex items-center gap-1 px-2 py-1 rounded text-[10px] font-medium bg-amber-500/10 text-amber-600 hover:bg-amber-500/20 transition-colors">
                    <PlugZap className="w-3 h-3" /> Disconnect
                  </button>
                  <button onClick={handleLogout} className="flex items-center gap-1 px-2 py-1 rounded text-[10px] font-medium bg-red-500/10 text-red-600 hover:bg-red-500/20 transition-colors">
                    <LogOut className="w-3 h-3" /> Logout
                  </button>
                </>
              ) : (
                <button onClick={handleConnect} className="flex items-center gap-1 px-2 py-1 rounded text-[10px] font-medium bg-emerald-500/10 text-emerald-600 hover:bg-emerald-500/20 transition-colors" disabled={!state.authenticated}>
                  <Plug className="w-3 h-3" /> Connect
                </button>
              )}
            </div>
          </div>

          {error && (
            <div className="p-2 rounded text-[10px] bg-red-500/10 text-red-600 border border-red-500/20">
              {error}
            </div>
          )}

          {status === "connected" && (
            <div className="grid grid-cols-3 gap-2">
              <div className="rounded-md bg-muted/20 p-2 text-center">
                <div className="text-[18px] font-bold font-mono">{state.websocket?.ticks_received || 0}</div>
                <div className="text-[9px] text-muted-foreground">Ticks</div>
              </div>
              <div className="rounded-md bg-muted/20 p-2 text-center">
                <div className="text-[18px] font-bold font-mono">{state.websocket?.subscribed_tokens || 0}</div>
                <div className="text-[9px] text-muted-foreground">Subscriptions</div>
              </div>
              <div className="rounded-md bg-muted/20 p-2 text-center">
                <div className="text-[18px] font-bold font-mono">{state.websocket?.reconnect_attempts || 0}</div>
                <div className="text-[9px] text-muted-foreground">Reconnects</div>
              </div>
            </div>
          )}
        </div>
      </SettingsSection>

      {/* Authentication */}
      <SettingsSection title="Authentication">
        <div className="space-y-3">
          <div className="flex items-center justify-between">
            <div className="text-xs text-muted-foreground">Step 1: Get login URL</div>
            <button
              onClick={handleGetLoginUrl}
              className="flex items-center gap-1 px-3 py-1.5 rounded text-[10px] font-medium bg-primary/10 text-primary hover:bg-primary/20 transition-colors"
            >
              <ExternalLink className="w-3 h-3" /> Get Login URL
            </button>
          </div>

          <div>
            <div className="text-xs text-muted-foreground mb-1">Step 2: Enter request token from redirect URL</div>
            <div className="flex gap-2">
              <input
                type="text"
                value={requestToken}
                onChange={(e) => setRequestToken(e.target.value)}
                placeholder="Enter request_token from URL..."
                className="flex-1 h-8 rounded border bg-muted/30 px-2 text-[11px] font-mono focus:outline-none focus:ring-1 focus:ring-primary"
              />
              <button
                onClick={handleSubmitToken}
                disabled={!requestToken.trim()}
                className="flex items-center gap-1 px-3 py-1.5 rounded text-[10px] font-medium bg-primary text-primary-foreground hover:bg-primary/90 transition-colors disabled:opacity-50"
              >
                <LogIn className="w-3 h-3" /> Authenticate
              </button>
            </div>
          </div>

          <div className="flex items-center gap-2 text-[10px]">
            <div className={`w-2 h-2 rounded-full ${state.authenticated ? "bg-emerald-500" : "bg-muted-foreground/30"}`} />
            <span className="text-muted-foreground">
              {state.authenticated ? `Authenticated as ${state.user_name || state.user_id}` : "Not authenticated"}
            </span>
          </div>
        </div>
      </SettingsSection>

      {/* Instruments */}
      <SettingsSection title="Instruments">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <div className={`w-2 h-2 rounded-full ${state.instruments_loaded ? "bg-emerald-500" : "bg-muted-foreground/30"}`} />
            <span className="text-xs text-muted-foreground">
              {state.instruments_loaded ? `${state.instruments_count} instruments loaded` : "Not loaded"}
            </span>
          </div>
          <button onClick={fetchStatus} className="flex items-center gap-1 px-2 py-1 rounded text-[10px] font-medium text-muted-foreground hover:bg-accent transition-colors">
            <RefreshCw className="w-3 h-3" /> Refresh
          </button>
        </div>
      </SettingsSection>

      {/* Account */}
      <SettingsSection title="Account">
        <div className="space-y-2 text-xs">
          <div className="flex justify-between">
            <span className="text-muted-foreground">Broker</span>
            <span className="font-medium">{state.broker}</span>
          </div>
          <div className="flex justify-between">
            <span className="text-muted-foreground">Exchange</span>
            <span className="font-medium">{state.exchange}</span>
          </div>
          <div className="flex justify-between">
            <span className="text-muted-foreground">User ID</span>
            <span className="font-medium font-mono">{state.user_id || "—"}</span>
          </div>
          <div className="flex justify-between">
            <span className="text-muted-foreground">Name</span>
            <span className="font-medium">{state.user_name || "—"}</span>
          </div>
        </div>
      </SettingsSection>

      {/* Actions */}
      <div className="flex gap-2 pt-2">
        <button onClick={fetchStatus} className="flex items-center gap-1 px-3 py-1.5 rounded text-[10px] font-medium text-muted-foreground hover:bg-accent transition-colors border">
          <RefreshCw className="w-3 h-3" /> Refresh Status
        </button>
      </div>
    </div>
  )
}
