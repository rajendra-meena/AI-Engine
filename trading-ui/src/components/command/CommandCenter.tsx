"use client"

import { useState, useMemo } from "react"
import { useRealtimeStore } from "@/store/useRealtimeStore"
import { useQuery } from "@tanstack/react-query"
import { decisionService } from "@/services/decisionService"
import { predictionService } from "@/services/predictionService"
import { aiOrchestratorService } from "@/services/aiOrchestratorService"
import { AIHealthCard } from "./AIHealthCard"
import { Shield, Activity, Cpu, Network, BrainCircuit, BarChart3, Target, Search, LayoutDashboard } from "lucide-react"
import { cn } from "@/lib/utils"

const TABS = [
  { id: "overview", label: "Overview", icon: <LayoutDashboard className="w-3.5 h-3.5" /> },
  { id: "autonomous", label: "Auto Mode", icon: <BrainCircuit className="w-3.5 h-3.5" /> },
  { id: "opportunities", label: "Opportunities", icon: <Target className="w-3.5 h-3.5" /> },
  { id: "allocation", label: "Allocation", icon: <BarChart3 className="w-3.5 h-3.5" /> },
  { id: "models", label: "AI Models", icon: <Cpu className="w-3.5 h-3.5" /> },
  { id: "learning", label: "Self-Learning", icon: <Activity className="w-3.5 h-3.5" /> },
  { id: "risk", label: "Risk Center", icon: <Shield className="w-3.5 h-3.5" /> },
  { id: "monitoring", label: "Monitoring", icon: <Network className="w-3.5 h-3.5" /> },
  { id: "audit", label: "Audit", icon: <Search className="w-3.5 h-3.5" /> },
]

export function CommandCenter() {
  const [activeTab, setActiveTab] = useState("overview")
  const connection = useRealtimeStore((s) => s.connection)

  const { data: decision } = useQuery({ queryKey: ["cmd-decision"], queryFn: () => decisionService.getLatest("NIFTY 50"), refetchInterval: 30_000, staleTime: 10_000, retry: 2 })
  const { data: stats } = useQuery({ queryKey: ["cmd-stats"], queryFn: () => predictionService.getStats("NIFTY 50"), refetchInterval: 60_000, staleTime: 30_000, retry: 2 })
  const { data: aiHealth } = useQuery({ queryKey: ["cmd-ai-health"], queryFn: () => aiOrchestratorService.getHealth(), refetchInterval: 30_000, staleTime: 10_000, retry: 1 })

  const systemHealth = useMemo(() => ({
    websocket: connection.state === "connected" ? "healthy" as const : connection.state === "reconnecting" ? "degraded" as const : "down" as const,
    broker: "healthy" as const,
    database: "healthy" as const,
    ai: decision ? "healthy" as const : "degraded" as const,
  }), [connection.state, decision])

  const score = decision?.score ?? 0
  const confidence = decision?.confidence ?? 0
  const riskLevel = decision?.risk_level ?? "MEDIUM"

  const overviewContent = useMemo(() => {
    const provHealth = aiHealth?.providers ?? {}
    return (
    <div className="space-y-3">
      <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-2">
        {Object.entries(systemHealth).map(([key, val]) => (
          <AIHealthCard key={key} label={key} value={val === "healthy" ? "Online" : val === "degraded" ? "Degraded" : "Offline"} status={val} />
        ))}
        <AIHealthCard label="AI Score" value={score} status={score >= 60 ? "healthy" : score >= 40 ? "warning" : "down"} detail={`Conf: ${confidence}%`} />
        <AIHealthCard label="Risk Level" value={riskLevel} status={riskLevel === "LOW" ? "healthy" : riskLevel === "MEDIUM" ? "warning" : "down"} />
      </div>

      <div className="grid grid-cols-2 sm:grid-cols-4 gap-2">
        <AIHealthCard label="Latency" value={`${connection.latency}ms`} status={connection.latency < 100 ? "healthy" : connection.latency < 300 ? "degraded" : "down"} />
        <AIHealthCard label="Uptime" value={connection.state === "connected" ? "Live" : "Offline"} status={connection.state === "connected" ? "healthy" : "down"} />
        <AIHealthCard label="Decision Accuracy" value={stats?.hit_rate ? `${(stats.hit_rate * 100).toFixed(1)}%` : "N/A"} status={stats?.hit_rate && stats.hit_rate > 0.5 ? "healthy" : "warning"} />
        <AIHealthCard label="Total Predictions" value={stats?.total_predictions ?? 0} status="healthy" detail={`${stats?.total_checked ?? 0} checked`} />
      </div>

      <div className="rounded-lg border bg-card p-3">
        <div className="text-[9px] font-medium text-muted-foreground uppercase tracking-wider mb-2">Provider Status</div>
        <div className="grid grid-cols-3 sm:grid-cols-5 gap-1.5">
          {Object.entries(provHealth).length > 0 ? Object.entries(provHealth).map(([name, health]) => (
            <div key={name} className="flex items-center gap-1.5 rounded bg-muted/20 px-2 py-1">
              <span className={cn("w-1.5 h-1.5 rounded-full", health ? "bg-emerald-500" : "bg-red-500")} />
              <span className="text-[9px] capitalize">{name}</span>
            </div>
          )) : (
            <span className="text-[9px] text-muted-foreground col-span-full">No provider data</span>
          )}
        </div>
      </div>
    </div>
  )}, [systemHealth, score, confidence, riskLevel, connection.latency, connection.state, stats, aiHealth])

  const opportunitiesContent = useMemo(() => (
    <div className="rounded-lg border bg-card p-4 text-center text-[10px] text-muted-foreground">
      Live opportunity feed will display real-time AI-screened trades sorted by score and confidence.
    </div>
  ), [])

  return (
    <div className="space-y-3">
      <div className="flex items-center gap-2">
        <BrainCircuit className="w-4 h-4 text-primary" />
        <h2 className="text-sm font-bold">AI Command Center</h2>
      </div>

      <div className="flex items-center gap-1 border-b overflow-x-auto">
        {TABS.map((tab) => (
          <button key={tab.id} onClick={() => setActiveTab(tab.id)}
            className={cn("flex items-center gap-1 px-3 py-1.5 text-[9px] font-medium transition-colors border-b-2 -mb-px whitespace-nowrap", activeTab === tab.id ? "text-primary border-primary" : "text-muted-foreground hover:text-foreground border-transparent")}>
            {tab.icon} {tab.label}
          </button>
        ))}
      </div>

      {activeTab === "overview" && overviewContent}
      {activeTab === "opportunities" && opportunitiesContent}
      {activeTab === "risk" && (
        <div className="space-y-2">
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-2">
            <AIHealthCard label="Max DD" value="0%" status="healthy" />
            <AIHealthCard label="Daily Loss" value="₹0" status="healthy" />
            <AIHealthCard label="Exposure" value="0%" status="healthy" />
            <AIHealthCard label="Margin" value="100%" status="healthy" />
          </div>
          <div className="flex flex-wrap gap-2">
            {["Pause AI", "Close All", "Disable Broker", "Switch Paper", "Stop Trading"].map((action) => (
              <button key={action} className="rounded-md border border-red-500/30 bg-red-500/10 px-3 py-1.5 text-[9px] font-medium text-red-500 hover:bg-red-500/20 transition-colors">{action}</button>
            ))}
          </div>
        </div>
      )}
      {activeTab !== "overview" && activeTab !== "opportunities" && activeTab !== "risk" && (
        <div className="rounded-lg border bg-card p-6 text-center text-[10px] text-muted-foreground">{TABS.find((t) => t.id === activeTab)?.label} dashboard coming soon.</div>
      )}
    </div>
  )
}
