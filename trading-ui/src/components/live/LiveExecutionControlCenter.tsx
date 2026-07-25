"use client"

import { useState, useEffect, useCallback } from "react"
import {
  Shield, Activity, AlertTriangle, CheckCircle, XCircle, BarChart3,
  RefreshCw, Lock, Play, Zap, Radio, TrendingUp, Clock, Siren,
  BugPlay, Shuffle, UserCheck, Timer, Ban, List,
} from "lucide-react"
import { liveExecutionService } from "@/services/liveExecutionService"

type TabId = "overview" | "preflight" | "canary" | "orders" | "positions" | "safety" | "audit"

export function LiveExecutionControlCenter() {
  const [activeTab, setActiveTab] = useState<TabId>("overview")
  const [status, setStatus] = useState<any>(null)
  const [brokerSession, setBrokerSession] = useState<any>(null)
  const [canaryStatus, setCanaryStatus] = useState<any>(null)
  const [limits, setLimits] = useState<any>(null)
  const [orders, setOrders] = useState<any>(null)
  const [positions, setPositions] = useState<any>(null)
  const [preflightResult, setPreflightResult] = useState<any>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [actionLoading, setActionLoading] = useState<string | null>(null)
  const [showConfirm, setShowConfirm] = useState<string | null>(null)
  const [reviewerInput, setReviewerInput] = useState("")
  const [reasonInput, setReasonInput] = useState("")
  const [preflightSymbol, setPreflightSymbol] = useState("RELIANCE")
  const [preflightQty, setPreflightQty] = useState(1)

  const fetchAll = useCallback(async () => {
    setError(null)
    try {
      const [s, bs, cs, l, o, p] = await Promise.all([
        liveExecutionService.getStatus().catch(() => null),
        liveExecutionService.getBrokerSession().catch(() => null),
        liveExecutionService.getCanaryStatus().catch(() => null),
        liveExecutionService.getLimits().catch(() => null),
        liveExecutionService.getOrders(10).catch(() => null),
        liveExecutionService.getPositions().catch(() => null),
      ])
      if (s) setStatus(s)
      if (bs) setBrokerSession(bs)
      if (cs) setCanaryStatus(cs)
      if (l) setLimits(l)
      if (o) setOrders(o)
      if (p) setPositions(p)
    } catch {
      setError("Failed to load execution data")
    }
    setLoading(false)
  }, [])

  useEffect(() => {
    fetchAll()
    const interval = setInterval(fetchAll, 15000)
    return () => clearInterval(interval)
  }, [fetchAll])

  const handleAction = async (action: string, fn: () => Promise<any>) => {
    setActionLoading(action)
    setError(null)
    setShowConfirm(null)
    try {
      await fn()
      await fetchAll()
    } catch (e: any) {
      setError(e.message || `${action} failed`)
    }
    setActionLoading(null)
  }

  const tabs = [
    { id: "overview" as TabId, label: "Overview", icon: <Activity className="w-3.5 h-3.5" /> },
    { id: "preflight" as TabId, label: "Preflight", icon: <Shield className="w-3.5 h-3.5" /> },
    { id: "canary" as TabId, label: "Canary", icon: <BugPlay className="w-3.5 h-3.5" /> },
    { id: "orders" as TabId, label: "Orders", icon: <List className="w-3.5 h-3.5" /> },
    { id: "positions" as TabId, label: "Positions", icon: <BarChart3 className="w-3.5 h-3.5" /> },
    { id: "safety" as TabId, label: "Safety", icon: <Shield className="w-3.5 h-3.5" /> },
    { id: "audit" as TabId, label: "Audit", icon: <Clock className="w-3.5 h-3.5" /> },
  ]

  const ConfirmationDialog = ({ action, onConfirm, onCancel }: {
    action: string; onConfirm: () => void; onCancel: () => void
  }) => (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
      <div className="rounded-lg border bg-card p-6 max-w-md mx-4 shadow-xl">
        <div className="flex items-center gap-2 mb-3">
          {action === "kill_switch" || action === "emergency_cancel" ? (
            <Siren className="w-5 h-5 text-red-500" />
          ) : (
            <AlertTriangle className="w-5 h-5 text-amber-500" />
          )}
          <h3 className="text-sm font-bold">{action.replace(/_/g, " ").toUpperCase()}</h3>
        </div>
        <p className="text-[10px] text-muted-foreground mb-4">
          {action === "canary_arm" && "This will arm canary mode. Real broker orders may be placed within strict limits."}
          {action === "emergency_cancel" && "This will CANCEL ALL OPEN ORDERS and block new entries. Requires explicit recovery."}
        </p>
        <div className="flex gap-2 justify-end">
          <button onClick={onCancel}
            className="px-3 py-1.5 rounded text-[10px] font-medium border bg-card hover:bg-accent">
            Cancel
          </button>
          <button onClick={onConfirm}
            className={`px-3 py-1.5 rounded text-[10px] font-medium text-white bg-red-600 hover:bg-red-700`}>
            Confirm {action.replace(/_/g, " ")}
          </button>
        </div>
      </div>
    </div>
  )

  return (
    <div className="space-y-4">
      {/* Header */}
      <div className="flex items-center gap-2">
        <Zap className="w-5 h-5 text-primary" />
        <h1 className="text-lg font-bold">Live Execution</h1>
        <span className="px-2 py-0.5 rounded text-[8px] font-bold bg-amber-500/10 text-amber-600 border border-amber-500/20">
          PHASE 46
        </span>
        <button onClick={fetchAll} className="ml-auto p-1 rounded text-muted-foreground hover:text-foreground hover:bg-accent" disabled={loading}>
          <RefreshCw className={`w-3.5 h-3.5 ${loading ? "animate-spin" : ""}`} />
        </button>
      </div>

      {/* Status Bar */}
      <div className="flex items-center gap-2 p-2 rounded-lg border bg-card text-[10px] flex-wrap">
        <span className="flex items-center gap-1">
          <Lock className="w-3 h-3" />
          <span>Phase 43 Lock: <strong className="text-amber-500">ACTIVE</strong></span>
        </span>
        <span className="text-muted-foreground">|</span>
        <span>Executions: <strong>{status?.total_executions || 0}</strong></span>
        <span className="text-muted-foreground">|</span>
        <span>Canary: <strong className={canaryStatus?.armed ? "text-emerald-500" : "text-muted-foreground"}>{canaryStatus?.armed ? "ARMED" : "DISARMED"}</strong></span>
        <span className="text-muted-foreground">|</span>
        <span>Daily Trades: <strong>{status?.daily_trade_count || 0}</strong></span>
      </div>

      {error && <div className="rounded border border-red-500/20 bg-red-500/5 p-2 text-[10px] text-red-600">{error}</div>}

      {/* Phase banner */}
      <div className="rounded-lg border border-amber-500/20 bg-amber-500/5 p-3 text-[10px] text-amber-700">
        <strong>Phase 46 — Controlled Live Execution Integration & Canary Trading.</strong>{' '}
        Broker session validation, preflight checks, dry-run execution, and canary trading.
        PHASE_43_LIVE_EXECUTION_LOCK remains active. Canary mode is disarmed by default.
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
          <div className="grid grid-cols-4 gap-3">
            <MetricCard label="Status" value={status ? `${status.total_executions} executions` : "—"} />
            <MetricCard label="Daily Trades" value={String(status?.daily_trade_count ?? 0)} color="text-emerald-500" />
            <MetricCard label="Canary" value={canaryStatus?.armed ? "ARMED" : "DISARMED"}
              color={canaryStatus?.armed ? "text-emerald-500" : "text-muted-foreground"} />
            <MetricCard label="Recent Success" value={
              status ? `${status.recent_results?.success || 0}/${status.recent_results?.total || 0}` : "—"
            } color={status?.recent_results?.success > 0 ? "text-emerald-500" : "text-muted-foreground"} />
          </div>

          <div className="rounded-lg border bg-card p-4">
            <h3 className="text-xs font-bold mb-3 flex items-center gap-2">
              <Radio className="w-3.5 h-3.5" /> Broker Session
            </h3>
            {brokerSession?.session ? (
              <div className="grid grid-cols-2 gap-2 text-[10px]">
                <div className="flex justify-between p-1.5 rounded bg-muted/20">
                  <span className="text-muted-foreground">Authenticated:</span>
                  <span className={brokerSession.session.authenticated ? "text-emerald-500" : "text-red-500"}>
                    {brokerSession.session.authenticated ? "YES" : "NO"}
                  </span>
                </div>
                <div className="flex justify-between p-1.5 rounded bg-muted/20">
                  <span className="text-muted-foreground">All Valid:</span>
                  <span className={brokerSession.session.all_valid ? "text-emerald-500" : "text-red-500"}>
                    {brokerSession.session.all_valid ? "YES" : "NO"}
                  </span>
                </div>
              </div>
            ) : (
              <div className="text-[10px] text-muted-foreground">No session data</div>
            )}
          </div>

          {/* Execution Lock */}
          <div className="rounded-lg border bg-card p-4">
            <h3 className="text-xs font-bold mb-3 flex items-center gap-2">
              <Lock className="w-3.5 h-3.5" /> Live Auto Trading
            </h3>
            <div className="p-4 rounded bg-amber-500/5 border border-amber-500/20 text-center">
              <div className="text-2xl font-bold text-amber-500 mb-1">🔒 DISABLED</div>
              <div className="text-[10px] text-muted-foreground">
                Phase 43 execution lock is active. PHASE_43_LIVE_EXECUTION_LOCK remains TRUE.
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Preflight Tab */}
      {activeTab === "preflight" && (
        <div className="space-y-4">
          <div className="rounded-lg border bg-card p-4">
            <h3 className="text-xs font-bold mb-3">Preflight Validation</h3>
            <div className="flex gap-2 mb-3">
              <input type="text" value={preflightSymbol} onChange={e => setPreflightSymbol(e.target.value)}
                placeholder="Symbol" className="flex-1 px-2 py-1.5 rounded border bg-card text-[10px]" />
              <input type="number" value={preflightQty} onChange={e => setPreflightQty(Number(e.target.value))}
                placeholder="Qty" min={1} className="w-20 px-2 py-1.5 rounded border bg-card text-[10px]" />
              <button onClick={() => handleAction("preflight", () =>
                liveExecutionService.runPreflight(preflightSymbol, "BUY", preflightQty, 2500, 2450, 2600)
                  .then(r => setPreflightResult(r))
              )}
                disabled={actionLoading === "preflight"}
                className="px-3 py-1.5 rounded text-[10px] font-medium bg-primary/10 text-primary hover:bg-primary/20 border border-primary/20">
                Run Preflight
              </button>
              <button onClick={() => handleAction("dry_run", () =>
                liveExecutionService.runDryRun(preflightSymbol, "BUY", preflightQty, 2500, 2450, 2600)
                  .then(r => setPreflightResult(r))
              )}
                disabled={actionLoading === "dry_run"}
                className="px-3 py-1.5 rounded text-[10px] font-medium bg-amber-500/10 text-amber-600 hover:bg-amber-500/20 border border-amber-500/20">
                Dry Run
              </button>
            </div>

            {preflightResult && (
              <div>
                <div className="flex items-center gap-2 mb-2">
                  <span className={`text-[10px] font-bold ${preflightResult.passed ? "text-emerald-500" : "text-red-500"}`}>
                    {preflightResult.passed ? "PASSED" : "BLOCKED"}
                  </span>
                  {preflightResult.blockers?.length > 0 && (
                    <span className="text-[10px] text-red-500">{preflightResult.blockers.length} blocker(s)</span>
                  )}
                </div>
                {preflightResult.checks && (
                  <div className="border rounded-lg overflow-hidden">
                    <table className="w-full text-[10px]">
                      <thead><tr className="bg-muted/30 border-b">
                        <th className="text-left px-3 py-2">Check</th>
                        <th className="text-left px-3 py-2">Status</th>
                        <th className="text-left px-3 py-2">Message</th>
                      </tr></thead>
                      <tbody className="divide-y">
                        {Object.entries(preflightResult.checks).map(([key, check]: [string, any]) => (
                          <tr key={key} className="hover:bg-muted/20">
                            <td className="px-3 py-1.5 font-medium">{key.replace(/_/g, " ")}</td>
                            <td className="px-3 py-1.5">
                              <span className={`px-1.5 py-0.5 rounded text-[8px] font-medium ${
                                check.passed ? "bg-emerald-500/10 text-emerald-500" : "bg-red-500/10 text-red-500"
                              }`}>{check.passed ? "PASS" : "FAIL"}</span>
                            </td>
                            <td className="px-3 py-1.5 text-muted-foreground">{check.message || "—"}</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                )}
              </div>
            )}
          </div>
        </div>
      )}

      {/* Canary Tab */}
      {activeTab === "canary" && (
        <div className="space-y-4">
          <div className="rounded-lg border bg-card p-4">
            <h3 className="text-xs font-bold mb-3 flex items-center gap-2">
              <BugPlay className="w-3.5 h-3.5" /> Canary Mode
            </h3>
            <div className="flex items-center gap-2 mb-3">
              <span className={`text-[10px] font-bold px-2 py-1 rounded ${
                canaryStatus?.armed ? "bg-emerald-500/10 text-emerald-500" : "bg-muted/20 text-muted-foreground"
              }`}>
                {canaryStatus?.armed ? "● ARMED" : "○ DISARMED"}
              </span>
            </div>

            <div className="flex gap-2 mb-3">
              {!canaryStatus?.armed && (
                <button onClick={() => setShowConfirm("canary_arm")}
                  className="px-3 py-1.5 rounded text-[10px] font-medium bg-emerald-500/10 text-emerald-600 hover:bg-emerald-500/20 border border-emerald-500/20">
                  <Play className="w-3 h-3 inline mr-1" /> Arm Canary
                </button>
              )}
              {canaryStatus?.armed && (
                <button onClick={() => handleAction("disarm", () => liveExecutionService.disarmCanary())}
                  className="px-3 py-1.5 rounded text-[10px] font-medium bg-red-500/10 text-red-600 hover:bg-red-500/20 border border-red-500/20">
                  <Ban className="w-3 h-3 inline mr-1" /> Disarm Canary
                </button>
              )}
            </div>

            {showConfirm === "canary_arm" && (
              <div className="space-y-2 mb-3 p-3 rounded border bg-card">
                <input type="text" placeholder="Reviewer identity" value={reviewerInput}
                  onChange={e => setReviewerInput(e.target.value)}
                  className="w-full px-2 py-1.5 rounded border bg-card text-[10px]" />
                <input type="text" placeholder="Reason for arming canary" value={reasonInput}
                  onChange={e => setReasonInput(e.target.value)}
                  className="w-full px-2 py-1.5 rounded border bg-card text-[10px]" />
                <div className="text-[9px] text-amber-600 p-2 rounded bg-amber-500/5 border border-amber-500/20">
                  I understand that Canary Mode may submit real broker orders within the configured strict limits.
                </div>
                <div className="flex gap-2">
                  <button onClick={() => setShowConfirm(null)}
                    className="px-3 py-1 rounded text-[10px] font-medium border bg-card">Cancel</button>
                  <button onClick={() => handleAction("arm", () =>
                    liveExecutionService.armCanary(reviewerInput, reasonInput)
                  )}
                    className="px-3 py-1 rounded text-[10px] font-medium bg-emerald-600 text-white">Confirm Arm</button>
                </div>
              </div>
            )}

            {canaryStatus?.config && (
              <div className="grid grid-cols-2 gap-2 text-[10px]">
                <div className="flex justify-between p-1.5 rounded bg-muted/20">
                  <span className="text-muted-foreground">Max Trades:</span>
                  <span className="font-mono">{canaryStatus.config.max_trades}</span>
                </div>
                <div className="flex justify-between p-1.5 rounded bg-muted/20">
                  <span className="text-muted-foreground">Max Quantity:</span>
                  <span className="font-mono">{canaryStatus.config.max_quantity}</span>
                </div>
                <div className="flex justify-between p-1.5 rounded bg-muted/20">
                  <span className="text-muted-foreground">Max Notional:</span>
                  <span className="font-mono">{canaryStatus.config.max_notional}</span>
                </div>
                <div className="flex justify-between p-1.5 rounded bg-muted/20">
                  <span className="text-muted-foreground">Max Loss/Day:</span>
                  <span className="font-mono">{canaryStatus.config.max_daily_loss}</span>
                </div>
              </div>
            )}

            {canaryStatus?.current_state && (
              <div className="mt-3 grid grid-cols-3 gap-2">
                <MetricCard label="Trades Remaining" value={String(canaryStatus.current_state.trades_remaining)} />
                <MetricCard label="Loss Remaining" value={String(canaryStatus.current_state.loss_remaining)} />
                <MetricCard label="Trade Count" value={String(canaryStatus.current_state.canary_trade_count)} />
              </div>
            )}
          </div>
        </div>
      )}

      {/* Orders Tab */}
      {activeTab === "orders" && (
        <div className="space-y-2">
          {orders?.executions?.length === 0 ? (
            <div className="p-8 text-center text-[10px] text-muted-foreground">No executions yet.</div>
          ) : (
            <div className="border rounded-lg overflow-hidden">
              <table className="w-full text-[10px]">
                <thead><tr className="bg-muted/30 border-b">
                  <th className="text-left px-3 py-2">ID</th>
                  <th className="text-left px-3 py-2">Symbol</th>
                  <th className="text-left px-3 py-2">Side</th>
                  <th className="text-left px-3 py-2">Qty</th>
                  <th className="text-left px-3 py-2">Status</th>
                  <th className="text-left px-3 py-2">Broker ID</th>
                </tr></thead>
                <tbody className="divide-y">
                  {(orders?.executions || []).map((e: any, i: number) => (
                    <tr key={e.execution_id || i} className="hover:bg-muted/20">
                      <td className="px-3 py-1.5 font-mono text-[8px]">{e.execution_id?.slice(0, 12)}</td>
                      <td className="px-3 py-1.5">{e.symbol || "—"}</td>
                      <td className="px-3 py-1.5">{e.side || "—"}</td>
                      <td className="px-3 py-1.5">{e.quantity || "—"}</td>
                      <td className="px-3 py-1.5">
                        <span className={`px-1.5 py-0.5 rounded text-[8px] font-medium ${
                          e.success ? "bg-emerald-500/10 text-emerald-500" :
                          e.blockers?.length > 0 ? "bg-red-500/10 text-red-500" : "bg-muted/20 text-muted-foreground"
                        }`}>{e.status || "—"}</span>
                      </td>
                      <td className="px-3 py-1.5 font-mono text-[8px]">{e.broker_order_id?.slice(0, 12) || "—"}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      )}

      {/* Positions Tab */}
      {activeTab === "positions" && (
        <div className="rounded-lg border bg-card p-4">
          <h3 className="text-xs font-bold mb-3">Position Reconciliation</h3>
          <div className="text-[10px] space-y-2">
            <div className="flex justify-between p-1.5 rounded bg-muted/20">
              <span className="text-muted-foreground">Blocked:</span>
              <span className={positions?.blocked ? "text-red-500 font-bold" : "text-emerald-500"}>
                {positions?.blocked ? "YES" : "NO"}
              </span>
            </div>
            <div className="flex justify-between p-1.5 rounded bg-muted/20">
              <span className="text-muted-foreground">Results:</span>
              <span>{positions?.results?.length || 0}</span>
            </div>
            <button onClick={() => handleAction("reconcile", () => liveExecutionService.reconcile())}
              className="px-3 py-1.5 rounded text-[10px] font-medium bg-primary/10 text-primary hover:bg-primary/20 border border-primary/20 mt-2">
              Run Reconciliation
            </button>
          </div>
        </div>
      )}

      {/* Safety Tab */}
      {activeTab === "safety" && (
        <div className="space-y-4">
          <div className="rounded-lg border bg-card p-4">
            <h3 className="text-xs font-bold mb-3">Execution Limits</h3>
            {limits?.limits ? (
              <div className="grid grid-cols-3 gap-2 text-[10px]">
                {Object.entries(limits.limits).map(([key, val]: [string, any]) => (
                  <div key={key} className="flex justify-between p-1.5 rounded bg-muted/20">
                    <span className="text-muted-foreground capitalize">{key.replace(/_/g, " ")}:</span>
                    <span className="font-mono">{String(val)}</span>
                  </div>
                ))}
              </div>
            ) : (
              <div className="text-[10px] text-muted-foreground">No limit data</div>
            )}
          </div>

          <div className="rounded-lg border bg-card p-4">
            <h3 className="text-xs font-bold mb-3">Emergency Controls</h3>
            <button onClick={() => setShowConfirm("emergency_cancel")}
              className="px-3 py-1.5 rounded text-[10px] font-medium bg-red-500/10 text-red-600 hover:bg-red-500/20 border border-red-500/20">
              <Siren className="w-3 h-3 inline mr-1" /> Emergency Cancel All Orders
            </button>
          </div>

          {showConfirm === "emergency_cancel" && (
            <ConfirmationDialog action="emergency_cancel"
              onConfirm={() => handleAction("emergency_cancel", () => liveExecutionService.emergencyCancel("manual_emergency"))}
              onCancel={() => setShowConfirm(null)} />
          )}
        </div>
      )}

      {/* Audit Tab */}
      {activeTab === "audit" && (
        <div className="rounded-lg border bg-card p-4">
          <h3 className="text-xs font-bold mb-3">Audit Events</h3>
          <div className="text-[10px] text-muted-foreground">
            Audit events are logged through the ExecutionAuditLog system.
          </div>
          <button onClick={() => fetchAll()}
            className="px-3 py-1.5 rounded text-[10px] font-medium bg-primary/10 text-primary hover:bg-primary/20 border border-primary/20 mt-2">
            Refresh
          </button>
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
