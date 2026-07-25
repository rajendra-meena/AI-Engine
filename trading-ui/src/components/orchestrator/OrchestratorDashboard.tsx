"use client"

import { useState, useEffect, useCallback } from "react"
import {
  Activity, AlertTriangle, BarChart3, Brain, CheckCircle, Cpu,
  RefreshCw, Shield, TrendingUp, XCircle, Play, Zap, FileText,
} from "lucide-react"
import { orchestratorService } from "@/services/orchestratorService"

type TabId = "pipeline" | "traces" | "history"

interface StageBadge {
  label: string
  status: string
}

function StageIcon({ status }: { status: string }) {
  switch (status) {
    case "passed": return <CheckCircle className="w-3.5 h-3.5 text-emerald-500" />
    case "blocked": return <XCircle className="w-3.5 h-3.5 text-red-500" />
    case "skipped": return <AlertTriangle className="w-3.5 h-3.5 text-amber-500" />
    case "failed": return <XCircle className="w-3.5 h-3.5 text-red-500" />
    default: return <Activity className="w-3.5 h-3.5 text-muted-foreground" />
  }
}

export function OrchestratorDashboard() {
  const [activeTab, setActiveTab] = useState<TabId>("pipeline")
  const [status, setStatus] = useState<any>(null)
  const [lastDecision, setLastDecision] = useState<any>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [symbol, setSymbol] = useState("NIFTY 50")
  const [execMode, setExecMode] = useState("paper")
  const [traceId, setTraceId] = useState("")
  const [traceData, setTraceData] = useState<any>(null)

  const fetchStatus = useCallback(async () => {
    try {
      const s = await orchestratorService.getStatus()
      setStatus(s)
    } catch { /* ignore */ }
    try {
      const d = await orchestratorService.getLastDecision()
      setLastDecision(d?.decision || null)
    } catch { /* ignore */ }
    setLoading(false)
  }, [])

  useEffect(() => {
    fetchStatus()
    const interval = setInterval(fetchStatus, 10000)
    return () => clearInterval(interval)
  }, [fetchStatus])

  const handleAnalyze = async () => {
    setError(null)
    setLoading(true)
    try {
      const result = await orchestratorService.analyze({
        symbol, execution_mode: execMode, interval: "15m",
      })
      setLastDecision({ decision: result })
      setLoading(false)
    } catch (e) {
      setError("Analysis failed")
      setLoading(false)
    }
  }

  const handleTraceLookup = async () => {
    if (!traceId.trim()) return
    setError(null)
    try {
      const data = await orchestratorService.getTrace(traceId.trim())
      setTraceData(data)
    } catch {
      setError("Trace not found")
      setTraceData(null)
    }
  }

  const decision = lastDecision?.decision || null
  const stages = decision?.stages || {}
  const PIPELINE_STAGES = ["market_data", "context", "ai_decision", "ml_prediction", "strategy", "trade_planner", "risk_firewall", "execution", "portfolio", "learning"]

  const tabs = [
    { id: "pipeline" as TabId, label: "Pipeline", icon: <Activity className="w-3.5 h-3.5" /> },
    { id: "traces" as TabId, label: "Trace Lookup", icon: <FileText className="w-3.5 h-3.5" /> },
    { id: "history" as TabId, label: "History", icon: <BarChart3 className="w-3.5 h-3.5" /> },
  ]

  return (
    <div className="space-y-4">
      <div className="flex items-center gap-2">
        <Cpu className="w-5 h-5 text-primary" />
        <h1 className="text-lg font-bold">Trading Orchestrator</h1>
        <button onClick={fetchStatus} className="ml-auto p-1 rounded text-muted-foreground hover:text-foreground hover:bg-accent">
          <RefreshCw className={`w-3.5 h-3.5 ${loading ? "animate-spin" : ""}`} />
        </button>
      </div>

      {error && (
        <div className="rounded-lg border border-red-500/20 bg-red-500/5 p-3 text-[10px] text-red-600">
          {error}
        </div>
      )}

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

      <div className="min-h-[400px]">
        {activeTab === "pipeline" && (
          <div className="space-y-4">
            {/* Controls */}
            <div className="flex items-center gap-3 p-3 rounded-lg border bg-card">
              <div>
                <label className="text-[9px] text-muted-foreground block mb-0.5">Symbol</label>
                <select value={symbol} onChange={e => setSymbol(e.target.value)}
                  className="h-7 rounded border bg-muted/30 px-2 text-[10px] font-medium">
                  <option value="NIFTY 50">NIFTY 50</option>
                  <option value="BANKNIFTY">BANKNIFTY</option>
                  <option value="SENSEX">SENSEX</option>
                </select>
              </div>
              <div>
                <label className="text-[9px] text-muted-foreground block mb-0.5">Mode</label>
                <select value={execMode} onChange={e => setExecMode(e.target.value)}
                  className="h-7 rounded border bg-muted/30 px-2 text-[10px] font-medium">
                  <option value="paper">Paper</option>
                  <option value="manual">Manual</option>
                  <option value="semi_auto">Semi-Auto</option>
                </select>
              </div>
              <button onClick={handleAnalyze} disabled={loading}
                className="flex items-center gap-1 px-3 py-1.5 rounded text-[10px] font-medium bg-primary text-primary-foreground hover:bg-primary/90 mt-4">
                <Play className="w-3 h-3" /> Run Pipeline
              </button>
            </div>

            {/* Pipeline Visual */}
            <div className="rounded-lg border bg-card">
              <div className="px-3 py-2 border-b bg-muted/20 text-[10px] font-medium text-muted-foreground uppercase tracking-wider">Pipeline Status</div>
              <div className="p-3">
                <div className="grid grid-cols-5 gap-2 mb-4">
                  {PIPELINE_STAGES.map(stage => {
                    const s = stages[stage]?.status || "waiting"
                    return (
                      <div key={stage} className={`flex flex-col items-center gap-1 p-2 rounded-lg border text-center ${
                        s === "passed" ? "bg-emerald-500/5 border-emerald-500/20" :
                        s === "blocked" ? "bg-red-500/5 border-red-500/20" :
                        s === "skipped" ? "bg-amber-500/5 border-amber-500/20" :
                        s === "failed" ? "bg-red-500/5 border-red-500/20" :
                        "bg-muted/10 border-muted/20"
                      }`}>
                        <StageIcon status={s} />
                        <span className="text-[8px] font-medium uppercase leading-tight">{stage.replace(/_/g, " ")}</span>
                        <span className={`text-[7px] font-mono ${
                          s === "passed" ? "text-emerald-500" :
                          s === "blocked" ? "text-red-500" :
                          s === "skipped" ? "text-amber-500" :
                          "text-muted-foreground/50"
                        }`}>{s}</span>
                      </div>
                    )
                  })}
                </div>

                {stages.risk_firewall && stages.risk_firewall.status === "blocked" && (
                  <div className="rounded-lg border border-red-500/20 bg-red-500/5 p-3 mb-4">
                    <div className="flex items-center gap-2 text-xs font-bold text-red-600 mb-1">
                      <Shield className="w-4 h-4" /> TRADE BLOCKED BY RISK FIREWALL
                    </div>
                    <p className="text-[10px] text-red-600/80">{stages.risk_firewall.blocked_reason || "Risk check failed"}</p>
                  </div>
                )}

                {decision?.risk_status === "approved" && (
                  <div className="rounded-lg border border-emerald-500/20 bg-emerald-500/5 p-3 mb-4">
                    <div className="flex items-center gap-2 text-xs font-bold text-emerald-600 mb-1">
                      <CheckCircle className="w-4 h-4" /> RISK FIREWALL APPROVED
                    </div>
                    <p className="text-[10px] text-emerald-600/80">
                      Risk score: {decision.risk_score} | Grade: {decision.risk_grade}
                    </p>
                  </div>
                )}
              </div>
            </div>

            {/* Decision Summary */}
            {decision && (
              <div className="grid grid-cols-4 gap-3">
                <div className="rounded-lg border bg-card p-3">
                  <div className="text-[9px] text-muted-foreground uppercase">AI Decision</div>
                  <div className="text-sm font-bold mt-0.5">{decision.ai_decision || "N/A"}</div>
                  {decision.ai_score != null && <div className="text-[10px] text-muted-foreground">Score: {decision.ai_score} | Conf: {decision.ai_confidence}</div>}
                </div>
                <div className="rounded-lg border bg-card p-3">
                  <div className="text-[9px] text-muted-foreground uppercase">AI/ML Agreement</div>
                  <div className="text-sm font-bold mt-0.5">{decision.ai_ml_agreement || "N/A"}</div>
                  {decision.ml_prediction && <div className="text-[10px] text-muted-foreground">ML: {decision.ml_prediction}</div>}
                </div>
                <div className="rounded-lg border bg-card p-3">
                  <div className="text-[9px] text-muted-foreground uppercase">Risk Status</div>
                  <div className={`text-sm font-bold mt-0.5 ${decision.risk_status === "approved" ? "text-emerald-500" : "text-red-500"}`}>
                    {decision.risk_status?.toUpperCase() || "WAITING"}
                  </div>
                  <div className="text-[10px] text-muted-foreground">Score: {decision.risk_score} | {decision.risk_grade}</div>
                </div>
                <div className="rounded-lg border bg-card p-3">
                  <div className="text-[9px] text-muted-foreground uppercase">Execution Mode</div>
                  <div className="text-sm font-bold mt-0.5 uppercase">{decision.execution_mode || "manual"}</div>
                  <div className="text-[10px] text-muted-foreground">Order: {decision.order_state || "—"}</div>
                </div>
              </div>
            )}

            {!decision && (
              <div className="p-8 text-center text-[10px] text-muted-foreground">
                No pipeline decisions yet. Click "Run Pipeline" to start.
              </div>
            )}
          </div>
        )}

        {activeTab === "traces" && (
          <div className="space-y-4">
            <div className="flex gap-2">
              <input type="text" value={traceId} onChange={e => setTraceId(e.target.value)}
                placeholder="Enter trace ID (e.g. TRACE-XXXXXXXX)"
                className="flex-1 h-8 rounded border bg-muted/30 px-2 text-[11px] font-mono focus:outline-none focus:ring-1 focus:ring-primary" />
              <button onClick={handleTraceLookup}
                className="px-3 py-1.5 rounded text-[10px] font-medium bg-primary text-primary-foreground hover:bg-primary/90">
                Lookup
              </button>
            </div>

            {traceData && (
              <div className="space-y-3">
                <div className="rounded-lg border bg-card p-3">
                  <div className="flex items-center gap-2 mb-2">
                    <FileText className="w-4 h-4 text-primary" />
                    <span className="text-xs font-bold">Trace: {traceData.trace_id}</span>
                    <span className="text-[9px] text-muted-foreground ml-auto">{traceData.timestamp?.split("T")[0]}</span>
                  </div>
                  <div className="grid grid-cols-3 gap-2 text-[10px] mb-3">
                    <div><span className="text-muted-foreground">Symbol:</span> {traceData.symbol}</div>
                    <div><span className="text-muted-foreground">Mode:</span> {traceData.execution_mode}</div>
                    <div><span className="text-muted-foreground">Risk:</span> {traceData.risk_status}</div>
                  </div>
                  {traceData.stages && (
                    <div className="border-t pt-2">
                      <div className="text-[9px] text-muted-foreground uppercase mb-2">Stages</div>
                      <div className="grid grid-cols-5 gap-1">
                        {Object.entries(traceData.stages).map(([name, stage]: [string, any]) => (
                          <div key={name} className={`rounded p-1.5 text-center text-[8px] ${
                            stage.status === "passed" ? "bg-emerald-500/10" :
                            stage.status === "blocked" ? "bg-red-500/10" :
                            stage.status === "skipped" ? "bg-amber-500/10" :
                            "bg-muted/20"
                          }`}>
                            <div className="font-medium">{name.replace(/_/g, " ")}</div>
                            <div className={`font-mono ${
                              stage.status === "passed" ? "text-emerald-500" :
                              stage.status === "blocked" ? "text-red-500" :
                              "text-muted-foreground"
                            }`}>{stage.status}</div>
                            {stage.duration_ms > 0 && <div className="text-muted-foreground">{stage.duration_ms}ms</div>}
                          </div>
                        ))}
                      </div>
                    </div>
                  )}
                </div>
              </div>
            )}

            {!traceData && <div className="p-8 text-center text-[10px] text-muted-foreground">Enter a trace ID to view pipeline details</div>}
          </div>
        )}

        {activeTab === "history" && <HistoryTab />}
      </div>
    </div>
  )
}

function HistoryTab() {
  const [traces, setTraces] = useState<any[]>([])
  const [loading, setLoading] = useState(true)
  useEffect(() => {
    orchestratorService.getHistory(50).then(d => setTraces(d.traces || [])).catch(() => {}).finally(() => setLoading(false))
  }, [])
  if (loading) return <div className="p-8 text-center text-[10px] text-muted-foreground">Loading history...</div>
  if (traces.length === 0) return <div className="p-8 text-center text-[10px] text-muted-foreground">No pipeline executions yet</div>
  return (
    <div className="border rounded-lg overflow-hidden">
      <table className="w-full text-[10px]">
        <thead>
          <tr className="bg-muted/30 border-b">
            <th className="text-left px-3 py-2 font-medium text-muted-foreground">Trace ID</th>
            <th className="text-left px-3 py-2 font-medium text-muted-foreground">Symbol</th>
            <th className="text-left px-3 py-2 font-medium text-muted-foreground">Mode</th>
            <th className="text-left px-3 py-2 font-medium text-muted-foreground">Risk</th>
            <th className="text-left px-3 py-2 font-medium text-muted-foreground">AI Decision</th>
            <th className="text-right px-3 py-2 font-medium text-muted-foreground">Risk Score</th>
            <th className="text-right px-3 py-2 font-medium text-muted-foreground">Timestamp</th>
          </tr>
        </thead>
        <tbody className="divide-y">
          {traces.map((t: any, i: number) => (
            <tr key={t.trace_id || i} className="hover:bg-muted/20">
              <td className="px-3 py-1.5 font-mono text-muted-foreground">{t.trace_id || "—"}</td>
              <td className="px-3 py-1.5 font-medium">{t.symbol}</td>
              <td className="px-3 py-1.5 uppercase">{t.execution_mode || "—"}</td>
              <td className="px-3 py-1.5">
                <span className={`px-1.5 py-0.5 rounded text-[8px] font-medium ${
                  t.risk_status === "approved" ? "bg-emerald-500/10 text-emerald-500" : "bg-red-500/10 text-red-500"
                }`}>{t.risk_status || "—"}</span>
              </td>
              <td className="px-3 py-1.5">{t.ai_decision || "—"}</td>
              <td className="px-3 py-1.5 text-right font-mono">{t.risk_score != null ? t.risk_score : "—"}</td>
              <td className="px-3 py-1.5 text-right text-muted-foreground">{t.timestamp?.split("T")[1]?.slice(0, 8) || "—"}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}
