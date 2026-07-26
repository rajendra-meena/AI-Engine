"use client"

import { useState, useEffect, useCallback } from "react"
import {
  Shield, Activity, AlertTriangle, CheckCircle,
  RefreshCw, Lock, Play, Zap, Clock, Siren,
  PauseOctagon, RotateCcw,
  Timer, Ban,
} from "lucide-react"
import { liveActivationService } from "@/services/liveActivationService"

type TabId = "overview" | "prerequisites" | "history"

export function LiveActivationCenter() {
  const [activeTab, setActiveTab] = useState<TabId>("overview")
  const [status, setStatus] = useState<any>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [actionLoading, setActionLoading] = useState<string | null>(null)
  const [showConfirm, setShowConfirm] = useState<string | null>(null)
  const [reviewerInput, setReviewerInput] = useState("")
  const [reasonInput, setReasonInput] = useState("")
  const [durationInput, setDurationInput] = useState(30)
  const [tokenInput, setTokenInput] = useState("")
  const [history, setHistory] = useState<any[]>([])
  const [countdown, setCountdown] = useState(0)

  const fetchAll = useCallback(async () => {
    setError(null)
    try {
      const [s, h] = await Promise.all([
        liveActivationService.getStatus().catch(() => null),
        liveActivationService.getHistory(5).catch(() => null),
      ])
      if (s) {
        setStatus(s)
        setCountdown(s.remaining_seconds || 0)
      }
      if (h) setHistory(h.history || [])
    } catch {
      setError("Failed to load activation data")
    }
    setLoading(false)
  }, [])

  useEffect(() => {
    const t = setTimeout(() => fetchAll(), 0)
    const interval = setInterval(fetchAll, 15000)
    return () => { clearTimeout(t); clearInterval(interval) }
  }, [fetchAll])

  // Countdown timer when ACTIVE
  useEffect(() => {
    if (status?.state !== "active") return
    const timer = setInterval(() => {
      setCountdown(prev => Math.max(0, prev - 1))
    }, 1000)
    return () => clearInterval(timer)
  }, [status?.state])

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

  const stateColor = status?.state === "active" ? "text-emerald-500"
    : status?.state === "armed" ? "text-amber-500"
    : status?.state === "ready" ? "text-blue-500"
    : status?.state === "paused" ? "text-yellow-500"
    : status?.state === "kill_switched" || status?.state === "revoked" ? "text-red-500"
    : status?.state === "expired" ? "text-muted-foreground"
    : "text-muted-foreground"

  const tabs = [
    { id: "overview" as TabId, label: "Overview", icon: <Activity className="w-3.5 h-3.5" /> },
    { id: "prerequisites" as TabId, label: "Prerequisites", icon: <Shield className="w-3.5 h-3.5" /> },
    { id: "history" as TabId, label: "History", icon: <Clock className="w-3.5 h-3.5" /> },
  ]

  // Format countdown
  const formatTime = (seconds: number) => {
    const m = Math.floor(seconds / 60)
    const s = seconds % 60
    return `${m}:${s.toString().padStart(2, "0")}`
  }

  return (
    <div className="space-y-4">
      {/* Header */}
      <div className="flex items-center gap-2">
        <Zap className="w-5 h-5 text-primary" />
        <h1 className="text-lg font-bold">Live Activation</h1>
        <span className="px-2 py-0.5 rounded text-[8px] font-bold bg-amber-500/10 text-amber-600 border border-amber-500/20">
          PHASE 45
        </span>
        <button onClick={fetchAll} className="ml-auto p-1 rounded text-muted-foreground hover:text-foreground hover:bg-accent" disabled={loading}>
          <RefreshCw className={`w-3.5 h-3.5 ${loading ? "animate-spin" : ""}`} />
        </button>
      </div>

      {/* State Banner */}
      <div className={`p-3 rounded-lg border text-center ${
        status?.state === "active" ? "border-emerald-500/30 bg-emerald-500/10" :
        status?.state === "armed" ? "border-amber-500/30 bg-amber-500/10" :
        status?.state === "ready" ? "border-blue-500/30 bg-blue-500/10" :
        status?.state === "kill_switched" ? "border-red-500/30 bg-red-500/10" :
        status?.state === "revoked" ? "border-red-500/30 bg-red-500/10" :
        status?.state === "expired" ? "border-muted/30 bg-muted/10" :
        "border-muted/30 bg-muted/10"
      }`}>
        <div className={`text-lg font-bold ${stateColor}`}>
          {status?.state ? status.state.toUpperCase().replace(/_/g, " ") : "NOT INITIALIZED"}
        </div>
        {status?.state === "active" && countdown > 0 && (
          <div className="text-[10px] text-muted-foreground mt-1">
            Remaining: <span className="font-mono font-bold">{formatTime(countdown)}</span>
          </div>
        )}
      </div>

      {/* Status Bar */}
      <div className="flex items-center gap-2 p-2 rounded-lg border bg-card text-[10px] flex-wrap">
        <span className="flex items-center gap-1">
          <Lock className="w-3 h-3" />
          <span>Phase 43 Lock: <strong className="text-amber-500">ACTIVE</strong></span>
        </span>
        <span className="text-muted-foreground">|</span>
        <span>Live: <strong className={status?.is_live_armed ? "text-emerald-500" : "text-red-500"}>
          {status?.is_live_armed ? "ARMED" : "LOCKED"}
        </strong></span>
        <span className="text-muted-foreground">|</span>
        <span>Orders: {status?.total_orders_placed || 0} placed / {status?.total_orders_blocked || 0} blocked</span>
        {status?.state === "active" && (
          <>
            <span className="text-muted-foreground">|</span>
            <span className="flex items-center gap-1">
              <Timer className="w-3 h-3" />
              <span className="font-mono">{formatTime(countdown)}</span>
            </span>
          </>
        )}
      </div>

      {error && <div className="rounded border border-red-500/20 bg-red-500/5 p-2 text-[10px] text-red-600">{error}</div>}

      {/* Phase banner */}
      <div className="rounded-lg border border-amber-500/20 bg-amber-500/5 p-3 text-[10px] text-amber-700">
        <strong>Phase 45 — Controlled Live Activation Gate.</strong>{' '}
        The system validates 28 prerequisites before allowing activation.
        LIVE auto trading remains disabled. PHASE_43_LIVE_EXECUTION_LOCK remains active.
      </div>

      {/* Action Buttons */}
      <div className="flex gap-2 flex-wrap">
        {/* Validate */}
        {(status?.state === "locked" || status?.state === "ready") && (
          <button onClick={() => handleAction("validate",
            () => liveActivationService.validate(reviewerInput, reasonInput))}
            disabled={actionLoading === "validate"}
            className="px-3 py-1.5 rounded text-[10px] font-medium bg-primary/10 text-primary hover:bg-primary/20 border border-primary/20">
            <CheckCircle className="w-3 h-3 inline mr-1" /> Validate Prerequisites
          </button>
        )}

        {/* Arm */}
        {(status?.state === "ready") && (
          <button onClick={() => setShowConfirm("arm")}
            className="px-3 py-1.5 rounded text-[10px] font-medium bg-amber-500/10 text-amber-600 hover:bg-amber-500/20 border border-amber-500/20">
            <Shield className="w-3 h-3 inline mr-1" /> Arm LIVE
          </button>
        )}

        {/* Start */}
        {(status?.state === "armed") && (
          <button onClick={() => setShowConfirm("start")}
            className="px-3 py-1.5 rounded text-[10px] font-medium bg-emerald-500/10 text-emerald-600 hover:bg-emerald-500/20 border border-emerald-500/20">
            <Play className="w-3 h-3 inline mr-1" /> Start LIVE
          </button>
        )}

        {/* Pause */}
        {status?.state === "active" && (
          <button onClick={() => handleAction("pause",
            () => liveActivationService.pause("Manual pause"))}
            disabled={actionLoading === "pause"}
            className="px-3 py-1.5 rounded text-[10px] font-medium bg-yellow-500/10 text-yellow-600 hover:bg-yellow-500/20 border border-yellow-500/20">
            <PauseOctagon className="w-3 h-3 inline mr-1" /> Pause New Orders
          </button>
        )}

        {/* Resume */}
        {status?.state === "paused" && (
          <button onClick={() => handleAction("resume",
            () => liveActivationService.start(tokenInput))}
            disabled={actionLoading === "resume"}
            className="px-3 py-1.5 rounded text-[10px] font-medium bg-emerald-500/10 text-emerald-600 hover:bg-emerald-500/20 border border-emerald-500/20">
            <RotateCcw className="w-3 h-3 inline mr-1" /> Resume
          </button>
        )}

        {/* Kill Switch */}
        {(status?.state === "active" || status?.state === "paused") && (
          <button onClick={() => setShowConfirm("kill_switch")}
            className="px-3 py-1.5 rounded text-[10px] font-medium bg-red-500/10 text-red-600 hover:bg-red-500/20 border border-red-500/20">
            <Siren className="w-3 h-3 inline mr-1" /> Kill Switch
          </button>
        )}

        {/* Revoke */}
        {(status?.state === "armed" || status?.state === "active" || status?.state === "paused") && (
          <button onClick={() => setShowConfirm("revoke")}
            className="px-3 py-1.5 rounded text-[10px] font-medium bg-red-500/10 text-red-600 hover:bg-red-500/20 border border-red-500/20">
            <Ban className="w-3 h-3 inline mr-1" /> Revoke Activation
          </button>
        )}

        {/* Recover */}
        {(status?.state === "kill_switched" || status?.state === "expired" || status?.state === "revoked") && (
          <button onClick={() => setShowConfirm("recover")}
            className="px-3 py-1.5 rounded text-[10px] font-medium bg-blue-500/10 text-blue-600 hover:bg-blue-500/20 border border-blue-500/20">
            <RotateCcw className="w-3 h-3 inline mr-1" /> Recover
          </button>
        )}
      </div>

      {/* Input Section (shown when needed) */}
      {(showConfirm === "arm" || showConfirm === "start" || showConfirm === "recover") && (
        <div className="rounded-lg border bg-card p-4 space-y-2">
          <h3 className="text-xs font-bold">
            {showConfirm === "arm" && "Arm LIVE — Enter Details"}
            {showConfirm === "start" && "Start Activation — Enter Token"}
            {showConfirm === "recover" && "Recovery — Enter Reviewer"}
          </h3>
          {showConfirm === "arm" && (
            <>
              <input type="text" placeholder="Reviewer identity" value={reviewerInput}
                onChange={e => setReviewerInput(e.target.value)}
                className="w-full px-2 py-1.5 rounded border bg-card text-[10px]" />
              <input type="text" placeholder="Reason for activation" value={reasonInput}
                onChange={e => setReasonInput(e.target.value)}
                className="w-full px-2 py-1.5 rounded border bg-card text-[10px]" />
              <div className="flex items-center gap-2">
                <span className="text-[9px] text-muted-foreground">Duration (min):</span>
                <input type="number" value={durationInput}
                  onChange={e => setDurationInput(Number(e.target.value))}
                  min={5} max={60}
                  className="w-20 px-2 py-1 rounded border bg-card text-[10px]" />
              </div>
            </>
          )}
          {showConfirm === "start" && (
            <input type="text" placeholder="Confirmation token from /arm" value={tokenInput}
              onChange={e => setTokenInput(e.target.value)}
              className="w-full px-2 py-1.5 rounded border bg-card text-[10px]" />
          )}
          {showConfirm === "recover" && (
            <input type="text" placeholder="Reviewer identity" value={reviewerInput}
              onChange={e => setReviewerInput(e.target.value)}
              className="w-full px-2 py-1.5 rounded border bg-card text-[10px]" />
          )}
        </div>
      )}

      {/* Confirmation Dialog */}
      {showConfirm && showConfirm !== "arm" && showConfirm !== "start" && showConfirm !== "recover" && (
        <ConfirmationDialog
          action={showConfirm}
          onConfirm={() => handleAction(showConfirm, async () => {
            if (showConfirm === "kill_switch") return liveActivationService.killSwitch(reasonInput || "Manual kill switch")
            if (showConfirm === "revoke") return liveActivationService.revoke(reasonInput || "Manual revoke")
            return null
          })}
          onCancel={() => setShowConfirm(null)}
        />
      )}

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
          {/* Key Metrics */}
          <div className="grid grid-cols-4 gap-3">
            <MetricCard label="Activation State" value={status?.state?.replace(/_/g, " ") || "—"} color={stateColor} />
            <MetricCard label="Prerequisites" value={status ? `${status.prerequisites_passed}/${status.prerequisites_total}` : "—"}
              color={status?.prerequisites_passed === status?.prerequisites_total ? "text-emerald-500" : "text-amber-500"} />
            <MetricCard label="Live Armed" value={status?.is_live_armed ? "YES" : "NO"}
              color={status?.is_live_armed ? "text-emerald-500" : "text-red-500"} />
            <MetricCard label="Orders (Placed/Blocked)" value={status ? `${status.total_orders_placed}/${status.total_orders_blocked}` : "—"}
              color="text-muted-foreground" />
          </div>

          {/* Activation Info */}
          {status && (
            <div className="rounded-lg border bg-card p-4">
              <h3 className="text-xs font-bold mb-3 flex items-center gap-2">
                <Zap className="w-3.5 h-3.5" /> Activation Details
              </h3>
              <div className="grid grid-cols-2 gap-3 text-[10px]">
                <div className="space-y-1">
                  <div className="flex justify-between p-1.5 rounded bg-muted/20">
                    <span className="text-muted-foreground">Activation ID:</span>
                    <span className="font-mono">{status.activation_id}</span>
                  </div>
                  <div className="flex justify-between p-1.5 rounded bg-muted/20">
                    <span className="text-muted-foreground">Reviewer:</span>
                    <span>{status.reviewer || "—"}</span>
                  </div>
                  <div className="flex justify-between p-1.5 rounded bg-muted/20">
                    <span className="text-muted-foreground">Reason:</span>
                    <span className="max-w-[200px] truncate">{status.reason || "—"}</span>
                  </div>
                </div>
                <div className="space-y-1">
                  <div className="flex justify-between p-1.5 rounded bg-muted/20">
                    <span className="text-muted-foreground">Activated At:</span>
                    <span>{status.activated_at ? new Date(status.activated_at).toLocaleString() : "—"}</span>
                  </div>
                  <div className="flex justify-between p-1.5 rounded bg-muted/20">
                    <span className="text-muted-foreground">Expires At:</span>
                    <span>{status.expires_at ? new Date(status.expires_at).toLocaleString() : "—"}</span>
                  </div>
                  <div className="flex justify-between p-1.5 rounded bg-muted/20">
                    <span className="text-muted-foreground">Duration:</span>
                    <span>{status.activation_duration_minutes} min</span>
                  </div>
                </div>
              </div>
            </div>
          )}

          {/* Execution Lock */}
          <div className="rounded-lg border bg-card p-4">
            <h3 className="text-xs font-bold mb-3 flex items-center gap-2">
              <Lock className="w-3.5 h-3.5" /> Live Auto Trading
            </h3>
            <div className="p-4 rounded bg-amber-500/5 border border-amber-500/20 text-center">
              <div className="text-2xl font-bold text-amber-500 mb-1">🔒 DISABLED</div>
              <div className="text-[10px] text-muted-foreground">
                Phase 43 execution lock is active.{' '}
                PHASE_43_LIVE_EXECUTION_LOCK remains TRUE.
                <br />
                <strong>Activation Gate must pass 28 prerequisites + human arm to authorize.</strong>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Prerequisites Tab */}
      {activeTab === "prerequisites" && (
        <div className="space-y-2">
          <button onClick={() => handleAction("validate",
            () => liveActivationService.validate(reviewerInput, reasonInput))}
            disabled={actionLoading === "validate"}
            className="px-3 py-1.5 rounded text-[10px] font-medium bg-primary/10 text-primary hover:bg-primary/20 border border-primary/20 mb-2">
            <RefreshCw className={`w-3 h-3 inline mr-1 ${actionLoading === "validate" ? "animate-spin" : ""}`} />
            Run Prerequisite Check
          </button>
          <div className="border rounded-lg overflow-hidden">
            <table className="w-full text-[10px]">
              <thead>
                <tr className="bg-muted/30 border-b">
                  <th className="text-left px-3 py-2">Check</th>
                  <th className="text-left px-3 py-2">Category</th>
                  <th className="text-left px-3 py-2">Name</th>
                  <th className="text-left px-3 py-2">Status</th>
                  <th className="text-left px-3 py-2">Message</th>
                </tr>
              </thead>
              <tbody className="divide-y">
                {(!status?.prerequisites || status.prerequisites.length === 0) ? (
                  <tr><td colSpan={5} className="px-3 py-4 text-center text-muted-foreground">
                    No prerequisites loaded. Click &ldquo;Run Prerequisite Check&rdquo;.
                  </td></tr>
                ) : (
                  /* Will use fetchAll to get fresh data */
                  <tr><td colSpan={5} className="px-3 py-4 text-center text-[9px] text-muted-foreground">
                    Run validation to see full 28-check results.
                  </td></tr>
                )}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* History Tab */}
      {activeTab === "history" && (
        <div className="space-y-2">
          {history.length === 0 ? (
            <div className="p-8 text-center text-[10px] text-muted-foreground">No activation history.</div>
          ) : (
            <div className="border rounded-lg overflow-hidden">
              <table className="w-full text-[10px]">
                <thead>
                  <tr className="bg-muted/30 border-b">
                    <th className="text-left px-3 py-2">ID</th>
                    <th className="text-left px-3 py-2">State</th>
                    <th className="text-left px-3 py-2">Reviewer</th>
                    <th className="text-left px-3 py-2">Reason</th>
                    <th className="text-left px-3 py-2">Created</th>
                    <th className="text-left px-3 py-2">Activated</th>
                  </tr>
                </thead>
                <tbody className="divide-y">
                  {history.map((h: any, i: number) => (
                    <tr key={i} className="hover:bg-muted/20">
                      <td className="px-3 py-1.5 font-mono">{h.activation_id}</td>
                      <td className="px-3 py-1.5 capitalize">{h.state?.replace(/_/g, " ")}</td>
                      <td className="px-3 py-1.5">{h.reviewer || "—"}</td>
                      <td className="px-3 py-1.5 max-w-[200px] truncate">{h.reason || "—"}</td>
                      <td className="px-3 py-1.5">{h.created_at ? new Date(h.created_at).toLocaleString() : "—"}</td>
                      <td className="px-3 py-1.5">{h.activated_at ? new Date(h.activated_at).toLocaleString() : "—"}</td>
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

function ConfirmationDialog({ action, onConfirm, onCancel }: {
  action: string; onConfirm: () => void; onCancel: () => void
}) {
  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
      <div className="rounded-lg border bg-card p-6 max-w-md mx-4 shadow-xl">
        <div className="flex items-center gap-2 mb-3">
          {action === "kill_switch" ? (
            <Siren className="w-5 h-5 text-red-500" />
          ) : (
            <AlertTriangle className="w-5 h-5 text-amber-500" />
          )}
          <h3 className="text-sm font-bold">
            {action === "kill_switch" ? "KILL SWITCH" : action.toUpperCase()}
          </h3>
        </div>
        <p className="text-[10px] text-muted-foreground mb-4">
          {action === "arm" && "This will arm the system for live activation. All 28 prerequisites must pass."}
          {action === "start" && "This will begin the activation window. Live orders will be authorized."}
          {action === "kill_switch" && "This EMERGENCY STOP blocks all new live orders immediately. Requires explicit recovery."}
          {action === "revoke" && "This revokes the current activation. Requires fresh validation to re-activate."}
          {action === "recover" && "This begins recovery from a terminal state. Complete re-validation required for activation."}
        </p>
        <div className="flex gap-2 justify-end">
          <button onClick={onCancel}
            className="px-3 py-1.5 rounded text-[10px] font-medium border bg-card hover:bg-accent">
            Cancel
          </button>
          <button onClick={onConfirm}
            className={`px-3 py-1.5 rounded text-[10px] font-medium text-white ${
              action === "kill_switch" ? "bg-red-600 hover:bg-red-700" : "bg-amber-600 hover:bg-amber-700"
            }`}>
            Confirm {action.replace(/_/g, " ")}
          </button>
        </div>
      </div>
    </div>
  )
}
