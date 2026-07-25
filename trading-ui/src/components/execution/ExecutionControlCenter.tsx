"use client"

import { useState, useEffect, useCallback } from "react"
import {
  Shield, Activity, AlertTriangle, CheckCircle, XCircle, BarChart3,
  RefreshCw, Lock, Unlock, Server, FileText, Play, Zap, Radio, Clock,
  BugPlay, Shuffle, Siren,
} from "lucide-react"
import { executionService } from "@/services/executionService"

type TabId = "overview" | "orders" | "reconciliation" | "safety" | "simulation" | "audit"

export function ExecutionControlCenter() {
  const [activeTab, setActiveTab] = useState<TabId>("overview")
  const [status, setStatus] = useState<any>(null)
  const [health, setHealth] = useState<any>(null)
  const [reconciliation, setReconciliation] = useState<any>(null)
  const [posReconciliation, setPosReconciliation] = useState<any>(null)
  const [audit, setAudit] = useState<any>(null)
  const [orders, setOrders] = useState<any>(null)
  const [configHash, setConfigHash] = useState<any>(null)
  const [simResult, setSimResult] = useState<any>(null)
  const [simMode, setSimMode] = useState("happy_path")
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const fetchAll = useCallback(async () => {
    setError(null)
    try {
      const [s, h, r, pr, a, o, ch] = await Promise.all([
        executionService.getStatus().catch(() => null),
        executionService.getHealth().catch(() => null),
        executionService.getReconciliation().catch(() => null),
        executionService.getPositionReconciliation().catch(() => null),
        executionService.getAudit(50).catch(() => null),
        executionService.getOrders(50).catch(() => null),
        executionService.getConfigHash().catch(() => null),
      ])
      if (s) setStatus(s)
      if (h) setHealth(h)
      if (r) setReconciliation(r)
      if (pr) setPosReconciliation(pr)
      if (a) setAudit(a)
      if (o) setOrders(o)
      if (ch) setConfigHash(ch)
    } catch {
      setError("Failed to load execution data")
    }
    setLoading(false)
  }, [])

  useEffect(() => {
    fetchAll()
    const interval = setInterval(fetchAll, 10000)
    return () => clearInterval(interval)
  }, [fetchAll])

  const handleSimulate = async () => {
    const result = await executionService.simulate(simMode)
    setSimResult(result)
  }

  const tabs = [
    { id: "overview" as TabId, label: "Overview", icon: <Activity className="w-3.5 h-3.5" /> },
    { id: "orders" as TabId, label: "Order Monitor", icon: <BarChart3 className="w-3.5 h-3.5" /> },
    { id: "reconciliation" as TabId, label: "Reconciliation", icon: <Shuffle className="w-3.5 h-3.5" /> },
    { id: "safety" as TabId, label: "Safety", icon: <Shield className="w-3.5 h-3.5" /> },
    { id: "simulation" as TabId, label: "Simulation", icon: <BugPlay className="w-3.5 h-3.5" /> },
    { id: "audit" as TabId, label: "Audit", icon: <FileText className="w-3.5 h-3.5" /> },
  ]

  const healthColor = health?.overall === "healthy" ? "text-emerald-500"
    : health?.overall === "degraded" ? "text-amber-500"
    : health?.overall === "blocked" ? "text-red-500"
    : "text-muted-foreground"

  return (
    <div className="space-y-4">
      {/* Header */}
      <div className="flex items-center gap-2">
        <Shield className="w-5 h-5 text-primary" />
        <h1 className="text-lg font-bold">Execution Control Center</h1>
        {status?.phase_43_lock && (
          <span className="px-2 py-0.5 rounded text-[8px] font-bold bg-amber-500/10 text-amber-600 border border-amber-500/20">
            PHASE 43 LOCK
          </span>
        )}
        <button onClick={fetchAll} className="ml-auto p-1 rounded text-muted-foreground hover:text-foreground hover:bg-accent" disabled={loading}>
          <RefreshCw className={`w-3.5 h-3.5 ${loading ? "animate-spin" : ""}`} />
        </button>
      </div>

      {/* Status bar */}
      <div className="flex items-center gap-2 p-2 rounded-lg border bg-card text-[10px] flex-wrap">
        <span className="flex items-center gap-1">
          <Server className="w-3 h-3" />
          <span className={`font-bold ${healthColor}`}>{health?.overall || "unknown"}</span>
        </span>
        <span className="text-muted-foreground">|</span>
        <span>Kill Switch: {status?.kill_switch?.active ? <span className="text-red-500 font-bold">ACTIVE</span> : <span className="text-emerald-500">Inactive</span>}</span>
        <span className="text-muted-foreground">|</span>
        <span>Policy: {status?.policy?.allowed ? <span className="text-red-500">ALLOWED</span> : <span className="text-amber-500">BLOCKED</span>}</span>
        <span className="text-muted-foreground">|</span>
        <span>Reconciliation: {status?.reconciliation_blocked ? <span className="text-red-500 font-bold">FAILED</span> : <span className="text-emerald-500">OK</span>}</span>
        <span className="text-muted-foreground">|</span>
        <span>Emergency: {status?.emergency?.active ? <span className="text-red-500 font-bold">ACTIVE</span> : <span className="text-emerald-500">Inactive</span>}</span>
      </div>

      {error && <div className="rounded border border-red-500/20 bg-red-500/5 p-2 text-[10px] text-red-600">{error}</div>}

      {/* Phase 43 banner */}
      <div className="rounded-lg border border-amber-500/20 bg-amber-500/5 p-3 text-[10px] text-amber-700">
        <strong>Phase 43 — Live Execution Disabled.</strong>{' '}
        Live execution is intentionally locked in this phase. All infrastructure is built for
        preparation only. No real broker orders can be placed. Run simulations to validate the system.
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
          {/* System Status Grid */}
          <div className="grid grid-cols-4 gap-3">
            <MetricCard label="Execution Infra" value={status?.phase_43_lock ? "BLOCKED" : "READY"}
              color={status?.phase_43_lock ? "text-amber-500" : "text-emerald-500"} />
            <MetricCard label="Broker Connectivity" value={health?.checks?.broker_connectivity?.state || "unknown"}
              color={health?.checks?.broker_connectivity?.state === "healthy" ? "text-emerald-500" : "text-red-500"} />
            <MetricCard label="Market Data" value={health?.checks?.market_data_freshness?.state || "unknown"}
              color={health?.checks?.market_data_freshness?.state === "healthy" ? "text-emerald-500" : "text-red-500"} />
            <MetricCard label="Kill Switch" value={status?.kill_switch?.active ? "ACTIVE" : "INACTIVE"}
              color={status?.kill_switch?.active ? "text-red-500" : "text-emerald-500"} />
          </div>

          {/* Execution Readiness */}
          <div className="rounded-lg border bg-card p-4">
            <h3 className="text-xs font-bold mb-3 flex items-center gap-2">
              <Zap className="w-3.5 h-3.5" /> Execution Readiness
            </h3>
            <div className="p-3 rounded bg-amber-500/5 border border-amber-500/20 text-center">
              <div className="text-lg font-bold text-amber-500">NOT ENABLED</div>
              <div className="text-[10px] text-muted-foreground mt-1">
                Live execution is intentionally disabled in Phase 43.
                All infrastructure is built for preparation only.
                Enablement requires a dedicated controlled phase after Phase 43.
              </div>
            </div>
          </div>

          {/* Safety Status */}
          <div className="rounded-lg border bg-card p-4">
            <h3 className="text-xs font-bold mb-3 flex items-center gap-2">
              <Shield className="w-3.5 h-3.5" /> Safety Systems
            </h3>
            <div className="grid grid-cols-2 gap-2 text-[10px]">
              <CheckItem label="Phase 43 Lock" active={status?.phase_43_lock} />
              <CheckItem label="Kill Switch Available" active={!!status?.kill_switch} />
              <CheckItem label="Policy Engine" active={!!status?.policy} />
              <CheckItem label="Execution Health" active={status?.health?.overall !== "blocked"} />
              <CheckItem label="Reconciliation OK" active={!status?.reconciliation_blocked} />
              <CheckItem label="Emergency Inactive" active={!status?.emergency?.active} />
              <CheckItem label="Config Guard" active={!status?.config_guard?.drift_detected} />
              <CheckItem label="Live Exec Possible" active={!!status?.live_execution_possible} colorActive="text-red-500" />
            </div>
          </div>

          {/* Permission Checks */}
          <div className="rounded-lg border bg-card p-4">
            <h3 className="text-xs font-bold mb-3 flex items-center gap-2">
              <Lock className="w-3.5 h-3.5" /> Permission Checks
            </h3>
            {status?.policy?.blocking_checks?.length > 0 ? (
              <div className="space-y-1 text-[10px]">
                {status.policy.blocking_checks.map((check: string, i: number) => (
                  <div key={i} className="flex items-center gap-1.5">
                    <XCircle className="w-3 h-3 text-red-500 shrink-0" />
                    <span>{check}</span>
                  </div>
                ))}
              </div>
            ) : (
              <div className="flex items-center gap-1.5 text-[10px]">
                <CheckCircle className="w-3 h-3 text-emerald-500" />
                <span>No blocking checks (but Phase 43 lock still active)</span>
              </div>
            )}
          </div>

          {/* Health Checks */}
          {health?.checks && (
            <div className="rounded-lg border bg-card p-4">
              <h3 className="text-xs font-bold mb-3 flex items-center gap-2">
                <Activity className="w-3.5 h-3.5" /> Health Checks
              </h3>
              <div className="grid grid-cols-2 gap-2 text-[10px]">
                {Object.entries(health.checks).map(([name, check]: [string, any]) => (
                  <div key={name} className="flex items-center gap-1.5">
                    {check.state === "healthy" ? <CheckCircle className="w-3 h-3 text-emerald-500" />
                      : check.state === "blocked" ? <XCircle className="w-3 h-3 text-red-500" />
                      : <AlertTriangle className="w-3 h-3 text-amber-500" />}
                    <span className="capitalize">{name.replace(/_/g, " ")}</span>
                    <span className={`ml-auto text-[8px] uppercase font-bold
                      ${check.state === "healthy" ? "text-emerald-500" :
                        check.state === "blocked" ? "text-red-500" :
                        check.state === "degraded" ? "text-amber-500" : "text-muted-foreground"}`}>
                      {check.state}
                    </span>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Config Hash */}
          <div className="rounded-lg border bg-card p-4">
            <h3 className="text-xs font-bold mb-3 flex items-center gap-2">
              <FileText className="w-3.5 h-3.5" /> Configuration Integrity
            </h3>
            <div className="text-[10px] space-y-1">
              <div className="flex justify-between">
                <span className="text-muted-foreground">Approval Snapshot:</span>
                <span className="font-mono">{configHash?.has_approval_snapshot ? "Captured" : "None"}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-muted-foreground">Drift Detected:</span>
                <span className={configHash?.drift_detected ? "text-red-500 font-bold" : "text-emerald-500"}>
                  {configHash?.drift_detected ? "YES" : "NO"}
                </span>
              </div>
              {configHash?.drift_reason && (
                <div className="text-red-500 mt-1">{configHash.drift_reason}</div>
              )}
              <div className="flex justify-between">
                <span className="text-muted-foreground">Approval Hash:</span>
                <span className="font-mono text-[8px]">{configHash?.approval_hash || "—"}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-muted-foreground">Current Hash:</span>
                <span className="font-mono text-[8px]">{configHash?.current_hash || "—"}</span>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Orders Tab */}
      {activeTab === "orders" && (
        <div className="space-y-3">
          <div className="text-[10px] text-muted-foreground">
            Order state monitor. Phase 43: no live orders exist. Showing audit events tagged with order activity.
          </div>
          {orders?.orders?.length === 0 ? (
            <div className="p-8 text-center text-[10px] text-muted-foreground">No order events recorded</div>
          ) : (
            <div className="border rounded-lg overflow-hidden">
              <table className="w-full text-[10px]">
                <thead><tr className="bg-muted/30 border-b">
                  <th className="text-left px-3 py-2">Event ID</th>
                  <th className="text-left px-3 py-2">Type</th>
                  <th className="text-left px-3 py-2">Severity</th>
                  <th className="text-left px-3 py-2">Order ID</th>
                  <th className="text-left px-3 py-2">Reason</th>
                  <th className="text-left px-3 py-2">Timestamp</th>
                </tr></thead>
                <tbody className="divide-y">
                  {(orders?.orders || []).map((e: any, i: number) => (
                    <tr key={e.event_id || i} className="hover:bg-muted/20">
                      <td className="px-3 py-1.5 font-mono text-[8px]">{(e.event_id || "").slice(0, 12)}</td>
                      <td className="px-3 py-1.5">{e.event_type}</td>
                      <td className="px-3 py-1.5">
                        <span className={`px-1.5 py-0.5 rounded text-[8px] font-medium ${
                          e.severity === "critical" || e.severity === "error" ? "bg-red-500/10 text-red-500" :
                          e.severity === "warning" ? "bg-amber-500/10 text-amber-500" :
                          "bg-muted/20 text-muted-foreground"
                        }`}>{e.severity}</span>
                      </td>
                      <td className="px-3 py-1.5 font-mono text-[8px]">{(e.order_id || "").slice(0, 12) || "—"}</td>
                      <td className="px-3 py-1.5 text-muted-foreground max-w-[200px] truncate">{e.reason || "—"}</td>
                      <td className="px-3 py-1.5 text-[8px] text-muted-foreground">
                        {e.timestamp ? e.timestamp.split(".")[0].replace("T", " ") : "—"}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      )}

      {/* Reconciliation Tab */}
      {activeTab === "reconciliation" && (
        <div className="grid grid-cols-2 gap-3">
          <div className="rounded-lg border bg-card p-4">
            <h3 className="text-xs font-bold mb-3">Order Reconciliation</h3>
            <div className="space-y-2 text-[10px]">
              <div className="flex justify-between">
                <span className="text-muted-foreground">Total Issues:</span>
                <span>{reconciliation?.total || 0}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-muted-foreground">Blocking Issues:</span>
                <span className={reconciliation?.blocking?.length > 0 ? "text-red-500 font-bold" : "text-emerald-500"}>
                  {reconciliation?.blocking?.length || 0}
                </span>
              </div>
            </div>
            {reconciliation?.issues?.length > 0 && (
              <div className="mt-3 space-y-1 max-h-60 overflow-y-auto">
                {reconciliation.issues.map((issue: any, i: number) => (
                  <div key={i} className={`p-2 rounded text-[9px] border ${
                    issue.severity === "critical" || issue.severity === "error"
                      ? "border-red-500/20 bg-red-500/5"
                      : issue.severity === "warning"
                      ? "border-amber-500/20 bg-amber-500/5"
                      : "border-muted/20"
                  }`}>
                    <div className="font-medium">{issue.description}</div>
                    <div className="text-muted-foreground mt-0.5">
                      Internal: {issue.internal_state} | Broker: {issue.broker_state}
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>

          <div className="rounded-lg border bg-card p-4">
            <h3 className="text-xs font-bold mb-3">Position Reconciliation</h3>
            <div className="space-y-2 text-[10px]">
              <div className="flex justify-between">
                <span className="text-muted-foreground">Total Discrepancies:</span>
                <span>{posReconciliation?.total || 0}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-muted-foreground">Blocked:</span>
                <span className={posReconciliation?.blocked ? "text-red-500 font-bold" : "text-emerald-500"}>
                  {posReconciliation?.blocked ? "YES" : "NO"}
                </span>
              </div>
            </div>
            {posReconciliation?.discrepancies?.length > 0 && (
              <div className="mt-3 space-y-1 max-h-60 overflow-y-auto">
                {posReconciliation.discrepancies.map((d: any, i: number) => (
                  <div key={i} className={`p-2 rounded text-[9px] border ${
                    d.severity === "critical" || d.severity === "error"
                      ? "border-red-500/20 bg-red-500/5"
                      : "border-amber-500/20 bg-amber-500/5"
                  }`}>
                    <div className="font-medium">{d.symbol} — {d.description}</div>
                    <div className="text-muted-foreground mt-0.5">
                      Internal: {d.internal_quantity} @ {d.internal_avg_price} | Broker: {d.broker_quantity} @ {d.broker_avg_price}
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      )}

      {/* Safety Tab */}
      {activeTab === "safety" && (
        <div className="space-y-4">
          {/* Kill Switch */}
          <div className="rounded-lg border bg-card p-4">
            <h3 className="text-xs font-bold mb-3 flex items-center gap-2">
              <Siren className="w-3.5 h-3.5" /> Kill Switch
            </h3>
            <div className="grid grid-cols-2 gap-3">
              <div>
                <div className="text-[10px] space-y-1">
                  <div className="flex justify-between">
                    <span className="text-muted-foreground">Status:</span>
                    <span className={status?.kill_switch?.active ? "text-red-500 font-bold" : "text-emerald-500"}>
                      {status?.kill_switch?.active ? "ACTIVE" : "INACTIVE"}
                    </span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-muted-foreground">Active Switches:</span>
                    <span>{status?.kill_switch?.active_count || 0}</span>
                  </div>
                </div>
              </div>
              <div className="flex gap-2">
                <button onClick={() => executionService.activateKillSwitch("manual from UI")}
                  className="flex-1 px-3 py-2 rounded text-[10px] font-medium bg-red-500/10 text-red-600 hover:bg-red-500/20 border border-red-500/20">
                  Activate Kill Switch
                </button>
                <button onClick={() => executionService.resetKillSwitch()}
                  className="flex-1 px-3 py-2 rounded text-[10px] font-medium bg-emerald-500/10 text-emerald-600 hover:bg-emerald-500/20 border border-emerald-500/20">
                  Reset Kill Switch
                </button>
              </div>
            </div>
          </div>

          {/* Emergency Stop */}
          <div className="rounded-lg border bg-card p-4">
            <h3 className="text-xs font-bold mb-3 flex items-center gap-2">
              <AlertTriangle className="w-3.5 h-3.5" /> Emergency Shutdown
            </h3>
            <div className="grid grid-cols-2 gap-3">
              <div className="text-[10px] space-y-1">
                <div className="flex justify-between">
                  <span className="text-muted-foreground">Status:</span>
                  <span className={status?.emergency?.active ? "text-red-500 font-bold" : "text-emerald-500"}>
                    {status?.emergency?.active ? "ACTIVE" : "INACTIVE"}
                  </span>
                </div>
              </div>
              <div className="flex gap-2">
                <button onClick={() => executionService.emergencyStop("Manual from UI")}
                  className="flex-1 px-3 py-2 rounded text-[10px] font-medium bg-red-500/10 text-red-600 hover:bg-red-500/20 border border-red-500/20">
                  <AlertTriangle className="w-3 h-3 inline mr-1" /> Emergency Stop
                </button>
                <button onClick={() => executionService.emergencyRecover()}
                  className="flex-1 px-3 py-2 rounded text-[10px] font-medium bg-amber-500/10 text-amber-600 hover:bg-amber-500/20 border border-amber-500/20">
                  Recover
                </button>
              </div>
            </div>
          </div>

          {/* Protection Systems */}
          <div className="rounded-lg border bg-card p-4">
            <h3 className="text-xs font-bold mb-3">Protection Systems</h3>
            <div className="grid grid-cols-3 gap-2 text-[10px]">
              <ProtectionCard title="Kill Switch" active={!!status?.kill_switch} level={status?.kill_switch?.active ? "Active" : "Inactive"} />
              <ProtectionCard title="Daily Loss Limit" active={true} level="Configured" />
              <ProtectionCard title="Max Drawdown" active={true} level="Configured" />
              <ProtectionCard title="Stale Data Protection" active={health?.checks?.market_data_freshness?.state !== "blocked"} level={health?.checks?.market_data_freshness?.state || "N/A"} />
              <ProtectionCard title="Position Reconciliation" active={!posReconciliation?.blocked} level={posReconciliation?.blocked ? "FAILED" : "OK"} />
              <ProtectionCard title="Order Reconciliation" active={!reconciliation?.blocking?.length} level={reconciliation?.blocking?.length > 0 ? "ISSUES" : "OK"} />
              <ProtectionCard title="Idempotency" active={true} level="Active" />
              <ProtectionCard title="Config Drift Protection" active={!status?.config_guard?.drift_detected} level={status?.config_guard?.drift_detected ? "DRIFT" : "Clean"} />
              <ProtectionCard title="Phase 43 Lock" active={true} level="ACTIVE" colorLevel="text-amber-500" />
            </div>
          </div>
        </div>
      )}

      {/* Simulation Tab */}
      {activeTab === "simulation" && (
        <div className="space-y-4">
          <div className="rounded-lg border bg-card p-4">
            <h3 className="text-xs font-bold mb-3 flex items-center gap-2">
              <BugPlay className="w-3.5 h-3.5" /> Broker Simulator
            </h3>
            <div className="text-[10px] text-muted-foreground mb-3">
              Run infrastructure tests using the broker simulator. Never connects to a real broker.
            </div>

            <div className="flex gap-2 mb-3">
              <select value={simMode} onChange={e => setSimMode(e.target.value)}
                className="flex-1 px-2 py-1.5 rounded border bg-card text-[10px]">
                <option value="happy_path">Happy Path — Full Fill</option>
                <option value="reject">Rejection</option>
                <option value="partial_fill">Partial Fill</option>
                <option value="timeout">Timeout</option>
                <option value="delayed_ack">Delayed Acknowledge</option>
                <option value="cancel">Cancellation</option>
                <option value="duplicate_response">Duplicate Response</option>
                <option value="unknown_order">Unknown Order</option>
                <option value="reconciliation_mismatch">Reconciliation Mismatch</option>
              </select>
              <button onClick={handleSimulate}
                className="px-4 py-1.5 rounded text-[10px] font-medium bg-primary/10 text-primary hover:bg-primary/20 border border-primary/20">
                <Play className="w-3 h-3 inline mr-1" /> Run
              </button>
            </div>

            {simResult && (
              <div className="space-y-2">
                <div className="text-[10px] font-medium">Simulation Result:</div>
                <pre className="p-3 rounded bg-muted/20 text-[9px] font-mono overflow-x-auto border">
                  {JSON.stringify(simResult, null, 2)}
                </pre>
                <div className="text-[9px] text-muted-foreground">
                  Note: Simulated only. No real order placed. Phase 43: live execution disabled.
                </div>
              </div>
            )}
          </div>

          <div className="rounded-lg border bg-card p-4">
            <h3 className="text-xs font-bold mb-3">Test Scenarios</h3>
            <div className="text-[10px] space-y-2">
              <p>Available failure scenarios to validate infrastructure:</p>
              <ul className="list-disc pl-4 space-y-1 text-muted-foreground">
                <li>Duplicate signal / API request</li>
                <li>Websocket reconnect handling</li>
                <li>Broker timeout / rejection</li>
                <li>Partial fill tracking</li>
                <li>Unknown broker order</li>
                <li>Internal/broker state mismatch</li>
                <li>Position mismatch detection</li>
              </ul>
            </div>
          </div>
        </div>
      )}

      {/* Audit Tab */}
      {activeTab === "audit" && (
        <div className="space-y-3">
          <div className="flex justify-between items-center">
            <div className="text-[10px] text-muted-foreground">
              Append-only event log. Total events: {audit?.total || 0}
            </div>
          </div>
          {audit?.entries?.length === 0 ? (
            <div className="p-8 text-center text-[10px] text-muted-foreground">No audit events recorded</div>
          ) : (
            <div className="border rounded-lg overflow-hidden max-h-96 overflow-y-auto">
              <table className="w-full text-[10px]">
                <thead><tr className="bg-muted/30 border-b sticky top-0">
                  <th className="text-left px-3 py-2">Event ID</th>
                  <th className="text-left px-3 py-2">Type</th>
                  <th className="text-left px-3 py-2">Severity</th>
                  <th className="text-left px-3 py-2">Actor</th>
                  <th className="text-left px-3 py-2">Reason</th>
                  <th className="text-left px-3 py-2">Timestamp</th>
                </tr></thead>
                <tbody className="divide-y">
                  {(audit?.entries || []).map((e: any, i: number) => (
                    <tr key={e.event_id || i} className="hover:bg-muted/20">
                      <td className="px-3 py-1.5 font-mono text-[8px]">{(e.event_id || "").slice(0, 12)}</td>
                      <td className="px-3 py-1.5">{e.event_type}</td>
                      <td className="px-3 py-1.5">
                        <span className={`px-1.5 py-0.5 rounded text-[8px] font-medium ${
                          e.severity === "critical" ? "bg-red-500/10 text-red-500" :
                          e.severity === "error" ? "bg-red-500/5 text-red-400" :
                          e.severity === "warning" ? "bg-amber-500/10 text-amber-500" :
                          "bg-muted/20 text-muted-foreground"
                        }`}>{e.severity}</span>
                      </td>
                      <td className="px-3 py-1.5">{e.actor || "system"}</td>
                      <td className="px-3 py-1.5 text-muted-foreground max-w-[200px] truncate">{e.reason || "—"}</td>
                      <td className="px-3 py-1.5 text-[8px] text-muted-foreground">
                        {e.timestamp ? e.timestamp.split(".")[0].replace("T", " ") : "—"}
                      </td>
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

function CheckItem({ label, active, colorActive }: { label: string; active: boolean; colorActive?: string }) {
  return <div className="flex items-center gap-1.5">
    {active
      ? <CheckCircle className={`w-3 h-3 ${colorActive || "text-emerald-500"}`} />
      : <XCircle className="w-3 h-3 text-red-500" />}
    <span>{label}</span>
  </div>
}

function ProtectionCard({ title, active, level, colorLevel }: { title: string; active: boolean; level: string; colorLevel?: string }) {
  return <div className={`p-2 rounded border ${active ? "bg-card" : "bg-red-500/5 border-red-500/20"}`}>
    <div className="text-[9px] text-muted-foreground">{title}</div>
    <div className={`text-xs font-bold mt-0.5 ${colorLevel || (active ? "text-emerald-500" : "text-red-500")}`}>{level}</div>
  </div>
}
