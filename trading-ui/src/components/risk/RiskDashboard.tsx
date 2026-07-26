"use client"

import { useState, useEffect, useCallback } from "react"
import { Shield, Activity, BarChart3, AlertTriangle, Ban, PauseCircle, Power, LogOut, RefreshCw, FileText, TrendingDown, DollarSign, Target } from "lucide-react"
import { riskService, type RiskStatus } from "@/services/riskService"

type TabId = "overview" | "exposure" | "drawdown" | "rules" | "logs" | "sizing" | "emergency"

interface LogEntry {
  id: number
  timestamp: string
  event_type: string
  symbol: string
  side: string
  status: string
  reason: string
  risk_score: number
  risk_grade: string
}

export function RiskDashboard() {
  const [activeTab, setActiveTab] = useState<TabId>("overview")
  const [status, setStatus] = useState<RiskStatus | null>(null)
  const [logs, setLogs] = useState<LogEntry[]>([])
  const [loading, setLoading] = useState(true)

  const fetchData = useCallback(async () => {
    try {
      const s = await riskService.getStatus()
      setStatus(s)
    } catch {
      // ignore
    }
    try {
      const l = await riskService.getLogs(50)
      setLogs(l.logs as unknown as LogEntry[])
    } catch {
      // ignore
    }
    setLoading(false)
  }, [])

  useEffect(() => {
    const t = setTimeout(() => fetchData(), 0)
    const interval = setInterval(fetchData, 10000)
    return () => { clearTimeout(t); clearInterval(interval) }
  }, [fetchData])

  const handleEmergency = async (action: string) => {
    try {
      await riskService.emergency(action)
      await fetchData()
    } catch {
      // ignore
    }
  }

  const tabs: { id: TabId; label: string; icon: React.ReactNode }[] = [
    { id: "overview", label: "Overview", icon: <Shield className="w-3.5 h-3.5" /> },
    { id: "exposure", label: "Exposure", icon: <BarChart3 className="w-3.5 h-3.5" /> },
    { id: "drawdown", label: "Drawdown", icon: <TrendingDown className="w-3.5 h-3.5" /> },
    { id: "rules", label: "Rules", icon: <Target className="w-3.5 h-3.5" /> },
    { id: "logs", label: "Audit Log", icon: <FileText className="w-3.5 h-3.5" /> },
    { id: "sizing", label: "Sizing", icon: <DollarSign className="w-3.5 h-3.5" /> },
    { id: "emergency", label: "Emergency", icon: <AlertTriangle className="w-3.5 h-3.5" /> },
  ]

  const gradeColor = (g?: string) => {
    switch (g) {
      case "CRITICAL": return "text-red-500"
      case "HIGH": return "text-orange-500"
      case "MEDIUM": return "text-amber-500"
      default: return "text-emerald-500"
    }
  }

  const gradeBg = (g?: string) => {
    switch (g) {
      case "CRITICAL": return "bg-red-500/10 border-red-500/20"
      case "HIGH": return "bg-orange-500/10 border-orange-500/20"
      case "MEDIUM": return "bg-amber-500/10 border-amber-500/20"
      default: return "bg-emerald-500/10 border-emerald-500/20"
    }
  }

  return (
    <div className="space-y-4">
      {/* Header */}
      <div className="flex items-center gap-2">
        <Shield className="w-5 h-5 text-primary" />
        <h1 className="text-lg font-bold">Risk Firewall</h1>
        {status && (
          <span className={`ml-auto px-2 py-0.5 rounded text-[10px] font-bold border ${gradeBg(status.risk_grade)} ${gradeColor(status.risk_grade)}`}>
            {status.risk_grade} · Score {status.risk_score}
          </span>
        )}
        <button onClick={fetchData} className="p-1 rounded text-muted-foreground hover:text-foreground hover:bg-accent">
          <RefreshCw className={`w-3.5 h-3.5 ${loading ? "animate-spin" : ""}`} />
        </button>
      </div>

      {/* Tabs */}
      <div className="flex gap-1 border-b overflow-x-auto">
        {tabs.map((tab) => (
          <button
            key={tab.id}
            onClick={() => setActiveTab(tab.id)}
            className={`flex items-center gap-1 px-3 py-1.5 text-[10px] font-medium border-b-2 transition-colors shrink-0 ${
              activeTab === tab.id ? "border-primary text-foreground" : "border-transparent text-muted-foreground hover:text-foreground"
            }`}
          >
            {tab.icon} {tab.label}
          </button>
        ))}
      </div>

      {/* Content */}
      <div className="min-h-[400px]">
        {activeTab === "overview" && <OverviewTab status={status} />}
        {activeTab === "exposure" && <ExposureTab status={status} />}
        {activeTab === "drawdown" && <DrawdownTab status={status} />}
        {activeTab === "rules" && <RulesTab />}
        {activeTab === "logs" && <LogsTab logs={logs} />}
        {activeTab === "sizing" && <SizingTab />}
        {activeTab === "emergency" && <EmergencyTab onAction={handleEmergency} status={status} />}
      </div>
    </div>
  )
}

function MetricCard({ label, value, sub, color }: { label: string; value: string; sub?: string; color?: string }) {
  return (
    <div className="rounded-lg border bg-card p-3">
      <div className="text-[9px] text-muted-foreground uppercase tracking-wider">{label}</div>
      <div className={`text-lg font-bold font-mono mt-0.5 ${color || ""}`}>{value}</div>
      {sub && <div className="text-[9px] text-muted-foreground mt-0.5">{sub}</div>}
    </div>
  )
}

function OverviewTab({ status }: { status: RiskStatus | null }) {
  if (!status) return <div className="p-8 text-center text-[10px] text-muted-foreground">Loading risk data...</div>

  const exposure = (status.exposure || {}) as Record<string, unknown>

  return (
    <div className="space-y-4">
      <div className="grid grid-cols-4 gap-3">
        <MetricCard label="Risk Score" value={`${status.risk_score}`} sub={`Grade: ${status.risk_grade}`} color={status.risk_score >= 50 ? "text-red-500" : "text-emerald-500"} />
        <MetricCard label="Daily Trades" value={`${status.daily_trades}`} sub="Today" />
        <MetricCard label="Daily PnL" value={`₹${(status.daily_loss || 0).toLocaleString()}`} color={(status.daily_loss || 0) < 0 ? "text-red-500" : "text-emerald-500"} />
        <MetricCard label="Exposure" value={`${(exposure.buying_power_used_pct as number || 0).toFixed(1)}%`}
          color={(exposure.buying_power_used_pct as number || 0) > 60 ? "text-amber-500" : "text-emerald-500"} />
      </div>

      {/* Status Cards */}
      <div className="grid grid-cols-3 gap-3">
        <div className={`rounded-lg border p-3 ${status.trading_halt ? "bg-red-500/10 border-red-500/20" : "bg-card"}`}>
          <div className="flex items-center gap-2">
            <PauseCircle className={`w-4 h-4 ${status.trading_halt ? "text-red-500" : "text-muted-foreground"}`} />
            <span className="text-xs font-medium">{status.trading_halt ? "Trading Halted" : "Trading Active"}</span>
          </div>
        </div>
        <div className={`rounded-lg border p-3 ${status.broker_disabled ? "bg-red-500/10 border-red-500/20" : "bg-card"}`}>
          <div className="flex items-center gap-2">
            <Ban className={`w-4 h-4 ${status.broker_disabled ? "text-red-500" : "text-muted-foreground"}`} />
            <span className="text-xs font-medium">{status.broker_disabled ? "Broker Disabled" : "Broker Active"}</span>
          </div>
        </div>
        <div className={`rounded-lg border p-3 ${status.ai_disabled ? "bg-amber-500/10 border-amber-500/20" : "bg-card"}`}>
          <div className="flex items-center gap-2">
            <Power className={`w-4 h-4 ${status.ai_disabled ? "text-amber-500" : "text-muted-foreground"}`} />
            <span className="text-xs font-medium">{status.ai_disabled ? "AI Disabled" : "AI Active"}</span>
          </div>
        </div>
      </div>

      {/* Logs Summary */}
      <div className="border rounded-lg">
        <div className="px-3 py-2 border-b bg-muted/20 flex items-center gap-2">
          <Activity className="w-3.5 h-3.5 text-muted-foreground" />
          <span className="text-[10px] font-medium text-muted-foreground uppercase">Recent Validations</span>
        </div>
        <div className="max-h-48 overflow-y-auto">
          <MiniLogViewer />
        </div>
      </div>
    </div>
  )
}

function MiniLogViewer() {
  const [logs, setLogs] = useState<LogEntry[]>([])
  useEffect(() => {
    riskService.getLogs(20).then(d => setLogs((d.logs ?? []) as any)).catch(() => {})
  }, [])

  if (logs.length === 0) return <div className="p-4 text-center text-[10px] text-muted-foreground">No recent validations</div>

  return (
    <div className="divide-y text-[10px]">
      {logs.map((log) => (
        <div key={log.id} className="flex items-center gap-2 px-3 py-1.5 hover:bg-muted/20">
          <div className={`w-1.5 h-1.5 rounded-full ${
            log.status === "pass" ? "bg-emerald-500" : log.status === "rejected" ? "bg-red-500" : "bg-amber-500"
          }`} />
          <span className="font-mono text-muted-foreground w-16">{log.timestamp?.split("T")[1]?.slice(0, 8) || ""}</span>
          <span className="font-medium">{log.symbol || "—"}</span>
          <span className="text-muted-foreground truncate flex-1">{log.reason || log.status}</span>
          <span className={log.risk_grade === "CRITICAL" ? "text-red-500 font-bold" : "text-muted-foreground"}>
            {log.risk_score ? `${log.risk_score}` : ""}
          </span>
        </div>
      ))}
    </div>
  )
}

function ExposureTab({ status }: { status: RiskStatus | null }) {
  const exposure = (status?.exposure || {}) as Record<string, unknown>
  const snap = exposure as Record<string, number | string>
  return (
    <div className="grid grid-cols-3 gap-3">
      <MetricCard label="Total Exposure" value={`₹${(snap.total_exposure || 0).toLocaleString()}`} />
      <MetricCard label="Long Exposure" value={`₹${(snap.long_exposure || 0).toLocaleString()}`} color="text-emerald-500" />
      <MetricCard label="Short Exposure" value={`₹${(Math.abs(snap.short_exposure as number || 0)).toLocaleString()}`} color="text-red-500" />
      <MetricCard label="Net Exposure" value={`₹${(snap.net_exposure || 0).toLocaleString()}`} />
      <MetricCard label="Gross Exposure" value={`₹${(snap.gross_exposure || 0).toLocaleString()}`} />
      <MetricCard label="Buying Power" value={`₹${(snap.buying_power || 0).toLocaleString()}`} color="text-emerald-500" />
      <MetricCard label="BP Used" value={`${Number(snap.buying_power_used_pct || 0).toFixed(1)}%`} color={Number(snap.buying_power_used_pct || 0) > 60 ? "text-amber-500" : ""} />
    </div>
  )
}

function DrawdownTab({ status }: { status: RiskStatus | null }) {
  const dd = (status?.drawdown || {}) as Record<string, number>
  return (
    <div className="grid grid-cols-3 gap-3">
      <MetricCard label="Session DD" value={`${(dd.session_dd_percent || 0).toFixed(1)}%`} color={(dd.session_dd_percent || 0) > 10 ? "text-red-500" : ""} />
      <MetricCard label="Weekly DD" value={`${(dd.week_dd_percent || 0).toFixed(1)}%`} color={(dd.week_dd_percent || 0) > 15 ? "text-red-500" : ""} />
      <MetricCard label="Monthly DD" value={`${(dd.month_dd_percent || 0).toFixed(1)}%`} color={(dd.month_dd_percent || 0) > 20 ? "text-red-500" : ""} />
      <MetricCard label="All Time DD" value={`${(dd.all_time_dd_percent || 0).toFixed(1)}%`} color="text-red-500" />
      <MetricCard label="Session PnL" value={`₹${(dd.session_pnl || 0).toLocaleString()}`} color={(dd.session_pnl || 0) < 0 ? "text-red-500" : "text-emerald-500"} />
      <MetricCard label="Month PnL" value={`₹${(dd.month_pnl || 0).toLocaleString()}`} color={(dd.month_pnl || 0) < 0 ? "text-red-500" : "text-emerald-500"} />
    </div>
  )
}

function RulesTab() {
  const [settings, setSettings] = useState<Record<string, unknown>>({})
  const [saving, setSaving] = useState(false)

  useEffect(() => {
    riskService.getSettings().then(setSettings).catch(() => {})
  }, [])

  const handleChange = async (key: string, value: number | boolean) => {
    const updated = { ...settings, [key]: value }
    setSettings(updated)
    setSaving(true)
    try {
      await riskService.updateSettings(updated as Record<string, unknown>)
    } catch {
      // ignore
    }
    setSaving(false)
  }

  const rules = [
    { key: "max_daily_loss", label: "Max Daily Loss", desc: "Stop trading after this loss", suffix: "", step: 1000 },
    { key: "max_weekly_loss", label: "Max Weekly Loss", desc: "Stop trading for the week", suffix: "", step: 1000 },
    { key: "max_monthly_loss", label: "Max Monthly Loss", desc: "Stop trading for the month", suffix: "", step: 5000 },
    { key: "max_drawdown_percent", label: "Max Drawdown %", desc: "Max peak-to-trough decline", suffix: "%", step: 1 },
    { key: "max_daily_trades", label: "Max Daily Trades", desc: "Trade count limit", suffix: "", step: 1 },
    { key: "max_concurrent_positions", label: "Max Positions", desc: "Open position limit", suffix: "", step: 1 },
    { key: "max_open_orders", label: "Max Open Orders", desc: "Pending order limit", suffix: "", step: 1 },
    { key: "max_exposure_percent", label: "Max Exposure %", desc: "Portfolio exposure cap", suffix: "%", step: 5 },
    { key: "max_risk_percent", label: "Max Risk %/Trade", desc: "Per-trade risk cap", suffix: "%", step: 0.5 },
    { key: "trade_cooldown_seconds", label: "Cooldown (sec)", desc: "Min time between trades", suffix: "s", step: 10 },
    { key: "min_ai_score", label: "Min AI Score", desc: "Min score for auto trades", suffix: "", step: 5 },
    { key: "min_ai_confidence", label: "Min AI Confidence", desc: "Min confidence for auto trades", suffix: "", step: 5 },
    { key: "min_reward_risk", label: "Min R:R Ratio", desc: "Minimum reward-to-risk", suffix: "", step: 0.1 },
  ]

  return (
    <div className="space-y-2">
      <div className="flex items-center gap-2 mb-3">
        <span className="text-[10px] text-muted-foreground">Configure risk limits. {saving && "Saving..."}</span>
      </div>
      <div className="grid grid-cols-2 gap-3">
        {rules.map((rule) => (
          <div key={rule.key} className="rounded-lg border bg-card p-3">
            <div className="flex items-center justify-between mb-1">
              <label className="text-[11px] font-medium">{rule.label}</label>
              <span className="text-[11px] font-mono font-bold">
                {String(settings[rule.key] ?? 0)}{rule.suffix}
              </span>
            </div>
            <p className="text-[9px] text-muted-foreground mb-2">{rule.desc}</p>
            <input
              type="range"
              min={0}
              max={typeof settings[rule.key] === "number" ? Math.max((settings[rule.key] as number) * 2, 100) : 100}
              step={rule.step}
              value={String(settings[rule.key] ?? 0)}
              onChange={(e) => handleChange(rule.key, Number(e.target.value))}
              className="w-full h-1 accent-primary"
            />
          </div>
        ))}
      </div>
    </div>
  )
}

function LogsTab({ logs }: { logs: LogEntry[] }) {
  if (logs.length === 0) return <div className="p-8 text-center text-[10px] text-muted-foreground">No validation logs yet</div>

  return (
    <div className="border rounded-lg overflow-hidden">
      <table className="w-full text-[10px]">
        <thead>
          <tr className="bg-muted/30 border-b">
            <th className="text-left px-3 py-2 font-medium text-muted-foreground">Time</th>
            <th className="text-left px-3 py-2 font-medium text-muted-foreground">Symbol</th>
            <th className="text-left px-3 py-2 font-medium text-muted-foreground">Status</th>
            <th className="text-left px-3 py-2 font-medium text-muted-foreground">Reason</th>
            <th className="text-right px-3 py-2 font-medium text-muted-foreground">Risk Score</th>
            <th className="text-right px-3 py-2 font-medium text-muted-foreground">Grade</th>
          </tr>
        </thead>
        <tbody className="divide-y">
          {logs.map((log) => (
            <tr key={log.id} className="hover:bg-muted/20">
              <td className="px-3 py-1.5 font-mono text-muted-foreground">{log.timestamp?.split("T")[1]?.slice(0, 8) || log.timestamp}</td>
              <td className="px-3 py-1.5 font-medium">{log.symbol || "—"}</td>
              <td className="px-3 py-1.5">
                <span className={`px-1.5 py-0.5 rounded text-[9px] font-medium ${
                  log.status === "pass" ? "bg-emerald-500/10 text-emerald-500" : "bg-red-500/10 text-red-500"
                }`}>{log.status}</span>
              </td>
              <td className="px-3 py-1.5 text-muted-foreground max-w-[200px] truncate">{log.reason || "—"}</td>
              <td className="px-3 py-1.5 text-right font-mono">{log.risk_score ?? "—"}</td>
              <td className="px-3 py-1.5 text-right">
                <span className={`font-bold ${log.risk_grade === "CRITICAL" ? "text-red-500" : log.risk_grade === "HIGH" ? "text-orange-500" : "text-muted-foreground"}`}>
                  {log.risk_grade || "—"}
                </span>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}

function SizingTab() {
  const [method, setMethod] = useState("fixed_risk")
  const [params, setParams] = useState({
    capital: 100000, risk_percent: 2, price: 24500, stop_loss: 24300,
    quantity: 1, amount: 10000, lot_size: 1, atr: 200,
    win_rate: 0.55, avg_win: 500, avg_loss: 300,
    volatility_pct: 20, atr_multiplier: 2, kelly_fraction: 0.25,
  })
  const [result, setResult] = useState<Record<string, unknown> | null>(null)

  const calculate = async () => {
    try {
      const res = await riskService.calculatePositionSize({ ...params, method })
      setResult(res)
    } catch {
      // ignore
    }
  }

  useEffect(() => { const t = setTimeout(() => calculate(), 0); return () => clearTimeout(t) }, [method, params])

  return (
    <div className="grid grid-cols-2 gap-4">
      <div className="space-y-3 border rounded-lg p-4">
        <h3 className="text-xs font-bold">Position Sizing Calculator</h3>
        <select value={method} onChange={(e) => setMethod(e.target.value)}
          className="w-full h-7 rounded border bg-muted/30 px-2 text-[10px] font-medium">
          <option value="fixed_quantity">Fixed Quantity</option>
          <option value="fixed_amount">Fixed Amount</option>
          <option value="fixed_risk">Fixed Risk %</option>
          <option value="atr_based">ATR-Based</option>
          <option value="kelly">Kelly Criterion</option>
          <option value="volatility_adjusted">Volatility Adjusted</option>
        </select>
        {method === "fixed_quantity" && (
          <InputParam label="Quantity" value={params.quantity} onChange={(v) => setParams({ ...params, quantity: v })} />
        )}
        {method === "fixed_amount" && (
          <>
            <InputParam label="Amount (₹)" value={params.amount} onChange={(v) => setParams({ ...params, amount: v })} />
            <InputParam label="Lot Size" value={params.lot_size} onChange={(v) => setParams({ ...params, lot_size: v })} />
          </>
        )}
        {method === "fixed_risk" && (
          <>
            <InputParam label="Capital (₹)" value={params.capital} onChange={(v) => setParams({ ...params, capital: v })} />
            <InputParam label="Risk %" value={params.risk_percent} onChange={(v) => setParams({ ...params, risk_percent: v })} step={0.5} />
            <InputParam label="Entry Price" value={params.price} onChange={(v) => setParams({ ...params, price: v })} />
            <InputParam label="Stop Loss" value={params.stop_loss} onChange={(v) => setParams({ ...params, stop_loss: v })} />
            <InputParam label="Lot Size" value={params.lot_size} onChange={(v) => setParams({ ...params, lot_size: v })} />
          </>
        )}
        {method === "atr_based" && (
          <>
            <InputParam label="Capital (₹)" value={params.capital} onChange={(v) => setParams({ ...params, capital: v })} />
            <InputParam label="Entry Price" value={params.price} onChange={(v) => setParams({ ...params, price: v })} />
            <InputParam label="ATR Value" value={params.atr} onChange={(v) => setParams({ ...params, atr: v })} />
            <InputParam label="Risk %" value={params.risk_percent} onChange={(v) => setParams({ ...params, risk_percent: v })} step={0.5} />
            <InputParam label="ATR Multiplier" value={params.atr_multiplier} onChange={(v) => setParams({ ...params, atr_multiplier: v })} step={0.5} />
          </>
        )}
        {method === "kelly" && (
          <>
            <InputParam label="Capital (₹)" value={params.capital} onChange={(v) => setParams({ ...params, capital: v })} />
            <InputParam label="Win Rate" value={params.win_rate} onChange={(v) => setParams({ ...params, win_rate: v })} step={0.05} />
            <InputParam label="Avg Win (₹)" value={params.avg_win} onChange={(v) => setParams({ ...params, avg_win: v })} />
            <InputParam label="Avg Loss (₹)" value={params.avg_loss} onChange={(v) => setParams({ ...params, avg_loss: v })} />
            <InputParam label="Kelly Fraction" value={params.kelly_fraction} onChange={(v) => setParams({ ...params, kelly_fraction: v })} step={0.05} />
            <InputParam label="Price" value={params.price} onChange={(v) => setParams({ ...params, price: v })} />
          </>
        )}
        {method === "volatility_adjusted" && (
          <>
            <InputParam label="Capital (₹)" value={params.capital} onChange={(v) => setParams({ ...params, capital: v })} />
            <InputParam label="Price" value={params.price} onChange={(v) => setParams({ ...params, price: v })} />
            <InputParam label="Volatility %" value={params.volatility_pct} onChange={(v) => setParams({ ...params, volatility_pct: v })} />
            <InputParam label="Target Risk %" value={params.risk_percent} onChange={(v) => setParams({ ...params, risk_percent: v })} step={0.5} />
          </>
        )}
        <button onClick={calculate} className="w-full py-1.5 rounded text-[10px] font-medium bg-primary text-primary-foreground hover:bg-primary/90">
          Calculate
        </button>
      </div>

      <div className="border rounded-lg p-4">
        <h3 className="text-xs font-bold mb-3">Result</h3>
        {result ? (
          <div className="space-y-3">
            <div className="grid grid-cols-2 gap-2">
              <MetricCard label="Quantity" value={`${result.quantity || 0}`} />
              <MetricCard label="Capital Used" value={`₹${(result.capital_used as number || 0).toLocaleString()}`} />
              <MetricCard label="Risk Amount" value={`₹${(result.risk_amount as number || 0).toLocaleString()}`} color="text-red-500" />
              <MetricCard label="Risk %" value={`${(result.risk_percent as number || 0).toFixed(2)}%`} color={(result.risk_percent as number || 0) > 3 ? "text-red-500" : "text-emerald-500"} />
              <MetricCard label="Margin Req." value={`₹${(result.margin_required as number || 0).toLocaleString()}`} />
              <MetricCard label="Method" value={String(result.method || "")} />
            </div>
            {!!result.detail && typeof result.detail === "object" && (
              <div className="border-t pt-2 mt-2">
                <div className="text-[9px] text-muted-foreground uppercase mb-1">Details</div>
                <pre className="text-[9px] font-mono text-muted-foreground whitespace-pre-wrap">
                  {JSON.stringify(result.detail, null, 1)}
                </pre>
              </div>
            )}
          </div>
        ) : (
          <div className="p-8 text-center text-[10px] text-muted-foreground">Click Calculate</div>
        )}
      </div>
    </div>
  )
}

function InputParam({ label, value, onChange, step = 1 }: { label: string; value: number; onChange: (v: number) => void; step?: number }) {
  return (
    <div className="flex items-center justify-between gap-2">
      <label className="text-[10px] text-muted-foreground shrink-0">{label}</label>
      <input
        type="number"
        value={value}
        onChange={(e) => onChange(Number(e.target.value))}
        step={step}
        className="w-28 h-6 rounded border bg-muted/30 px-1.5 text-[10px] font-mono text-right focus:outline-none focus:ring-1 focus:ring-primary"
      />
    </div>
  )
}

function EmergencyTab({ onAction, status }: { onAction: (action: string) => void; status: RiskStatus | null }) {
  const actions = [
    { id: "pause_trading", label: "Pause Trading", icon: PauseCircle, color: "bg-amber-500/10 text-amber-600 hover:bg-amber-500/20 border-amber-500/20", active: status?.trading_halt },
    { id: "disable_ai", label: "Disable AI", icon: Power, color: "bg-orange-500/10 text-orange-600 hover:bg-orange-500/20 border-orange-500/20", active: status?.ai_disabled },
    { id: "disable_broker", label: "Disable Broker", icon: Ban, color: "bg-red-500/10 text-red-600 hover:bg-red-500/20 border-red-500/20", active: status?.broker_disabled },
    { id: "emergency_exit", label: "Emergency Exit", icon: LogOut, color: "bg-red-600/10 text-red-600 hover:bg-red-600/20 border-red-600/20", active: false },
    { id: "reset", label: "Reset All", icon: RefreshCw, color: "bg-emerald-500/10 text-emerald-600 hover:bg-emerald-500/20 border-emerald-500/20", active: false },
  ]

  return (
    <div className="space-y-4">
      <div className="grid grid-cols-3 gap-3">
        {actions.map((action) => (
          <button
            key={action.id}
            onClick={() => onAction(action.id)}
            className={`flex flex-col items-center gap-2 p-6 rounded-lg border transition-colors ${action.color} ${action.active ? "ring-2 ring-red-500" : ""}`}
          >
            <action.icon className="w-6 h-6" />
            <span className="text-xs font-bold">{action.label}</span>
            {action.active && <span className="text-[9px] text-red-500 font-medium">ACTIVE</span>}
          </button>
        ))}
      </div>
      <div className="rounded-lg border bg-amber-500/5 p-3 text-[10px] text-amber-600">
        <strong>Warning:</strong> Emergency controls immediately halt trading activity. Use with caution.
      </div>
    </div>
  )
}
