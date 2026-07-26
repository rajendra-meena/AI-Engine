"use client"

import { useState, useEffect, useCallback } from "react"
import {
  Shield, Activity, AlertTriangle, CheckCircle, XCircle, BarChart3,
  RefreshCw, Lock, Server, FileText, Play, Zap, Radio, Clock, Siren,
  BugPlay, Shuffle, UserCheck, TrendingUp,
} from "lucide-react"
import { preLiveService } from "@/services/preLiveService"

type TabId = "overview" | "checks" | "broker" | "market" | "reconciliation" | "security" | "simulation"

export function PreLiveControlCenter() {
  const [activeTab, setActiveTab] = useState<TabId>("overview")
  const [status, setStatus] = useState<any>(null)
  const [report, setReport] = useState<any>(null)
  const [broker, setBroker] = useState<any>(null)
  const [marketData, setMarketData] = useState<any>(null)
  const [reconciliation, setReconciliation] = useState<any>(null)
  const [security, setSecurity] = useState<any>(null)
  const [executionLock, setExecutionLock] = useState<any>(null)
  const [loading, setLoading] = useState(true)
  const [running, setRunning] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [simResult, setSimResult] = useState<any>(null)
  const [simScenario, setSimScenario] = useState("broker_unavailable")

  const fetchAll = useCallback(async () => {
    setError(null)
    try {
      const [s, b, md, rec, sec, lock] = await Promise.all([
        preLiveService.getStatus().catch(() => null),
        preLiveService.getBroker().catch(() => null),
        preLiveService.getMarketData().catch(() => null),
        preLiveService.getReconciliation().catch(() => null),
        preLiveService.getSecurity().catch(() => null),
        preLiveService.getExecutionLock().catch(() => null),
      ])
      if (s) { setStatus(s); if (s.latest_validation) setReport(s.latest_validation) }
      if (b) setBroker(b)
      if (md) setMarketData(md)
      if (rec) setReconciliation(rec)
      if (sec) setSecurity(sec)
      if (lock) setExecutionLock(lock)
    } catch {
      setError("Failed to load pre-live data")
    }
    setLoading(false)
  }, [])

  useEffect(() => {
    const t = setTimeout(() => fetchAll(), 0)
    const interval = setInterval(fetchAll, 15000)
    return () => { clearTimeout(t); clearInterval(interval) }
  }, [fetchAll])

  const handleRunValidation = async () => {
    setRunning(true)
    setError(null)
    try {
      const result = await preLiveService.runValidation()
      setReport(result)
      await fetchAll()
    } catch {
      setError("Validation failed")
    }
    setRunning(false)
  }

  const handleSimulate = async () => {
    try {
      const result = await preLiveService.simulateFailure(simScenario)
      setSimResult(result)
      await fetchAll()
    } catch {
      setError("Simulation failed")
    }
  }

  const tabs = [
    { id: "overview" as TabId, label: "Overview", icon: <Activity className="w-3.5 h-3.5" /> },
    { id: "checks" as TabId, label: "Check List", icon: <FileText className="w-3.5 h-3.5" /> },
    { id: "broker" as TabId, label: "Broker", icon: <Radio className="w-3.5 h-3.5" /> },
    { id: "market" as TabId, label: "Market Data", icon: <TrendingUp className="w-3.5 h-3.5" /> },
    { id: "reconciliation" as TabId, label: "Reconciliation", icon: <Shuffle className="w-3.5 h-3.5" /> },
    { id: "security" as TabId, label: "Security", icon: <Shield className="w-3.5 h-3.5" /> },
    { id: "simulation" as TabId, label: "Simulation", icon: <BugPlay className="w-3.5 h-3.5" /> },
  ]

  const classColor = report?.classification === "ready_for_live_activation" ? "text-emerald-500"
    : report?.classification === "conditional_review" ? "text-amber-500"
    : report?.classification === "blocked" ? "text-red-500"
    : report?.classification === "failed" ? "text-red-600"
    : "text-muted-foreground"

  return (
    <div className="space-y-4">
      {/* Header */}
      <div className="flex items-center gap-2">
        <Shield className="w-5 h-5 text-primary" />
        <h1 className="text-lg font-bold">Pre-Live Validation</h1>
        <span className="px-2 py-0.5 rounded text-[8px] font-bold bg-amber-500/10 text-amber-600 border border-amber-500/20">
          PHASE 44
        </span>
        <button onClick={fetchAll} className="ml-auto p-1 rounded text-muted-foreground hover:text-foreground hover:bg-accent" disabled={loading}>
          <RefreshCw className={`w-3.5 h-3.5 ${loading ? "animate-spin" : ""}`} />
        </button>
        <button onClick={handleRunValidation} disabled={running}
          className="px-3 py-1 rounded text-[10px] font-medium bg-primary/10 text-primary hover:bg-primary/20 border border-primary/20">
          {running ? "Running..." : "Run Validation"}
        </button>
      </div>

      {/* Status bar */}
      <div className="flex items-center gap-2 p-2 rounded-lg border bg-card text-[10px] flex-wrap">
        <span className="flex items-center gap-1">
          <BarChart3 className="w-3 h-3" />
          <span>Score: <strong>{report?.score ?? "—"}</strong></span>
        </span>
        <span className="text-muted-foreground">|</span>
        <span>Status: <span className={`font-bold ${classColor}`}>{report?.classification?.replace(/_/g, " ") || "not tested"}</span></span>
        <span className="text-muted-foreground">|</span>
        <span>Checks: {report?.checks?.length || 0}</span>
        <span className="text-muted-foreground">|</span>
        <span className="flex items-center gap-1">
          <Lock className="w-3 h-3 text-amber-500" />
          <span className="text-amber-500 font-bold">LIVE EXECUTION DISABLED</span>
        </span>
      </div>

      {error && <div className="rounded border border-red-500/20 bg-red-500/5 p-2 text-[10px] text-red-600">{error}</div>}

      {/* Phase 44 banner */}
      <div className="rounded-lg border border-amber-500/20 bg-amber-500/5 p-3 text-[10px] text-amber-700">
        <strong>Phase 44 — Controlled Pre-Live Operational Validation.</strong>{' '}
        All checks run in read-only mode. LIVE auto trading remains disabled.
        The system validates readiness but cannot execute live orders.
      </div>

      {/* Tabs */}
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

      {/* Overview Tab */}
      {activeTab === "overview" && (
        <div className="space-y-4">
          {/* Key metrics */}
          <div className="grid grid-cols-4 gap-3">
            <MetricCard label="Readiness Score" value={report?.score != null ? `${Math.round(report.score)}%` : "—"} color={classColor} />
            <MetricCard label="Classification" value={report?.classification?.replace(/_/g, " ") || "not tested"} color={classColor} />
            <MetricCard label="Checks Passed" value={
              report?.checks ? `${report.checks.filter((c: any) => c.status === "pass").length}/${report.checks.length}` : "—"
            } color="text-emerald-500" />
            <MetricCard label="Hard Blocks" value={report?.hard_blocks?.length || 0} color={report?.hard_blocks?.length > 0 ? "text-red-500" : "text-emerald-500"} />
          </div>

          {/* Execution Lock */}
          <div className="rounded-lg border bg-card p-4">
            <h3 className="text-xs font-bold mb-3 flex items-center gap-2">
              <Lock className="w-3.5 h-3.5" /> Live Auto Trading
            </h3>
            <div className="p-4 rounded bg-amber-500/5 border border-amber-500/20 text-center">
              <div className="text-2xl font-bold text-amber-500 mb-1">🔒 DISABLED</div>
              <div className="text-[10px] text-muted-foreground">
                Phase 43 execution lock is active.{' '}
                {executionLock?.message || "LIVE trading remains disabled."}
                <br />
                <strong>can_execute_live = {String(executionLock?.can_execute_live ?? false)}</strong>
                {' | '}
                <strong>phase_43_lock = {String(executionLock?.phase_43_lock_active ?? true)}</strong>
              </div>
            </div>
          </div>

          {/* Score Breakdown */}
          {report?.checks && (
            <div className="rounded-lg border bg-card p-4">
              <h3 className="text-xs font-bold mb-3">Validation Checks Summary</h3>
              <div className="grid grid-cols-3 gap-2 text-[10px]">
                {report.checks.map((check: any, i: number) => (
                  <div key={i} className={`p-2 rounded border ${
                    check.status === "pass" ? "border-emerald-500/20 bg-emerald-500/5" :
                    check.status === "warning" ? "border-amber-500/20 bg-amber-500/5" :
                    check.status === "blocked" || check.status === "fail" ? "border-red-500/20 bg-red-500/5" :
                    "border-muted/20"
                  }`}>
                    <div className="flex items-center gap-1">
                      {check.status === "pass" ? <CheckCircle className="w-3 h-3 text-emerald-500" /> :
                       check.status === "warning" ? <AlertTriangle className="w-3 h-3 text-amber-500" /> :
                       check.status === "blocked" || check.status === "fail" ? <XCircle className="w-3 h-3 text-red-500" /> :
                       <Clock className="w-3 h-3 text-muted-foreground" />}
                      <span className="font-medium capitalize">{check.category?.replace(/_/g, " ")}</span>
                    </div>
                    <div className="text-[8px] text-muted-foreground mt-0.5">{check.message || check.status}</div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Hard Blocks */}
          {report?.hard_blocks?.length > 0 && (
            <div className="rounded-lg border border-red-500/20 bg-red-500/5 p-4">
              <h3 className="text-xs font-bold mb-2 text-red-600 flex items-center gap-2">
                <XCircle className="w-3.5 h-3.5" /> Hard Blocks
              </h3>
              <ul className="space-y-1 text-[10px]">
                {report.hard_blocks.map((block: string, i: number) => (
                  <li key={i} className="flex items-center gap-1.5">
                    <XCircle className="w-3 h-3 text-red-500 shrink-0" />
                    <span>{block.replace(/_/g, " ")}</span>
                  </li>
                ))}
              </ul>
            </div>
          )}
        </div>
      )}

      {/* Check List Tab */}
      {activeTab === "checks" && (
        <div className="space-y-2">
          {report?.checks?.length === 0 ? (
            <div className="p-8 text-center text-[10px] text-muted-foreground">
              No checks run yet. Click &ldquo;Run Validation&rdquo; to start.
            </div>
          ) : (
            <div className="border rounded-lg overflow-hidden">
              <table className="w-full text-[10px]">
                <thead><tr className="bg-muted/30 border-b">
                  <th className="text-left px-3 py-2">Category</th>
                  <th className="text-left px-3 py-2">Name</th>
                  <th className="text-left px-3 py-2">Status</th>
                  <th className="text-left px-3 py-2">Message</th>
                  <th className="text-right px-3 py-2">Duration (ms)</th>
                </tr></thead>
                <tbody className="divide-y">
                  {(report?.checks || []).map((check: any, i: number) => (
                    <tr key={check.check_id || i} className="hover:bg-muted/20">
                      <td className="px-3 py-1.5 font-medium capitalize">{check.category?.replace(/_/g, " ")}</td>
                      <td className="px-3 py-1.5">{check.name}</td>
                      <td className="px-3 py-1.5">
                        <span className={`px-1.5 py-0.5 rounded text-[8px] font-medium ${
                          check.status === "pass" ? "bg-emerald-500/10 text-emerald-500" :
                          check.status === "warning" ? "bg-amber-500/10 text-amber-500" :
                          check.status === "blocked" || check.status === "fail" ? "bg-red-500/10 text-red-500" :
                          "bg-muted/20 text-muted-foreground"
                        }`}>{check.status}</span>
                      </td>
                      <td className="px-3 py-1.5 text-muted-foreground max-w-[250px] truncate">{check.message || "—"}</td>
                      <td className="px-3 py-1.5 text-right font-mono">{check.duration_ms?.toFixed(0) || "—"}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      )}

      {/* Broker Tab */}
      {activeTab === "broker" && (
        <div className="space-y-4">
          <div className="rounded-lg border bg-card p-4">
            <h3 className="text-xs font-bold mb-3 flex items-center gap-2">
              <Radio className="w-3.5 h-3.5" /> Broker Connectivity (Read-Only)
            </h3>
            <div className="text-[10px] text-muted-foreground mb-3">
              Read-only check. No orders are placed, modified, or cancelled.
            </div>
            <div className="grid grid-cols-2 gap-3 text-[10px]">
              <div className="space-y-1">
                <div className="flex justify-between p-1.5 rounded bg-muted/20">
                  <span className="text-muted-foreground">Status:</span>
                  <span className={broker?.status === "connected" ? "text-emerald-500 font-bold" : "text-red-500"}>
                    {broker?.status || "unknown"}
                  </span>
                </div>
                <div className="flex justify-between p-1.5 rounded bg-muted/20">
                  <span className="text-muted-foreground">Broker:</span>
                  <span>{broker?.broker || "not configured"}</span>
                </div>
                <div className="flex justify-between p-1.5 rounded bg-muted/20">
                  <span className="text-muted-foreground">Health:</span>
                  <span>{broker?.health?.status || "unknown"}</span>
                </div>
              </div>
              <div className="space-y-1">
                <div className="flex justify-between p-1.5 rounded bg-muted/20">
                  <span className="text-muted-foreground">Account:</span>
                  <span>{broker?.account?.status || "—"}</span>
                </div>
                <div className="flex justify-between p-1.5 rounded bg-muted/20">
                  <span className="text-muted-foreground">Available Funds:</span>
                  <span className="font-mono">{broker?.balance?.available ?? "—"}</span>
                </div>
                <div className="flex justify-between p-1.5 rounded bg-muted/20">
                  <span className="text-muted-foreground">Phase 43:</span>
                  <span className="text-amber-500">{broker?.phase_43 ? "LOCKED" : "?"}</span>
                </div>
              </div>
            </div>
          </div>

          <div className="rounded-lg border border-amber-500/20 bg-amber-500/5 p-3 text-[10px] text-amber-700">
            <strong>⚠ Read-Only Mode.</strong> All broker operations are read-only.
            Real order placement raises <code>LiveExecutionDisabledError</code>.
          </div>
        </div>
      )}

      {/* Market Data Tab */}
      {activeTab === "market" && (
        <div className="rounded-lg border bg-card p-4">
          <h3 className="text-xs font-bold mb-3 flex items-center gap-2">
            <TrendingUp className="w-3.5 h-3.5" /> Market Data Health
          </h3>
          {marketData ? (
            <div className="grid grid-cols-2 gap-3 text-[10px]">
              <div className="space-y-1">
                <div className="flex justify-between p-1.5 rounded bg-muted/20">
                  <span className="text-muted-foreground">Market Data:</span>
                  <span className={marketData.market_data?.state === "healthy" ? "text-emerald-500" : "text-amber-500"}>
                    {marketData.market_data?.state || "unknown"}
                  </span>
                </div>
                <div className="flex justify-between p-1.5 rounded bg-muted/20">
                  <span className="text-muted-foreground">Latency:</span>
                  <span>{marketData.market_data?.latency_ms ?? "—"} ms</span>
                </div>
              </div>
              <div className="space-y-1">
                <div className="flex justify-between p-1.5 rounded bg-muted/20">
                  <span className="text-muted-foreground">WebSocket:</span>
                  <span className={marketData.websocket?.state === "healthy" ? "text-emerald-500" : "text-amber-500"}>
                    {marketData.websocket?.state || "unknown"}
                  </span>
                </div>
                <div className="flex justify-between p-1.5 rounded bg-muted/20">
                  <span className="text-muted-foreground">Overall:</span>
                  <span className={marketData.status === "healthy" ? "text-emerald-500 font-bold" : "text-amber-500"}>
                    {marketData.status || "unknown"}
                  </span>
                </div>
              </div>
            </div>
          ) : (
            <div className="text-[10px] text-muted-foreground">No market data available</div>
          )}
        </div>
      )}

      {/* Reconciliation Tab */}
      {activeTab === "reconciliation" && (
        <div className="grid grid-cols-2 gap-3">
          <div className="rounded-lg border bg-card p-4">
            <h3 className="text-xs font-bold mb-3">Order Reconciliation</h3>
            <div className="space-y-2 text-[10px]">
              <div className="flex justify-between p-1.5 rounded bg-muted/20">
                <span className="text-muted-foreground">Status:</span>
                <span className={reconciliation?.order_reconciliation?.status === "clean" ? "text-emerald-500" : "text-red-500"}>
                  {reconciliation?.order_reconciliation?.status || "unknown"}
                </span>
              </div>
              <div className="flex justify-between p-1.5 rounded bg-muted/20">
                <span className="text-muted-foreground">Total Issues:</span>
                <span>{reconciliation?.order_reconciliation?.total_issues ?? "—"}</span>
              </div>
              <div className="flex justify-between p-1.5 rounded bg-muted/20">
                <span className="text-muted-foreground">Blocking:</span>
                <span className={reconciliation?.order_reconciliation?.blocking_issues > 0 ? "text-red-500" : "text-emerald-500"}>
                  {reconciliation?.order_reconciliation?.blocking_issues ?? "—"}
                </span>
              </div>
            </div>
          </div>
          <div className="rounded-lg border bg-card p-4">
            <h3 className="text-xs font-bold mb-3">Position Reconciliation</h3>
            <div className="space-y-2 text-[10px]">
              <div className="flex justify-between p-1.5 rounded bg-muted/20">
                <span className="text-muted-foreground">Status:</span>
                <span className={reconciliation?.position_reconciliation?.status === "clean" ? "text-emerald-500" : "text-red-500"}>
                  {reconciliation?.position_reconciliation?.status || "unknown"}
                </span>
              </div>
              <div className="flex justify-between p-1.5 rounded bg-muted/20">
                <span className="text-muted-foreground">Discrepancies:</span>
                <span>{reconciliation?.position_reconciliation?.total_discrepancies ?? "—"}</span>
              </div>
              <div className="flex justify-between p-1.5 rounded bg-muted/20">
                <span className="text-muted-foreground">Blocked:</span>
                <span className={reconciliation?.position_reconciliation?.blocked ? "text-red-500" : "text-emerald-500"}>
                  {reconciliation?.position_reconciliation?.blocked ? "YES" : "NO"}
                </span>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Security Tab */}
      {activeTab === "security" && (
        <div className="space-y-4">
          <div className="rounded-lg border bg-card p-4">
            <h3 className="text-xs font-bold mb-3 flex items-center gap-2">
              <Shield className="w-3.5 h-3.5" /> Security Validation
            </h3>
            <div className="grid grid-cols-2 gap-2 text-[10px]">
              {security?.security_checks && Object.entries(security.security_checks).map(([key, val]: [string, any]) => (
                <div key={key} className="flex items-center gap-1.5 p-1.5 rounded bg-muted/20">
                  {val === false || val === true ? (
                    val === false || (typeof val === "boolean" && !val) || val === "live" ? (
                      <XCircle className="w-3 h-3 text-red-500 shrink-0" />
                    ) : (
                      <CheckCircle className="w-3 h-3 text-emerald-500 shrink-0" />
                    )
                  ) : val === "observe" || val === "shadow" ? (
                    <CheckCircle className="w-3 h-3 text-emerald-500 shrink-0" />
                  ) : (
                    <AlertTriangle className="w-3 h-3 text-amber-500 shrink-0" />
                  )}
                  <span className="capitalize">{key.replace(/_/g, " ")}:</span>
                  <span className="font-mono ml-auto">{String(val)}</span>
                </div>
              ))}
            </div>
          </div>

          <div className="rounded-lg border bg-card p-4">
            <h3 className="text-xs font-bold mb-3">Execution Lock Status</h3>
            <div className="p-3 rounded bg-amber-500/5 border border-amber-500/20 text-center">
              <div className="flex items-center justify-center gap-2 text-sm font-bold text-amber-500 mb-1">
                <Lock className="w-4 h-4" /> LIVE AUTO TRADING DISABLED
              </div>
              <div className="text-[10px] text-muted-foreground">
                Phase 43 live execution lock prevents all real trading.
                {executionLock?.message && ` ${executionLock.message}`}
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Simulation Tab */}
      {activeTab === "simulation" && (
        <div className="space-y-4">
          <div className="rounded-lg border bg-card p-4">
            <h3 className="text-xs font-bold mb-3 flex items-center gap-2">
              <BugPlay className="w-3.5 h-3.5" /> Failure Scenario Simulation
            </h3>
            <div className="text-[10px] text-muted-foreground mb-3">
              Test safety systems using simulated failures. Never touches real broker connections or orders.
            </div>
            <div className="flex gap-2 mb-3">
              <select value={simScenario} onChange={e => setSimScenario(e.target.value)}
                className="flex-1 px-2 py-1.5 rounded border bg-card text-[10px]">
                <option value="broker_unavailable">Broker Unavailable / Timeout</option>
                <option value="market_data_stale">Market Data Stale</option>
                <option value="kill_switch_activate">Kill Switch Activation</option>
                <option value="config_drift">Configuration Drift</option>
              </select>
              <button onClick={handleSimulate}
                className="px-4 py-1.5 rounded text-[10px] font-medium bg-primary/10 text-primary hover:bg-primary/20 border border-primary/20">
                <Play className="w-3 h-3 inline mr-1" /> Simulate
              </button>
            </div>
            {simResult && (
              <div>
                <div className="text-[10px] font-medium mb-1">Result:</div>
                <pre className="p-3 rounded bg-muted/20 text-[9px] font-mono overflow-x-auto border max-h-32 overflow-y-auto">
                  {JSON.stringify(simResult, null, 2)}
                </pre>
              </div>
            )}
          </div>
          <div className="rounded-lg border bg-card p-4">
            <h3 className="text-xs font-bold mb-3">Test Scenarios</h3>
            <div className="text-[10px] space-y-2">
              <ul className="list-disc pl-4 space-y-1 text-muted-foreground">
                <li><strong>Broker Unavailable</strong> — Simulates broker connection failure. Execution blocked.</li>
                <li><strong>Market Data Stale</strong> — Simulates stale tick data. Execution blocked.</li>
                <li><strong>Kill Switch</strong> — Tests kill switch activation/reset cycle.</li>
                <li><strong>Config Drift</strong> — Tests configuration change detection.</li>
              </ul>
              <div className="mt-2 p-2 rounded bg-amber-500/5 border border-amber-500/20 text-amber-700">
                <strong>Note:</strong> All simulations are in-memory only. No real broker interaction.
              </div>
            </div>
          </div>
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
