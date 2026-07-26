"use client"

import { useState, useEffect, useCallback, useRef } from "react"
import {
  Shield, Activity, AlertTriangle, CheckCircle, XCircle, BarChart3,
  RefreshCw, Lock, Zap, Radio, TrendingUp, Clock, Siren,
  BugPlay, Shuffle, UserCheck, Timer, Ban, Server, Wifi,
  Target, DollarSign, PieChart, List, ExternalLink,
} from "lucide-react"
import { commandCenterService } from "@/services/commandCenterService"

type RefreshRate = 5 | 10 | 30 | 60 | 0

export function CommandCenter() {
  const [snapshot, setSnapshot] = useState<any>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [refreshRate, setRefreshRate] = useState<RefreshRate>(5)
  const [lastUpdated, setLastUpdated] = useState<string>("")
  const [dataAge, setDataAge] = useState(0)
  const abortRef = useRef<AbortController | null>(null)
  const timerRef = useRef<NodeJS.Timeout | null>(null)

  const fetchSnapshot = useCallback(async () => {
    // Cancel any in-flight request
    if (abortRef.current) abortRef.current.abort()
    const controller = new AbortController()
    abortRef.current = controller

    setError(null)
    try {
      const res = await fetch(
        `${process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"}/api/operations/command-center`,
        { signal: controller.signal },
      )
      if (!res.ok) throw new Error(`HTTP ${res.status}`)
      const data = await res.json()
      setSnapshot(data)
      setLastUpdated(data.timestamp || new Date().toISOString())
      setDataAge(0)
    } catch (e: any) {
      if (e.name === "AbortError") return
      setError(e.message || "Failed to fetch")
    }
    setLoading(false)
  }, [])

  // Age counter
  useEffect(() => {
    const interval = setInterval(() => {
      setDataAge(prev => prev + 1)
    }, 1000)
    return () => clearInterval(interval)
  }, [])

  // Polling
  useEffect(() => {
    const t = setTimeout(() => fetchSnapshot(), 0)
    if (refreshRate > 0) {
      timerRef.current = setInterval(fetchSnapshot, refreshRate * 1000)
    }
    return () => {
      clearTimeout(t)
      if (timerRef.current) clearInterval(timerRef.current)
      if (abortRef.current) abortRef.current.abort()
    }
  }, [fetchSnapshot, refreshRate])

  const statusColor = snapshot?.unified_status === "healthy" ? "text-emerald-500"
    : snapshot?.unified_status === "degraded" ? "text-amber-500"
    : snapshot?.unified_status === "trading_blocked" || snapshot?.unified_status === "incident_active" ? "text-red-500"
    : snapshot?.unified_status === "recovery_required" || snapshot?.unified_status === "rollback_active" ? "text-red-600"
    : snapshot?.unified_status === "halted" ? "text-red-700"
    : "text-muted-foreground"

  const isStale = dataAge > 15
  const isWarning = dataAge > 5 && dataAge <= 15
  const isFresh = dataAge <= 5

  const blockReasons: string[] = []
  if (snapshot?.market?.stale) blockReasons.push("Market data is stale")
  if (snapshot?.broker?.connected === false) blockReasons.push("Broker is disconnected")
  if (snapshot?.risk?.risk_blocked) blockReasons.push("Risk engine has blocked trading")
  if (snapshot?.safety?.kill_switch) blockReasons.push("Kill switch is active")
  if (snapshot?.reconciliation?.mismatches > 0) blockReasons.push("Reconciliation mismatches exist")
  if (snapshot?.recovery?.recovery_required) blockReasons.push("System recovery is required")
  if (snapshot?.integrity?.integrity_status === "failure") blockReasons.push("Configuration integrity failure")
  if (snapshot?.rollout?.rollback_active) blockReasons.push("Rollback is active")

  return (
    <div className="space-y-4">
      {/* ── Header ── */}
      <div className="flex items-center gap-2">
        <Activity className="w-5 h-5 text-primary" />
        <h1 className="text-lg font-bold">Command Center</h1>
        <span className={`px-2 py-0.5 rounded text-[8px] font-bold ${
          statusColor.replace("text-", "bg-").replace("500", "500/10 text-").replace("600", "600/10 text-").replace("700", "700/10 text-") || "bg-muted/20 text-muted-foreground"
        } border`}>
          PHASE 53
        </span>
        <div className="ml-auto flex items-center gap-2 text-[10px] text-muted-foreground">
          {/* Status indicator */}
          <span className="flex items-center gap-1">
            <span className={`w-2 h-2 rounded-full ${
              isFresh ? "bg-emerald-500" : isWarning ? "bg-amber-500" : "bg-red-500"
            }`} />
            {isFresh ? "Live" : isWarning ? "Stale" : "Unavailable"}
          </span>
          <span>|</span>
          <span>Updated: {dataAge}s ago</span>
          <span>|</span>
          <select value={refreshRate} onChange={e => setRefreshRate(Number(e.target.value) as RefreshRate)}
            className="px-1 py-0.5 rounded border bg-card text-[10px]">
            <option value={5}>5s</option>
            <option value={10}>10s</option>
            <option value={30}>30s</option>
            <option value={60}>60s</option>
            <option value={0}>Manual</option>
          </select>
          <button onClick={fetchSnapshot} disabled={loading}
            className="p-1 rounded hover:bg-accent">
            <RefreshCw className={`w-3.5 h-3.5 ${loading ? "animate-spin" : ""}`} />
          </button>
        </div>
      </div>

      {/* ── Error / Stale Warning ── */}
      {error && (
        <div className="rounded border border-red-500/20 bg-red-500/5 p-2 text-[10px] text-red-600">
          Connection lost: {error}. Last successful update: {lastUpdated ? new Date(lastUpdated).toLocaleTimeString() : "never"}
        </div>
      )}
      {isStale && !error && (
        <div className="rounded border border-amber-500/20 bg-amber-500/5 p-2 text-[10px] text-amber-700">
          ⚠ Snapshot is {dataAge}s old. Data may be stale. Safety state cannot be fully verified.
        </div>
      )}

      {/* ── Safety Banner ── */}
      <div className="rounded-lg border border-amber-500/20 bg-amber-500/5 p-3">
        <div className="flex items-center gap-3 flex-wrap">
          <div className="text-lg">🔒</div>
          <div className="text-[10px] space-y-0.5">
            <div className="font-bold text-amber-700">LIVE EXECUTION LOCKED</div>
            <div className="text-amber-600">
              PHASE_43_LOCK: {snapshot?.safety?.phase43_lock ? "TRUE" : "FALSE"} |
              can_execute_live: {String(snapshot?.safety?.can_execute_live ?? false)} |
              Activation: {snapshot?.safety?.activation_state || "locked"} |
              Auto Resume: DISABLED
            </div>
          </div>
          <div className="ml-auto">
            <span className={`text-[10px] font-bold px-2 py-1 rounded ${
              statusColor.includes("emerald") ? "bg-emerald-500/10 text-emerald-500" :
              statusColor.includes("red") ? "bg-red-500/10 text-red-500" :
              "bg-amber-500/10 text-amber-500"
            }`}>
              {snapshot?.unified_status?.toUpperCase().replace(/_/g, " ") || "LOADING"}
            </span>
          </div>
        </div>
      </div>

      {/* ── Loading State ── */}
      {loading && !snapshot && (
        <div className="p-12 text-center text-[10px] text-muted-foreground">Loading command center data...</div>
      )}

      {/* ── Main Dashboard ── */}
      {snapshot && (
        <>
          {/* ── KPI Cards ── */}
          <div className="grid grid-cols-2 sm:grid-cols-4 lg:grid-cols-8 gap-2">
            <KpiCard label="System" value={snapshot.system?.operational_state || "?"} color={statusColor} />
            <KpiCard label="Market" value={snapshot.market?.stale ? "STALE" : snapshot.market?.connected ? "OK" : "OFF"}
              color={snapshot.market?.stale ? "text-red-500" : snapshot.market?.connected ? "text-emerald-500" : "text-muted-foreground"} />
            <KpiCard label="Broker" value={snapshot.broker?.connected ? "OK" : "OFF"}
              color={snapshot.broker?.connected ? "text-emerald-500" : "text-red-500"} />
            <KpiCard label="Risk" value={snapshot.risk?.risk_blocked ? "BLOCKED" : "OK"}
              color={snapshot.risk?.risk_blocked ? "text-red-500" : "text-emerald-500"} />
            <KpiCard label="Positions" value={String(snapshot.positions?.open_positions || 0)} />
            <KpiCard label="Incidents" value={String(snapshot.incidents?.open_count || 0)}
              color={snapshot.incidents?.critical_count > 0 ? "text-red-500" : snapshot.incidents?.open_count > 0 ? "text-amber-500" : "text-emerald-500"} />
            <KpiCard label="Canary" value={snapshot.canary?.active ? "ACTIVE" : "IDLE"}
              color={snapshot.canary?.active ? "text-blue-500" : "text-muted-foreground"} />
            <KpiCard label="Rollout" value={snapshot.rollout?.current_stage || "locked"}
              color={snapshot.rollout?.rollback_active ? "text-red-500" : "text-emerald-500"} />
          </div>

          {/* ── Trading Block Reason ── */}
          {Array.isArray(blockReasons) && blockReasons.length > 0 && (
            <div className="rounded-lg border border-red-500/20 bg-red-500/5 p-3">
              <h3 className="text-xs font-bold mb-2 flex items-center gap-2 text-red-600">
                <Ban className="w-3.5 h-3.5" /> TRADING BLOCKED
              </h3>
              <ul className="space-y-1 text-[10px]">
                {blockReasons.map((reason, i) => (
                  <li key={i} className="flex items-center gap-1.5 text-red-600">
                    <XCircle className="w-3 h-3 shrink-0" /> {reason}
                  </li>
                ))}
              </ul>
            </div>
          )}

          {/* ── 3-Column Grid ── */}
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">

            {/* System Health */}
            <SectionCard icon={<Server className="w-3.5 h-3.5" />} title="System Health">
              <div className="space-y-1.5 text-[10px]">
                <Row label="Status" value={snapshot.system?.operational_state || "?"}
                  color={statusColor} />
                <Row label="Health Score" value={snapshot.system?.health_score != null ? `${snapshot.system.health_score}%` : "?"} />
                <Row label="Uptime" value={snapshot.metrics?.uptime_hours ? `${snapshot.metrics.uptime_hours.toFixed(1)}h` : "?"} />
                <Row label="Degraded" value={snapshot.system?.degraded ? "YES" : "NO"}
                  color={snapshot.system?.degraded ? "text-amber-500" : "text-emerald-500"} />
                <Row label="Trading Blocked" value={snapshot.system?.trading_blocked ? "YES" : "NO"}
                  color={snapshot.system?.trading_blocked ? "text-red-500" : "text-emerald-500"} />
              </div>
            </SectionCard>

            {/* Safety */}
            <SectionCard icon={<Lock className="w-3.5 h-3.5" />} title="Safety">
              <div className="space-y-1.5 text-[10px]">
                <Row label="Phase 43 Lock" value={snapshot.safety?.phase43_lock ? "ACTIVE" : "INACTIVE"}
                  color={snapshot.safety?.phase43_lock ? "text-amber-500" : "text-red-500"} />
                <Row label="can_execute_live" value={String(snapshot.safety?.can_execute_live ?? false)}
                  color={snapshot.safety?.can_execute_live ? "text-red-500" : "text-emerald-500"} />
                <Row label="Activation Gate" value={snapshot.safety?.activation_state || "?"}
                  color={snapshot.safety?.activation_state === "locked" ? "text-emerald-500" : "text-amber-500"} />
                <Row label="Kill Switch" value={snapshot.safety?.kill_switch ? "ACTIVE" : "CLEAR"}
                  color={snapshot.safety?.kill_switch ? "text-red-500" : "text-emerald-500"} />
                <Row label="Auto Resume" value="DISABLED" color="text-emerald-500" />
              </div>
            </SectionCard>

            {/* Market Data */}
            <SectionCard icon={<Wifi className="w-3.5 h-3.5" />} title="Market Data">
              <div className="space-y-1.5 text-[10px]">
                <Row label="Connected" value={snapshot.market?.connected ? "YES" : "NO"}
                  color={snapshot.market?.connected ? "text-emerald-500" : "text-red-500"} />
                <Row label="Data Quality" value={snapshot.market?.data_quality || "?"} />
                <Row label="Tick Age" value={snapshot.market?.tick_age_ms != null ? `${snapshot.market.tick_age_ms.toFixed(0)}ms` : "?"} />
                <Row label="Stale" value={snapshot.market?.stale ? "YES" : "NO"}
                  color={snapshot.market?.stale ? "text-red-500" : "text-emerald-500"} />
              </div>
            </SectionCard>

            {/* Broker Health */}
            <SectionCard icon={<Radio className="w-3.5 h-3.5" />} title="Broker">
              <div className="space-y-1.5 text-[10px]">
                <Row label="Connected" value={snapshot.broker?.connected ? "YES" : "NO"}
                  color={snapshot.broker?.connected ? "text-emerald-500" : "text-red-500"} />
                <Row label="Authenticated" value={snapshot.broker?.authenticated ? "YES" : "NO"}
                  color={snapshot.broker?.authenticated ? "text-emerald-500" : "text-red-500"} />
                <Row label="Session Valid" value={snapshot.broker?.session_valid ? "YES" : "NO"}
                  color={snapshot.broker?.session_valid ? "text-emerald-500" : "text-red-500"} />
                <Row label="API Health" value={snapshot.broker?.api_health || "?"} />
              </div>
            </SectionCard>

            {/* Risk */}
            <SectionCard icon={<Shield className="w-3.5 h-3.5" />} title="Risk">
              <div className="space-y-1.5 text-[10px]">
                <Row label="Engine Available" value={snapshot.risk?.risk_engine_available ? "YES" : "NO"}
                  color={snapshot.risk?.risk_engine_available ? "text-emerald-500" : "text-red-500"} />
                <Row label="Daily Loss" value={snapshot.risk?.daily_loss != null ? `$${snapshot.risk.daily_loss.toFixed(2)}` : "?"} />
                <Row label="Daily Limit" value={snapshot.risk?.daily_loss_limit != null ? `$${snapshot.risk.daily_loss_limit.toFixed(0)}` : "?"} />
                <Row label="Drawdown" value={snapshot.risk?.drawdown_pct != null ? `${snapshot.risk.drawdown_pct.toFixed(1)}%` : "?"} />
                <Row label="Risk Blocked" value={snapshot.risk?.risk_blocked ? "YES" : "NO"}
                  color={snapshot.risk?.risk_blocked ? "text-red-500" : "text-emerald-500"} />
              </div>
            </SectionCard>

            {/* Execution */}
            <SectionCard icon={<Zap className="w-3.5 h-3.5" />} title="Execution">
              <div className="space-y-1.5 text-[10px]">
                <Row label="Health" value={snapshot.execution?.execution_health || "?"} />
                <Row label="Unknown Orders" value={String(snapshot.execution?.unknown_orders || 0)}
                  color={snapshot.execution?.unknown_orders > 0 ? "text-red-500" : "text-emerald-500"} />
                <Row label="Duplicates" value={String(snapshot.execution?.duplicate_attempts || 0)}
                  color={snapshot.execution?.duplicate_attempts > 0 ? "text-amber-500" : "text-emerald-500"} />
                <Row label="Blocked" value={snapshot.execution?.blocked ? "YES" : "NO"}
                  color={snapshot.execution?.blocked ? "text-red-500" : "text-emerald-500"} />
              </div>
            </SectionCard>

            {/* Positions */}
            <SectionCard icon={<DollarSign className="w-3.5 h-3.5" />} title="Positions & P&L">
              <div className="space-y-1.5 text-[10px]">
                <Row label="Open Positions" value={String(snapshot.positions?.open_positions || 0)} />
                <Row label="Exposure" value={snapshot.positions?.total_exposure != null ? `$${snapshot.positions.total_exposure.toFixed(2)}` : "?"} />
                <Row label="Realized P&L" value={snapshot.positions?.realized_pnl != null ? `$${snapshot.positions.realized_pnl.toFixed(2)}` : "?"}
                  color={snapshot.positions?.realized_pnl > 0 ? "text-emerald-500" : snapshot.positions?.realized_pnl < 0 ? "text-red-500" : ""} />
                <Row label="Net P&L" value={snapshot.positions?.net_pnl != null ? `$${snapshot.positions.net_pnl.toFixed(2)}` : "?"}
                  color={snapshot.positions?.net_pnl > 0 ? "text-emerald-500" : snapshot.positions?.net_pnl < 0 ? "text-red-500" : ""} />
              </div>
            </SectionCard>

            {/* Canary */}
            <SectionCard icon={<BugPlay className="w-3.5 h-3.5" />} title="Canary">
              <div className="space-y-1.5 text-[10px]">
                <Row label="Active" value={snapshot.canary?.active ? "YES" : "NO"}
                  color={snapshot.canary?.active ? "text-blue-500" : "text-muted-foreground"} />
                <Row label="Authorization" value={snapshot.canary?.authorization_state || "none"} />
                <Row label="Evaluation" value={snapshot.canary?.evaluation_status || "pending"} />
                {snapshot.canary?.current_canary && (
                  <Row label="ID" value={snapshot.canary.current_canary.slice(0, 16)} />
                )}
              </div>
            </SectionCard>

            {/* Rollout */}
            <SectionCard icon={<TrendingUp className="w-3.5 h-3.5" />} title="Rollout">
              <div className="space-y-1.5 text-[10px]">
                <Row label="Current Stage" value={snapshot.rollout?.current_stage || "locked"} />
                <Row label="Rollback Active" value={snapshot.rollout?.rollback_active ? "YES" : "NO"}
                  color={snapshot.rollout?.rollback_active ? "text-red-500" : "text-emerald-500"} />
                {snapshot.rollout?.rollback_reason && (
                  <Row label="Rollback Reason" value={snapshot.rollout.rollback_reason.slice(0, 60)} color="text-red-500" />
                )}
                <div className="text-[8px] text-muted-foreground mt-1">No automatic progression. Human approval required.</div>
              </div>
            </SectionCard>

            {/* Reconciliation */}
            <SectionCard icon={<Shuffle className="w-3.5 h-3.5" />} title="Reconciliation">
              <div className="space-y-1.5 text-[10px]">
                <Row label="Orders" value={snapshot.reconciliation?.orders_ok ? "MATCHED" : "MISMATCH"}
                  color={snapshot.reconciliation?.orders_ok ? "text-emerald-500" : "text-red-500"} />
                <Row label="Positions" value={snapshot.reconciliation?.positions_ok ? "MATCHED" : "MISMATCH"}
                  color={snapshot.reconciliation?.positions_ok ? "text-emerald-500" : "text-red-500"} />
                <Row label="Mismatches" value={String(snapshot.reconciliation?.mismatches || 0)}
                  color={snapshot.reconciliation?.mismatches > 0 ? "text-red-500" : "text-emerald-500"} />
                {snapshot.reconciliation?.mismatches > 0 && (
                  <div className="text-[8px] text-red-500 mt-1">Auto-correction disabled. Manual reconciliation required.</div>
                )}
              </div>
            </SectionCard>

            {/* Incidents */}
            <SectionCard icon={<Siren className="w-3.5 h-3.5" />} title="Incidents">
              <div className="space-y-1.5 text-[10px]">
                <Row label="Open" value={String(snapshot.incidents?.open_count || 0)}
                  color={snapshot.incidents?.open_count > 0 ? "text-amber-500" : "text-emerald-500"} />
                <Row label="Critical" value={String(snapshot.incidents?.critical_count || 0)}
                  color={snapshot.incidents?.critical_count > 0 ? "text-red-500" : "text-emerald-500"} />
                <Row label="Emergency" value={String(snapshot.incidents?.emergency_count || 0)}
                  color={snapshot.incidents?.emergency_count > 0 ? "text-red-600" : "text-emerald-500"} />
                {snapshot.incidents?.latest_incident && (
                  <Row label="Latest" value={snapshot.incidents.latest_incident.slice(0, 50)} />
                )}
              </div>
            </SectionCard>

            {/* Recovery */}
            <SectionCard icon={<RefreshCw className="w-3.5 h-3.5" />} title="Recovery">
              <div className="space-y-1.5 text-[10px]">
                <Row label="Required" value={snapshot.recovery?.recovery_required ? "YES" : "NO"}
                  color={snapshot.recovery?.recovery_required ? "text-red-500" : "text-emerald-500"} />
                <Row label="State" value={snapshot.recovery?.recovery_state || "n/a"} />
                <Row label="Auto Resume" value={snapshot.recovery?.auto_resume_allowed ? "ENABLED" : "DISABLED"}
                  color={snapshot.recovery?.auto_resume_allowed ? "text-red-500" : "text-emerald-500"} />
                <div className="text-[8px] text-muted-foreground mt-1">Recovery never automatically resumes trading.</div>
              </div>
            </SectionCard>

            {/* Integrity */}
            <SectionCard icon={<Shield className="w-3.5 h-3.5" />} title="Integrity">
              <div className="space-y-1.5 text-[10px]">
                <Row label="Config" value={snapshot.integrity?.config_match ? "MATCH" : "MISMATCH"}
                  color={snapshot.integrity?.config_match ? "text-emerald-500" : "text-red-500"} />
                <Row label="Champion" value={snapshot.integrity?.champion_match ? "MATCH" : "MISMATCH"}
                  color={snapshot.integrity?.champion_match ? "text-emerald-500" : "text-red-500"} />
                <Row label="Status" value={snapshot.integrity?.integrity_status || "?"} />
                {!snapshot.integrity?.config_match && (
                  <div className="text-[8px] text-red-500 mt-1">Trading blocked. Human review required.</div>
                )}
              </div>
            </SectionCard>

            {/* Approval */}
            <SectionCard icon={<UserCheck className="w-3.5 h-3.5" />} title="Approval">
              <div className="space-y-1.5 text-[10px]">
                <Row label="State" value={snapshot.approval?.approval_state || "none"} />
                {snapshot.approval?.reviewer && (
                  <Row label="Reviewer" value={snapshot.approval.reviewer} />
                )}
                {snapshot.approval?.expires_at && (
                  <Row label="Expires" value={new Date(snapshot.approval.expires_at).toLocaleTimeString()} />
                )}
              </div>
            </SectionCard>

            {/* Metrics */}
            <SectionCard icon={<BarChart3 className="w-3.5 h-3.5" />} title="Metrics">
              <div className="space-y-1.5 text-[10px]">
                <Row label="Health Score" value={snapshot.metrics?.health_score != null ? `${snapshot.metrics.health_score}%` : "?"} />
                <Row label="Heartbeat Rate" value={snapshot.metrics?.heartbeat_rate != null ? `${snapshot.metrics.heartbeat_rate}%` : "?"} />
                <Row label="MTTA" value={snapshot.metrics?.mtta_seconds != null ? `${snapshot.metrics.mtta_seconds.toFixed(0)}s` : "?"} />
                <Row label="MTTR" value={snapshot.metrics?.mttr_seconds != null ? `${snapshot.metrics.mttr_seconds.toFixed(0)}s` : "?"} />
                <Row label="Incidents" value={String(snapshot.metrics?.incident_count || 0)} />
                <Row label="Rollbacks" value={String(snapshot.metrics?.rollback_count || 0)} />
              </div>
            </SectionCard>

          </div>

          {/* ── Safety Summary ── */}
          <div className="rounded-lg border bg-card p-3">
            <h3 className="text-xs font-bold mb-2 flex items-center gap-2">
              <Lock className="w-3.5 h-3.5" /> Safety Summary
            </h3>
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 text-[10px]">
              <SafetyItem label="Phase 43 Lock" status={snapshot.safety?.phase43_lock ? "ACTIVE" : "INACTIVE"}
                ok={snapshot.safety?.phase43_lock} />
              <SafetyItem label="can_execute_live" status={String(snapshot.safety?.can_execute_live ?? false)}
                ok={!snapshot.safety?.can_execute_live} />
              <SafetyItem label="Activation Gate" status={snapshot.safety?.activation_state || "?"}
                ok={snapshot.safety?.activation_state === "locked"} />
              <SafetyItem label="Kill Switch" status={snapshot.safety?.kill_switch ? "ACTIVE" : "CLEAR"}
                ok={!snapshot.safety?.kill_switch} />
              <SafetyItem label="Risk Engine" status={snapshot.risk?.risk_engine_available ? "AVAILABLE" : "UNAVAILABLE"}
                ok={snapshot.risk?.risk_engine_available} />
              <SafetyItem label="Market Data" status={snapshot.market?.stale ? "STALE" : "HEALTHY"}
                ok={!snapshot.market?.stale} />
              <SafetyItem label="Broker" status={snapshot.broker?.connected ? "CONNECTED" : "DISCONNECTED"}
                ok={snapshot.broker?.connected} />
              <SafetyItem label="Reconciliation" status={snapshot.reconciliation?.mismatches > 0 ? "MISMATCH" : "MATCHED"}
                ok={snapshot.reconciliation?.mismatches === 0} />
            </div>
            <div className="mt-2 text-[8px] text-muted-foreground text-center">
              No live order execution is currently permitted.
            </div>
          </div>

        </>
      )}
    </div>
  )
}

// ── Sub-components ──

function KpiCard({ label, value, color }: { label: string; value: string; color?: string }) {
  return (
    <div className="rounded-lg border bg-card p-2">
      <div className="text-[8px] text-muted-foreground uppercase tracking-wider">{label}</div>
      <div className={`text-xs font-bold font-mono mt-0.5 truncate ${color || ""}`}>{value}</div>
    </div>
  )
}

function SectionCard({ icon, title, children }: { icon: React.ReactNode; title: string; children: React.ReactNode }) {
  return (
    <div className="rounded-lg border bg-card p-3">
      <h3 className="text-xs font-bold mb-2 flex items-center gap-1.5">
        {icon} {title}
      </h3>
      {children}
    </div>
  )
}

function Row({ label, value, color }: { label: string; value: string; color?: string }) {
  return (
    <div className="flex justify-between items-center">
      <span className="text-muted-foreground">{label}</span>
      <span className={`font-mono font-medium ${color || ""}`}>{value}</span>
    </div>
  )
}

function SafetyItem({ label, status, ok }: { label: string; status: string; ok: boolean }) {
  return (
    <div className="flex items-center gap-1.5 p-1 rounded bg-muted/20">
      {ok ? <CheckCircle className="w-3 h-3 text-emerald-500 shrink-0" /> : <XCircle className="w-3 h-3 text-red-500 shrink-0" />}
      <div className="min-w-0">
        <div className="text-[8px] text-muted-foreground truncate">{label}</div>
        <div className={`text-[9px] font-mono font-medium truncate ${ok ? "text-emerald-500" : "text-red-500"}`}>{status}</div>
      </div>
    </div>
  )
}
