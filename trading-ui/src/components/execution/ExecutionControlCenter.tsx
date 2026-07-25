"use client"

import { useState, useEffect, useCallback } from "react"
import {
  Shield, Activity, AlertTriangle, CheckCircle, XCircle, BarChart3,
  RefreshCw, Lock, Unlock, Play, Zap,
} from "lucide-react"
import { executionService } from "@/services/executionService"
import { useBrokerStore } from "@/store/useBrokerStore"

type TabId = "overview" | "mode" | "arming" | "history"

export function ExecutionControlCenter() {
  const [activeTab, setActiveTab] = useState<TabId>("overview")
  const [status, setStatus] = useState<any>(null)
  const [mode, setMode] = useState<string>("disabled")
  const [arming, setArming] = useState<any>(null)
  const [history, setHistory] = useState<any[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const brokerConnected = useBrokerStore((s) => s.connected)

  const fetchAll = useCallback(async () => {
    setError(null)
    try {
      const [s, m, a, h] = await Promise.all([
        executionService.getStatus().catch(() => null),
        executionService.getMode().catch(() => null),
        executionService.getArmingStatus().catch(() => null),
        executionService.getHistory().catch(() => null),
      ])
      if (s) setStatus(s)
      if (m) setMode(m.mode)
      if (a) setArming(a)
      if (h) setHistory(h.executions || [])
    } catch { setError("Failed to load") }
    setLoading(false)
  }, [])

  useEffect(() => {
    fetchAll()
    const interval = setInterval(fetchAll, 10000)
    return () => clearInterval(interval)
  }, [fetchAll])

  const handleSetMode = async (newMode: string) => {
    await executionService.setMode(newMode)
    await fetchAll()
  }

  const handleArmLive = async () => {
    await executionService.armLive()
    await fetchAll()
  }

  const handleDisarmLive = async () => {
    await executionService.disarmLive()
    await fetchAll()
  }

  const tabs = [
    { id: "overview" as TabId, label: "Overview", icon: <Activity className="w-3.5 h-3.5" /> },
    { id: "mode" as TabId, label: "Execution Mode", icon: <Shield className="w-3.5 h-3.5" /> },
    { id: "arming" as TabId, label: "Live Arming", icon: <Lock className="w-3.5 h-3.5" /> },
    { id: "history" as TabId, label: "History", icon: <BarChart3 className="w-3.5 h-3.5" /> },
  ]

  const modeColor = mode === "live" ? "text-red-500" : mode === "paper" ? "text-amber-500" : "text-muted-foreground"

  return (
    <div className="space-y-4">
      <div className="flex items-center gap-2">
        <Shield className="w-5 h-5 text-primary" />
        <h1 className="text-lg font-bold">Execution Gateway</h1>
        <button onClick={fetchAll} className="ml-auto p-1 rounded text-muted-foreground hover:text-foreground hover:bg-accent" disabled={loading}>
          <RefreshCw className={`w-3.5 h-3.5 ${loading ? "animate-spin" : ""}`} />
        </button>
      </div>

      <div className="flex items-center gap-2 p-2 rounded-lg border bg-card text-[10px]">
        <span className={`font-bold uppercase ${modeColor}`}>{mode}</span>
        {mode === "live" && <span className={`${arming?.live_armed ? "text-emerald-500" : "text-red-500"}`}>{arming?.live_armed ? "ARMED" : "NOT ARMED"}</span>}
        <span className="text-muted-foreground">|</span>
        <span>Broker: {brokerConnected ? "Connected" : "Disconnected"}</span>
        <span className="text-muted-foreground">|</span>
        <span>Executions: {status?.total_executions || 0}</span>
      </div>

      {error && <div className="rounded border border-red-500/20 bg-red-500/5 p-2 text-[10px] text-red-600">{error}</div>}

      <div className="flex gap-1 border-b overflow-x-auto">
        {tabs.map(tab => (
          <button key={tab.id} onClick={() => setActiveTab(tab.id)}
            className={`flex items-center gap-1 px-3 py-1.5 text-[10px] font-medium border-b-2 transition-colors shrink-0 ${
              activeTab === tab.id ? "border-primary text-foreground" : "border-transparent text-muted-foreground hover:text-foreground"
            }`}>
            {tab.icon} {tab.label}
          </button>
        ))}
      </div>

      {activeTab === "overview" && (
        <div className="space-y-4">
          <div className="grid grid-cols-4 gap-3">
            <MetricCard label="Execution Mode" value={mode.toUpperCase()} color={modeColor} />
            <MetricCard label="Live Armed" value={arming?.live_armed ? "YES" : "NO"} color={arming?.live_armed ? "text-emerald-500" : "text-muted-foreground"} />
            <MetricCard label="Total Executions" value={String(status?.total_executions || 0)} />
            <MetricCard label="Broker" value={brokerConnected ? "Connected" : "Disconnected"} color={brokerConnected ? "text-emerald-500" : "text-red-500"} />
          </div>
          <div className="rounded-lg border p-4">
            <h3 className="text-xs font-bold mb-3 flex items-center gap-2"><Shield className="w-3.5 h-3.5" /> Safety Status</h3>
            <div className="grid grid-cols-2 gap-2 text-[10px]">
              <CheckItem label="Risk Firewall" active />
              <CheckItem label="Idempotency" active />
              <CheckItem label="Trade Geometry" active />
              <CheckItem label="Execution Mode" active />
              <CheckItem label="Live Arming Required" active={mode !== "live" || !!arming?.live_armed} />
              <CheckItem label="Broker Connection" active={brokerConnected} />
            </div>
          </div>
        </div>
      )}

      {activeTab === "mode" && (
        <div className="space-y-4">
          <div className="grid grid-cols-3 gap-3">
            <ModeCard title="DISABLED" desc="No execution permitted" active={mode === "disabled"} color="bg-muted/30 text-muted-foreground"
              onClick={() => handleSetMode("disabled")} />
            <ModeCard title="PAPER" desc="Simulated execution using real market data" active={mode === "paper"} color="bg-amber-500/10 text-amber-600 border-amber-500/20"
              onClick={() => handleSetMode("paper")} />
            <ModeCard title="LIVE" desc="Real broker execution" active={mode === "live"} color="bg-red-500/10 text-red-600 border-red-500/20"
              onClick={() => handleSetMode("live")} />
          </div>
          <div className="rounded-lg border border-amber-500/20 bg-amber-500/5 p-3 text-[10px] text-amber-600">
            <strong>Safety:</strong> LIVE mode requires explicit arming via the Live Arming tab. A short-lived confirmation token is required for each execution.
          </div>
        </div>
      )}

      {activeTab === "arming" && (
        <div className="space-y-4">
          <div className="grid grid-cols-2 gap-3">
            <div className="rounded-lg border bg-card p-4 text-center">
              <div className="text-2xl font-bold mb-1">{arming?.live_armed ? "ARMED" : "DISARMED"}</div>
              <div className="text-[10px] text-muted-foreground mb-3">
                {arming?.live_armed ? `Token expires: ${arming.token_expires_at?.split("T")[1]?.slice(0, 8) || ""}` : "LIVE execution not armed"}
              </div>
              {!arming?.live_armed ? (
                <button onClick={handleArmLive}
                  className="px-4 py-2 rounded text-xs font-medium bg-red-500/10 text-red-600 hover:bg-red-500/20 border border-red-500/20">
                  <Unlock className="w-4 h-4 inline mr-1" /> Arm LIVE
                </button>
              ) : (
                <button onClick={handleDisarmLive}
                  className="px-4 py-2 rounded text-xs font-medium bg-emerald-500/10 text-emerald-600 hover:bg-emerald-500/20 border border-emerald-500/20">
                  <Lock className="w-4 h-4 inline mr-1" /> Disarm
                </button>
              )}
            </div>
            <div className="rounded-lg border bg-card p-4">
              <h3 className="text-xs font-bold mb-2">Safety Requirements for LIVE</h3>
              <div className="space-y-1 text-[10px]">
                <CheckItem label="Mode set to LIVE" active={mode === "live"} />
                <CheckItem label="Live arming token generated" active={!!arming?.live_armed} />
                <CheckItem label="Risk Firewall enabled" active />
                <CheckItem label="Broker connected" active={brokerConnected} />
                <CheckItem label="Emergency stop inactive" active />
              </div>
            </div>
          </div>
        </div>
      )}

      {activeTab === "history" && (
        <div className="space-y-3">
          {history.length === 0 ? (
            <div className="p-8 text-center text-[10px] text-muted-foreground">No executions yet</div>
          ) : (
            <div className="border rounded-lg overflow-hidden">
              <table className="w-full text-[10px]">
                <thead><tr className="bg-muted/30 border-b">
                  <th className="text-left px-3 py-2">Symbol</th>
                  <th className="text-left px-3 py-2">Side</th>
                  <th className="text-right px-3 py-2">Qty</th>
                  <th className="text-left px-3 py-2">Mode</th>
                  <th className="text-left px-3 py-2">Status</th>
                  <th className="text-left px-3 py-2">Reason</th>
                  <th className="text-left px-3 py-2">Broker ID</th>
                </tr></thead>
                <tbody className="divide-y">
                  {history.map((e: any, i: number) => (
                    <tr key={e.execution_id || i} className="hover:bg-muted/20">
                      <td className="px-3 py-1.5 font-medium">{e.symbol}</td>
                      <td className={`px-3 py-1.5 ${e.side === "BUY" ? "text-emerald-500" : "text-red-500"}`}>{e.side}</td>
                      <td className="px-3 py-1.5 text-right font-mono">{e.quantity}</td>
                      <td className="px-3 py-1.5 uppercase">{e.execution_mode}</td>
                      <td className="px-3 py-1.5">
                        <span className={`px-1.5 py-0.5 rounded text-[8px] font-medium ${
                          e.status === "filled" ? "bg-emerald-500/10 text-emerald-500" :
                          e.status === "blocked" || e.status === "rejected" ? "bg-red-500/10 text-red-500" :
                          "bg-amber-500/10 text-amber-500"
                        }`}>{e.status}</span>
                      </td>
                      <td className="px-3 py-1.5 text-muted-foreground max-w-[150px] truncate">{e.rejection_reason || "—"}</td>
                      <td className="px-3 py-1.5 font-mono text-[9px] text-muted-foreground">{e.broker_order_id || "—"}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      )}
    </div>
  )
}

function MetricCard({ label, value, color }: { label: string; value: string; color?: string }) {
  return <div className="rounded-lg border bg-card p-3">
    <div className="text-[9px] text-muted-foreground uppercase tracking-wider">{label}</div>
    <div className={`text-lg font-bold font-mono mt-0.5 ${color || ""}`}>{value}</div>
  </div>
}

function CheckItem({ label, active }: { label: string; active: boolean }) {
  return <div className="flex items-center gap-1.5">
    {active ? <CheckCircle className="w-3 h-3 text-emerald-500" /> : <XCircle className="w-3 h-3 text-red-500" />}
    <span>{label}</span>
  </div>
}

function ModeCard({ title, desc, active, color, onClick }: { title: string; desc: string; active: boolean; color: string; onClick: () => void }) {
  return (
    <button onClick={onClick} className={`rounded-lg border p-4 text-left transition-colors ${active ? color + " ring-2 ring-primary/30" : "bg-card hover:bg-muted/20"}`}>
      <div className="text-sm font-bold">{title}</div>
      <div className="text-[9px] text-muted-foreground mt-1">{desc}</div>
    </button>
  )
}
