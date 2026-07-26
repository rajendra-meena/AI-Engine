"use client"

import { useState, useEffect, useCallback } from "react"
import {
  Activity, BarChart3, TrendingUp, DollarSign, Target, Shield,
  RefreshCw,
} from "lucide-react"
import { performanceService } from "@/services/performanceService"

type TabId = "overview" | "funnel" | "pnl" | "calibration" | "regimes" | "timeframes" | "symbols" | "directions" | "rmultiple" | "blocked"

export function PerformanceDashboard() {
  const [activeTab, setActiveTab] = useState<TabId>("overview")
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const [data, setData] = useState<any>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const fetchAll = useCallback(async () => {
    try {
      const d = await performanceService.getOverview()
      setError(null)
      setData(d)
    } catch { setError("Failed to load") }
    setLoading(false)
  }, [])

  useEffect(() => {
    const t = setTimeout(() => fetchAll(), 0)
    const interval = setInterval(fetchAll, 30000)
    return () => { clearTimeout(t); clearInterval(interval) }
  }, [fetchAll])

  const tabs = [
    { id: "overview" as TabId, label: "Overview", icon: <Activity className="w-3.5 h-3.5" /> },
    { id: "funnel" as TabId, label: "Funnel", icon: <BarChart3 className="w-3.5 h-3.5" /> },
    { id: "pnl" as TabId, label: "P&L", icon: <DollarSign className="w-3.5 h-3.5" /> },
    { id: "rmultiple" as TabId, label: "R-Multiple", icon: <Target className="w-3.5 h-3.5" /> },
    { id: "calibration" as TabId, label: "Calibration", icon: <Activity className="w-3.5 h-3.5" /> },
    { id: "regimes" as TabId, label: "Regimes", icon: <TrendingUp className="w-3.5 h-3.5" /> },
    { id: "timeframes" as TabId, label: "Timeframes", icon: <Activity className="w-3.5 h-3.5" /> },
    { id: "symbols" as TabId, label: "Symbols", icon: <Activity className="w-3.5 h-3.5" /> },
    { id: "directions" as TabId, label: "Directions", icon: <Target className="w-3.5 h-3.5" /> },
    { id: "blocked" as TabId, label: "Blocked", icon: <Shield className="w-3.5 h-3.5" /> },
  ]

  const s = data || {}

  return (
    <div className="space-y-4">
      <div className="flex items-center gap-2">
        <Activity className="w-5 h-5 text-primary" />
        <h1 className="text-lg font-bold">Performance Analytics</h1>
        <span className="ml-2 text-[9px] text-muted-foreground bg-muted/30 px-2 py-0.5 rounded">{s.sample_level?.replace(/_/g, " ") || "—"}</span>
        <button onClick={fetchAll} className="ml-auto p-1 rounded text-muted-foreground hover:text-foreground hover:bg-accent">
          <RefreshCw className={`w-3.5 h-3.5 ${loading ? "animate-spin" : ""}`} />
        </button>
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
            <MetricCard label="Total Trades" value={String(s.total_trades || 0)} />
            <MetricCard label="Win Rate" value={`${s.win_rate || 0}%`} color={(s.win_rate || 0) >= 50 ? "text-emerald-500" : "text-red-500"} />
            <MetricCard label="Net P&L" value={`$${(s.net_pnl || 0).toFixed(2)}`} color={(s.net_pnl || 0) >= 0 ? "text-emerald-500" : "text-red-500"} />
            <MetricCard label="Profit Factor" value={String(s.profit_factor || 0)} color={(s.profit_factor || 0) >= 1.5 ? "text-emerald-500" : "text-amber-500"} />
          </div>
          <div className="grid grid-cols-4 gap-3">
            <MetricCard label="Expectancy" value={`$${(s.expectancy || 0).toFixed(2)}`} color={(s.expectancy || 0) > 0 ? "text-emerald-500" : "text-red-500"} />
            <MetricCard label="Avg Win" value={`$${(s.average_win || 0).toFixed(2)}`} color="text-emerald-500" />
            <MetricCard label="Avg Loss" value={`$${(s.average_loss || 0).toFixed(2)}`} color="text-red-500" />
            <MetricCard label="Largest Win" value={`$${(s.largest_win || 0).toFixed(2)}`} color="text-emerald-500" />
          </div>
          <div className="grid grid-cols-4 gap-3">
            <MetricCard label="Target Hit Rate" value={`${s.target_hit_rate || 0}%`} color="text-emerald-500" />
            <MetricCard label="SL Hit Rate" value={`${s.stoploss_hit_rate || 0}%`} color="text-red-500" />
            <MetricCard label="Avg Holding" value={`${s.avg_holding_hours || 0}h`} />
            <MetricCard label="Blocked" value={String(s.blocked_count || 0)} />
          </div>
          <SampleInfo count={s.total_trades || 0} />
        </div>
      )}

      {activeTab === "funnel" && <FunnelTab />}
      {activeTab === "pnl" && <PnlTab />}
      {activeTab === "rmultiple" && <RMultipleTab />}
      {activeTab === "calibration" && <CalibrationTab />}
      {activeTab === "regimes" && <RegimeTab />}
      {activeTab === "timeframes" && <TimeframeTab />}
      {activeTab === "symbols" && <SymbolTab />}
      {activeTab === "directions" && <DirectionTab />}
      {activeTab === "blocked" && <BlockedTab />}
    </div>
  )
}

function MetricCard({ label, value, color }: { label: string; value: string; color?: string }) {
  return <div className="rounded-lg border bg-card p-3">
    <div className="text-[9px] text-muted-foreground uppercase tracking-wider">{label}</div>
    <div className={`text-lg font-bold font-mono mt-0.5 ${color || ""}`}>{value}</div>
  </div>
}

function SampleInfo({ count }: { count: number }) {
  const color = count < 20 ? "text-red-500" : count < 50 ? "text-amber-500" : count < 100 ? "text-blue-500" : "text-emerald-500"
  const label = count < 20 ? "Insufficient Sample" : count < 50 ? "Low Confidence" : count < 100 ? "Moderate Sample" : "Stronger Sample"
  return (
    <div className={`rounded-lg border p-3 text-[10px] ${color} bg-opacity-5`}>
      <strong>Sample Size: {count}</strong> — {label}. {count < 50 && "More data needed for reliable conclusions."}
    </div>
  )
}

function FunnelTab() {
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const [funnel, setFunnel] = useState<any>(null)
  const [loading, setLoading] = useState(true)
  useEffect(() => {
    performanceService.getFunnel().then(setFunnel).catch(() => {}).finally(() => setLoading(false))
  }, [])
  if (loading) return <div className="p-8 text-center text-[10px] text-muted-foreground">Loading...</div>
  if (!funnel) return <div className="p-8 text-center text-[10px] text-muted-foreground">No data</div>
  const stages = [
    { label: "Total Signals", value: funnel.total_signals },
    { label: "BUY / SELL", value: (funnel.buy || 0) + (funnel.sell || 0) },
    { label: "WAIT", value: funnel.wait },
    { label: "Strategy Qualified", value: funnel.strategy_qualified },
    { label: "Risk Approved", value: funnel.risk_approved },
    { label: "Executed", value: funnel.paper_executed },
    { label: "Closed", value: funnel.closed },
  ]
  return (
    <div className="space-y-3">
      <div className="grid grid-cols-4 gap-2">
        {stages.map((s, i) => (
          <div key={i} className="rounded-lg border bg-card p-3 text-center">
            <div className="text-lg font-bold font-mono">{s.value}</div>
            <div className="text-[9px] text-muted-foreground mt-1">{s.label}</div>
          </div>
        ))}
      </div>
      <div className="space-y-1 text-[10px] p-3 rounded-lg border">
        <div>Conversion Rate: {funnel.conversion_rate}%</div>
        <div>Qualification Rate: {funnel.qualification_rate}%</div>
        <div>Approval Rate: {funnel.approval_rate}%</div>
      </div>
    </div>
  )
}

function PnlTab() {
  const [pnl, setPnl] = useState<any>(null); const [loading, setL] = useState(true)
  useEffect(() => {
    performanceService.getPnl().then(setPnl).catch(() => {}).finally(() => setL(false))
  }, [])
  if (loading) return <div className="p-8 text-center text-[10px]">Loading...</div>
  const d = pnl?.overview || {}
  return (
    <div className="space-y-4">
      <div className="grid grid-cols-3 gap-3">
        <MetricCard label="Net P&L" value={`$${(d.net_pnl || 0).toFixed(2)}`} color={(d.net_pnl || 0) >= 0 ? "text-emerald-500" : "text-red-500"} />
        <MetricCard label="Profit Factor" value={String(d.profit_factor || 0)} />
        <MetricCard label="Expectancy" value={`$${(d.expectancy || 0).toFixed(2)}`} />
      </div>
      <div className="grid grid-cols-2 gap-3">
        <MetricCard label="Gross Profit" value={`$${(d.gross_profit || 0).toFixed(2)}`} color="text-emerald-500" />
        <MetricCard label="Gross Loss" value={`$${(d.gross_loss || 0).toFixed(2)}`} color="text-red-500" />
        <MetricCard label="Average Win" value={`$${(d.average_win || 0).toFixed(2)}`} color="text-emerald-500" />
        <MetricCard label="Average Loss" value={`$${(d.average_loss || 0).toFixed(2)}`} color="text-red-500" />
      </div>
      <SampleInfo count={d.total_trades || 0} />
    </div>
  )
}

function RMultipleTab() {
  const [rdata, setR] = useState<any>(null); const [loading, setL] = useState(true)
  useEffect(() => {
    performanceService.getRMultiple().then(setR).catch(() => {}).finally(() => setL(false))
  }, [])
  if (loading) return <div className="p-8 text-center text-[10px]">Loading...</div>
  if (!rdata) return <div className="p-8 text-center text-[10px]">No data</div>
  const dist = rdata.distribution || {}
  return (
    <div className="space-y-4">
      <div className="grid grid-cols-4 gap-3">
        <MetricCard label="Avg R" value={String(rdata.avg_r || 0)} color={(rdata.avg_r || 0) > 0 ? "text-emerald-500" : "text-red-500"} />
        <MetricCard label="Median R" value={String(rdata.median_r || 0)} />
        <MetricCard label="R ≥ 2" value={String(dist.ge_2r || 0)} color="text-emerald-500" />
        <MetricCard label="R ≤ -1" value={String(dist.lt_neg1r || 0)} color="text-red-500" />
      </div>
      <div className="grid grid-cols-5 gap-2 text-[10px]">
        {[
          { label: "≥ +2R", value: dist.ge_2r || 0, color: "text-emerald-500" },
          { label: "+1 to +2R", value: dist.ge_1r_lt_2r || 0, color: "text-emerald-400" },
          { label: "0 to +1R", value: dist.ge_0r_lt_1r || 0, color: "text-amber-500" },
          { label: "0 to -1R", value: dist.ge_neg1r_lt_0r || 0, color: "text-orange-500" },
          { label: "< -1R", value: dist.lt_neg1r || 0, color: "text-red-500" },
        ].map((b, i) => (
          <div key={i} className="rounded border bg-card p-2 text-center">
            <div className={`text-lg font-bold font-mono ${b.color}`}>{b.value}</div>
            <div className="text-muted-foreground">{b.label}</div>
          </div>
        ))}
      </div>
      <SampleInfo count={rdata.sample_count || 0} />
    </div>
  )
}

function CalibrationTab() {
  const [cal, setCal] = useState<any>(null); const [loading, setL] = useState(true)
  useEffect(() => {
    performanceService.getCalibration().then(setCal).catch(() => {}).finally(() => setL(false))
  }, [])
  if (loading) return <div className="p-8 text-center text-[10px]">Loading...</div>
  const buckets = cal?.buckets || []
  if (buckets.length === 0) return <div className="p-8 text-center text-[10px]">No calibration data</div>
  return (
    <div className="grid grid-cols-2 gap-3">
      {buckets.map((b: any) => (
        <div key={b.bucket} className="rounded-lg border bg-card p-3">
          <div className="text-xs font-bold mb-2">Confidence: {b.bucket}%</div>
          <div className="text-[10px] space-y-1">
            <div>Trades: <span className="font-mono">{b.trade_count}</span></div>
            <div>Wins: <span className="font-mono">{b.win_count}</span></div>
            <div>Win Rate: <span className={`font-mono ${b.win_rate >= 50 ? "text-emerald-500" : "text-red-500"}`}>{b.win_rate}%</span></div>
            <div>Avg R: <span className="font-mono">{b.avg_r}</span></div>
          </div>
          <span className={`text-[8px] ${b.sample_level === "insufficient_sample" ? "text-red-500" : "text-muted-foreground"}`}>{b.sample_level?.replace(/_/g, " ")}</span>
        </div>
      ))}
    </div>
  )
}

function RegimeTab() {
  const [regs, setRegs] = useState<any>(null); const [loading, setL] = useState(true)
  useEffect(() => {
    performanceService.getRegimes().then(setRegs).catch(() => {}).finally(() => setL(false))
  }, [])
  const items = regs?.regimes || []
  if (loading) return <div className="p-8 text-center text-[10px]">Loading...</div>
  if (items.length === 0) return <div className="p-8 text-center text-[10px]">No regime data</div>
  return <div className="grid grid-cols-2 gap-3">{items.map((r: any, i: number) => (
    <div key={i} className="rounded-lg border bg-card p-3">
      <div className="text-xs font-bold mb-1">{r.regime}</div>
      <div className="text-[10px] space-y-0.5">
        <div>Trades: {r.trade_count} | Wins: {r.win_count}</div>
        <div>Win Rate: <span className={r.win_rate >= 50 ? "text-emerald-500" : "text-red-500"}>{r.win_rate}%</span></div>
        <div>P&L: <span className={(r.net_pnl || 0) >= 0 ? "text-emerald-500" : "text-red-500"}>${(r.net_pnl || 0).toFixed(2)}</span></div>
      </div>
      <span className="text-[8px] text-muted-foreground">{r.sample_level?.replace(/_/g, " ")}</span>
    </div>
  ))}</div>
}

function TimeframeTab() {
  const [tfs, setTfs] = useState<any>(null); const [loading, setL] = useState(true)
  useEffect(() => {
    performanceService.getTimeframes().then(setTfs).catch(() => {}).finally(() => setL(false))
  }, [])
  const items = tfs?.timeframes || []
  if (loading) return <div className="p-8">Loading...</div>
  if (items.length === 0) return <div className="p-8 text-center text-[10px]">No timeframe data</div>
  return (
    <div className="border rounded-lg overflow-hidden">
      <table className="w-full text-[10px]">
        <thead><tr className="bg-muted/30 border-b">
          <th className="text-left px-3 py-2">Timeframe</th>
          <th className="text-right px-3 py-2">Trades</th>
          <th className="text-right px-3 py-2">Wins</th>
          <th className="text-right px-3 py-2">Win Rate</th>
          <th className="text-right px-3 py-2">P&L</th>
          <th className="text-left px-3 py-2">Sample</th>
        </tr></thead>
        <tbody className="divide-y">
          {items.map((tf: any, i: number) => (
            <tr key={i} className="hover:bg-muted/20">
              <td className="px-3 py-1.5 font-medium">{tf.timeframe}</td>
              <td className="px-3 py-1.5 text-right font-mono">{tf.trade_count}</td>
              <td className="px-3 py-1.5 text-right font-mono">{tf.win_count}</td>
              <td className={`px-3 py-1.5 text-right font-mono ${tf.win_rate >= 50 ? "text-emerald-500" : "text-red-500"}`}>{tf.win_rate}%</td>
              <td className={`px-3 py-1.5 text-right font-mono ${(tf.net_pnl || 0) >= 0 ? "text-emerald-500" : "text-red-500"}`}>${(tf.net_pnl || 0).toFixed(2)}</td>
              <td className="px-3 py-1.5 text-muted-foreground">{tf.sample_level?.replace(/_/g, " ")}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}

function SymbolTab() {
  const [syms, setSyms] = useState<any>(null); const [loading, setL] = useState(true)
  useEffect(() => {
    performanceService.getSymbols().then(setSyms).catch(() => {}).finally(() => setL(false))
  }, [])
  const items = syms?.symbols || []
  if (loading) return <div className="p-8">Loading...</div>
  if (items.length === 0) return <div className="p-8 text-center text-[10px]">No symbol data</div>
  return (
    <div className="border rounded-lg overflow-hidden">
      <table className="w-full text-[10px]">
        <thead><tr className="bg-muted/30 border-b">
          <th className="text-left px-3 py-2">Symbol</th>
          <th className="text-right px-3 py-2">Trades</th>
          <th className="text-right px-3 py-2">Wins</th>
          <th className="text-right px-3 py-2">Win Rate</th>
          <th className="text-right px-3 py-2">P&L</th>
        </tr></thead>
        <tbody className="divide-y">
          {items.map((s: any, i: number) => (
            <tr key={i} className="hover:bg-muted/20">
              <td className="px-3 py-1.5 font-medium">{s.symbol}</td>
              <td className="px-3 py-1.5 text-right font-mono">{s.trade_count}</td>
              <td className="px-3 py-1.5 text-right font-mono">{s.win_count}</td>
              <td className={`px-3 py-1.5 text-right font-mono ${s.win_rate >= 50 ? "text-emerald-500" : "text-red-500"}`}>{s.win_rate}%</td>
              <td className={`px-3 py-1.5 text-right font-mono ${(s.net_pnl || 0) >= 0 ? "text-emerald-500" : "text-red-500"}`}>${(s.net_pnl || 0).toFixed(2)}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}

function DirectionTab() {
  const [dirs, setDirs] = useState<any>(null); const [loading, setL] = useState(true)
  useEffect(() => {
    performanceService.getDirections().then(setDirs).catch(() => {}).finally(() => setL(false))
  }, [])
  const items = dirs?.directions || []
  if (loading) return <div className="p-8">Loading...</div>
  if (items.length === 0) return <div className="p-8 text-center text-[10px]">No direction data</div>
  return (
    <div className="grid grid-cols-2 gap-3">
      {items.map((d: any, i: number) => (
        <div key={i} className="rounded-lg border bg-card p-3">
          <div className="text-xs font-bold mb-1">{d.direction}</div>
          <div className="text-[10px] space-y-0.5">
            <div>Trades: {d.trade_count} | Wins: {d.win_count}</div>
            <div>Win Rate: <span className={d.win_rate >= 50 ? "text-emerald-500" : "text-red-500"}>{d.win_rate}%</span></div>
            <div>P&L: <span className={(d.net_pnl || 0) >= 0 ? "text-emerald-500" : "text-red-500"}>${(d.net_pnl || 0).toFixed(2)}</span></div>
          </div>
        </div>
      ))}
    </div>
  )
}

function BlockedTab() {
  const [blocked, setBlocked] = useState<any>(null); const [loading, setL] = useState(true)
  useEffect(() => {
    performanceService.getBlocked().then(setBlocked).catch(() => {}).finally(() => setL(false))
  }, [])
  if (loading) return <div className="p-8">Loading...</div>
  const reasons = blocked?.by_reason || []
  return (
    <div className="space-y-3">
      <MetricCard label="Total Blocked" value={String(blocked?.total_blocked || 0)} />
      {reasons.length === 0 && <div className="p-8 text-center text-[10px] text-muted-foreground">No blocked trades recorded</div>}
      {reasons.length > 0 && (
        <div className="border rounded-lg overflow-hidden">
          <table className="w-full text-[10px]">
            <thead><tr className="bg-muted/30 border-b">
              <th className="text-left px-3 py-2">Reason</th>
              <th className="text-right px-3 py-2">Count</th>
              <th className="text-right px-3 py-2">Percentage</th>
            </tr></thead>
            <tbody className="divide-y">
              {reasons.map((r: any, i: number) => (
                <tr key={i} className="hover:bg-muted/20">
                  <td className="px-3 py-1.5 font-medium">{r.reason}</td>
                  <td className="px-3 py-1.5 text-right font-mono">{r.count}</td>
                  <td className="px-3 py-1.5 text-right font-mono">{r.pct}%</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  )
}


