"use client"

import { useState, useEffect, useCallback } from "react"
import {
  FlaskConical, BarChart3, GitCompare, Layers, TrendingUp, PieChart, FileText,
  RefreshCw, AlertTriangle, CheckCircle, XCircle, Shield, Target, DollarSign,
} from "lucide-react"
import { researchService } from "@/services/researchService"

type TabId = "home" | "validation" | "walkforward" | "montecarlo" | "sensitivity" | "metrics" | "warnings" | "history" | "compare"

export function ResearchDashboard() {
  const [activeTab, setActiveTab] = useState<TabId>("home")
  const [validations, setValidations] = useState<any[]>([])
  const [selectedVal, setSelectedVal] = useState<any>(null)
  const [mcResult, setMcResult] = useState<any>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const fetchHistory = useCallback(async () => {
    try {
      const h = await researchService.getValidationHistory()
      setValidations(h.validations || [])
    } catch { /* ignore */ }
  }, [])

  useEffect(() => { const t = setTimeout(() => fetchHistory(), 0); return () => clearTimeout(t) }, [fetchHistory])

  const handleSelectValidation = async (val: any) => {
    setSelectedVal(val)
    setActiveTab("validation")
  }

  const handleRunValidation = async () => {
    setLoading(true); setError(null)
    try {
      const result = await researchService.runValidation({
        metrics: { total_trades: 0, win_rate: 0, net_pnl: 0, profit_factor: 0, expectancy: 0, max_drawdown_pct: 0 },
        trades: [], candles: [],
      })
      setSelectedVal(result)
      await fetchHistory()
      setActiveTab("validation")
    } catch { setError("Validation failed") }
    setLoading(false)
  }

  const handleRunMC = async () => {
    setLoading(true); setError(null)
    try {
      const mockTrades = Array.from({ length: 100 }, (_, i) => ({
        net_pnl: Math.random() * 500 - 200,
        pnl: Math.random() * 500 - 200,
      }))
      const result = await researchService.runMonteCarloSingle(mockTrades, 5000)
      setMcResult(result)
      setActiveTab("montecarlo")
    } catch { setError("Monte Carlo failed") }
    setLoading(false)
  }

  const handleDelete = async (valId: string) => {
    await researchService.deleteValidation(valId)
    if (selectedVal?.validation_id === valId) setSelectedVal(null)
    await fetchHistory()
  }

  const tabs = [
    { id: "home" as TabId, label: "Home", icon: <FlaskConical className="w-3.5 h-3.5" /> },
    { id: "validation" as TabId, label: "Validation", icon: <Shield className="w-3.5 h-3.5" /> },
    { id: "walkforward" as TabId, label: "Walk Forward", icon: <GitCompare className="w-3.5 h-3.5" /> },
    { id: "montecarlo" as TabId, label: "Monte Carlo", icon: <Layers className="w-3.5 h-3.5" /> },
    { id: "sensitivity" as TabId, label: "Sensitivity", icon: <TrendingUp className="w-3.5 h-3.5" /> },
    { id: "metrics" as TabId, label: "Metrics", icon: <BarChart3 className="w-3.5 h-3.5" /> },
    { id: "warnings" as TabId, label: "Warnings", icon: <AlertTriangle className="w-3.5 h-3.5" /> },
    { id: "history" as TabId, label: "History", icon: <FileText className="w-3.5 h-3.5" /> },
    { id: "compare" as TabId, label: "Compare", icon: <GitCompare className="w-3.5 h-3.5" /> },
  ]

  const s = selectedVal || {}
  const metrics = s.metrics || {}
  const m = metrics

  return (
    <div className="space-y-4">
      <div className="flex items-center gap-2">
        <FlaskConical className="w-5 h-5 text-primary" />
        <h1 className="text-lg font-bold">Strategy Research Lab</h1>
        <button onClick={handleRunValidation} disabled={loading}
          className="ml-2 px-3 py-1.5 rounded text-[10px] font-medium bg-primary/20 text-primary hover:bg-primary/30">
          {loading ? "Running..." : "Run Validation"}
        </button>
        <button onClick={fetchHistory} className="ml-auto p-1 rounded text-muted-foreground hover:bg-accent">
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

      {activeTab === "home" && (
        <div className="grid grid-cols-3 gap-3">
          <HomeCard icon={<Shield />} title="Run Validation" desc="Complete strategy validation with walk-forward, Monte Carlo, and sensitivity" onClick={() => { handleRunValidation() }} />
          <HomeCard icon={<GitCompare />} title="Walk Forward" desc="Test strategy across sequential time windows" onClick={() => setActiveTab("walkforward")} />
          <HomeCard icon={<Layers />} title="Monte Carlo" desc="Assess robustness through randomized trade resampling" onClick={() => { handleRunMC() }} />
          <HomeCard icon={<TrendingUp />} title="Sensitivity" desc="Test parameter stability across configurations" onClick={() => setActiveTab("sensitivity")} />
          <HomeCard icon={<BarChart3 />} title="Advanced Metrics" desc="Sharpe, Sortino, Calmar, MAE/MFE analysis" onClick={() => setActiveTab("metrics")} />
          <HomeCard icon={<FileText />} title="History & Compare" desc="Browse past validations and compare strategies" onClick={() => setActiveTab("history")} />
        </div>
      )}

      {activeTab === "validation" && (
        <div className="space-y-4">
          {!selectedVal ? (
            <div className="p-8 text-center text-[10px] text-muted-foreground">Select or run a validation</div>
          ) : (
            <>
              <div className="grid grid-cols-4 gap-3">
                <MetricCard label="Validation Score" value={`${s.validation_score || 0}/100`}
                  color={(s.validation_score || 0) >= 75 ? "text-emerald-500" : (s.validation_score || 0) >= 50 ? "text-amber-500" : "text-red-500"} />
                <MetricCard label="Classification" value={(s.classification || "N/A").toUpperCase()}
                  color={s.classification === "excellent" || s.classification === "strong" ? "text-emerald-500" : s.classification === "acceptable" ? "text-amber-500" : "text-red-500"} />
                <MetricCard label="Sample Size" value={String(s.sample_size || 0)} />
                <MetricCard label="Sample Level" value={(s.sample_level || "N/A").replace(/_/g, " ")} />
              </div>
              <div className="grid grid-cols-4 gap-3">
                <MetricCard label="Win Rate" value={`${m.win_rate || 0}%`} color={(m.win_rate || 0) >= 50 ? "text-emerald-500" : "text-red-500"} />
                <MetricCard label="Net P&L" value={`$${(m.net_pnl || 0).toFixed(2)}`} color={(m.net_pnl || 0) >= 0 ? "text-emerald-500" : "text-red-500"} />
                <MetricCard label="Profit Factor" value={String(m.profit_factor || 0)} color={(m.profit_factor || 0) >= 1.5 ? "text-emerald-500" : "text-amber-500"} />
                <MetricCard label="Max DD" value={`${m.max_drawdown_pct || 0}%`} color={(m.max_drawdown_pct || 0) <= 15 ? "text-emerald-500" : "text-red-500"} />
              </div>
              <div className="rounded-lg border p-4">
                <h3 className="text-xs font-bold mb-2 flex items-center gap-2"><Shield className="w-3.5 h-3.5" /> Breakdown</h3>
                <div className="grid grid-cols-3 gap-2 text-[10px]">
                  {Object.entries(s.breakdown || {}).map(([k, v]: any) => (
                    <div key={k} className="flex justify-between"><span className="text-muted-foreground">{k.replace(/_/g, " ")}</span><span className="font-mono">{v}</span></div>
                  ))}
                </div>
              </div>
              {s.warnings?.length > 0 && (
                <div className="rounded-lg border p-4">
                  <h3 className="text-xs font-bold mb-2 flex items-center gap-2"><AlertTriangle className="w-3.5 h-3.5 text-amber-500" /> Warnings</h3>
                  <div className="space-y-1">
                    {s.warnings.map((w: any, i: number) => (
                      <div key={i} className={`text-[10px] p-2 rounded ${
                        w.severity === "critical" ? "bg-red-500/10 text-red-600" :
                        w.severity === "warning" ? "bg-amber-500/10 text-amber-600" :
                        "bg-blue-500/10 text-blue-600"
                      }`}>{w.severity.toUpperCase()}: {w.message}</div>
                    ))}
                  </div>
                </div>
              )}
            </>
          )}
        </div>
      )}

      {activeTab === "walkforward" && (
        <div className="space-y-3">
          <div className="p-4 rounded-lg border bg-card">
            <h3 className="text-xs font-bold mb-3">Walk-Forward Analysis</h3>
            <p className="text-[10px] text-muted-foreground">Walk-forward validation tests strategy performance across sequential time windows. Each window has a training period and an out-of-sample validation period.</p>
          </div>
          {s.walk_forward?.windows?.length > 0 ? (
            <div className="border rounded-lg overflow-hidden">
              <table className="w-full text-[10px]">
                <thead><tr className="bg-muted/30 border-b">
                  <th className="text-left px-3 py-2">Window</th>
                  <th className="text-left px-3 py-2">Train</th>
                  <th className="text-left px-3 py-2">Validate</th>
                  <th className="text-right px-3 py-2">Status</th>
                </tr></thead>
                <tbody className="divide-y">
                  {s.walk_forward.windows.map((w: any, i: number) => (
                    <tr key={i} className="hover:bg-muted/20">
                      <td className="px-3 py-1.5 font-medium">{w.window_id || i + 1}</td>
                      <td className="px-3 py-1.5 text-muted-foreground">{w.train_start?.split("T")[0]} → {w.train_end?.split("T")[0]}</td>
                      <td className="px-3 py-1.5 text-muted-foreground">{w.val_start?.split("T")[0]} → {w.val_end?.split("T")[0]}</td>
                      <td className="px-3 py-1.5 text-right">{w.status}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ) : (
            <div className="p-8 text-center text-[10px] text-muted-foreground">No walk-forward data. Run a validation first.</div>
          )}
          {s.walk_forward?.generalization && (
            <div className="rounded-lg border p-3">
              <h4 className="text-[10px] font-bold mb-1">Generalization</h4>
              <div className="text-[10px]">
                <span className="text-muted-foreground">Classification: </span>
                <span className={`font-medium ${
                  s.walk_forward.generalization.classification === "strong" ? "text-emerald-500" :
                  s.walk_forward.generalization.classification === "acceptable" ? "text-amber-500" : "text-red-500"
                }`}>{s.walk_forward.generalization.classification}</span>
                <span className="ml-4 text-muted-foreground">Score: </span>
                <span className="font-mono">{s.walk_forward.generalization.score}</span>
              </div>
            </div>
          )}
        </div>
      )}

      {activeTab === "montecarlo" && (
        <div className="space-y-4">
          {mcResult ? (
            <>
              <div className="grid grid-cols-4 gap-3">
                <MetricCard label="Simulations" value={String(mcResult.simulations || 0)} />
                <MetricCard label="Median Equity" value={`$${(mcResult.median_final_equity || 0).toFixed(2)}`} />
                <MetricCard label="Worst Case" value={`$${(mcResult.worst_final_equity || 0).toFixed(2)}`} color="text-red-500" />
                <MetricCard label="Best Case" value={`$${(mcResult.best_final_equity || 0).toFixed(2)}`} color="text-emerald-500" />
              </div>
              <div className="grid grid-cols-4 gap-3">
                <MetricCard label="Prob of Loss" value={`${(mcResult.probability_of_loss || 0).toFixed(1)}%`}
                  color={(mcResult.probability_of_loss || 0) < 30 ? "text-emerald-500" : "text-red-500"} />
                <MetricCard label="Prob of Ruin" value={`${(mcResult.probability_of_ruin || 0).toFixed(1)}%`}
                  color={(mcResult.probability_of_ruin || 0) < 10 ? "text-emerald-500" : "text-red-500"} />
                <MetricCard label="Median DD" value={`${(mcResult.median_max_drawdown || 0).toFixed(1)}%`}
                  color={(mcResult.median_max_drawdown || 0) < 15 ? "text-emerald-500" : "text-red-500"} />
                <MetricCard label="Worst DD" value={`${(mcResult.worst_max_drawdown || 0).toFixed(1)}%`} color="text-red-500" />
              </div>
              <div className="grid grid-cols-2 gap-3">
                <MetricCard label="95th %ile Drawdown" value={`${(mcResult.pct_95_drawdown || 0).toFixed(1)}%`} color={(mcResult.pct_95_drawdown || 0) < 20 ? "text-emerald-500" : "text-red-500"} />
                <MetricCard label="99th %ile Drawdown" value={`${(mcResult.pct_99_drawdown || 0).toFixed(1)}%`} color={(mcResult.pct_99_drawdown || 0) < 30 ? "text-emerald-500" : "text-red-500"} />
              </div>
            </>
          ) : (
            <div className="p-8 text-center text-[10px] text-muted-foreground">Run a simulation to see results <button onClick={handleRunMC} className="text-primary underline">Run Now</button></div>
          )}
        </div>
      )}

      {activeTab === "sensitivity" && (
        <div className="rounded-lg border p-6 text-center text-[10px] text-muted-foreground">
          <p>Parameter sensitivity analysis available through complete validation.</p>
          <button onClick={handleRunValidation} className="mt-2 px-3 py-1.5 rounded text-[10px] font-medium bg-primary/20 text-primary hover:bg-primary/30">Run Full Validation</button>
        </div>
      )}

      {activeTab === "metrics" && (
        <div className="space-y-4">
          <div className="grid grid-cols-4 gap-3">
            <MetricCard label="Sharpe Ratio" value={String((s.breakdown?.sharpe_score || 0))} color={(s.breakdown?.sharpe_score || 0) >= 0.5 ? "text-emerald-500" : "text-amber-500"} />
            <MetricCard label="Expectancy" value={`$${(m.expectancy || 0).toFixed(2)}`} color={(m.expectancy || 0) > 0 ? "text-emerald-500" : "text-red-500"} />
            <MetricCard label="Avg Trade" value={`$${(m.avg_trade || 0).toFixed(2)}`} color={(m.avg_trade || 0) > 0 ? "text-emerald-500" : "text-red-500"} />
            <MetricCard label="Avg R" value={String(m.avg_r || 0)} color={(m.avg_r || 0) > 0 ? "text-emerald-500" : "text-red-500"} />
          </div>
        </div>
      )}

      {activeTab === "warnings" && <WarningsTab report={s} />}
      {activeTab === "history" && <HistoryTab validations={validations} onSelect={handleSelectValidation} onDelete={handleDelete} />}
      {activeTab === "compare" && <CompareTab />}
    </div>
  )
}

function HomeCard({ icon, title, desc, onClick }: { icon: React.ReactNode; title: string; desc: string; onClick: () => void }) {
  return (
    <button onClick={onClick} className="rounded-lg border bg-card p-4 text-left hover:bg-accent transition-colors space-y-2">
      <div className="text-primary w-5 h-5">{icon}</div>
      <div className="text-xs font-medium">{title}</div>
      <div className="text-[9px] text-muted-foreground">{desc}</div>
    </button>
  )
}

function MetricCard({ label, value, color }: { label: string; value: string; color?: string }) {
  return <div className="rounded-lg border bg-card p-3">
    <div className="text-[9px] text-muted-foreground uppercase tracking-wider">{label}</div>
    <div className={`text-lg font-bold font-mono mt-0.5 ${color || ""}`}>{value}</div>
  </div>
}

function WarningsTab({ report }: { report: any }) {
  const warnings = report?.warnings || []
  if (warnings.length === 0) return <div className="p-8 text-center text-[10px] text-muted-foreground">No warnings</div>
  const critical = warnings.filter((w: any) => w.severity === "critical")
  const warning = warnings.filter((w: any) => w.severity === "warning")
  const info = warnings.filter((w: any) => w.severity === "info")
  return (
    <div className="space-y-3">
      {critical.length > 0 && <div className="rounded-lg border border-red-500/20 bg-red-500/5 p-3"><h4 className="text-xs font-bold text-red-600 mb-2">Critical ({critical.length})</h4>{critical.map((w: any, i: number) => <div key={i} className="text-[10px] text-red-600 py-1">{w.code}: {w.message}</div>)}</div>}
      {warning.length > 0 && <div className="rounded-lg border border-amber-500/20 bg-amber-500/5 p-3"><h4 className="text-xs font-bold text-amber-600 mb-2">Warnings ({warning.length})</h4>{warning.map((w: any, i: number) => <div key={i} className="text-[10px] text-amber-600 py-1">{w.code}: {w.message}</div>)}</div>}
      {info.length > 0 && <div className="rounded-lg border p-3"><h4 className="text-xs font-bold mb-2">Info ({info.length})</h4>{info.map((w: any, i: number) => <div key={i} className="text-[10px] text-muted-foreground py-1">{w.message}</div>)}</div>}
    </div>
  )
}

function HistoryTab({ validations, onSelect, onDelete }: { validations: any[]; onSelect: (v: any) => void; onDelete: (id: string) => void }) {
  if (validations.length === 0) return <div className="p-8 text-center text-[10px] text-muted-foreground">No validation runs yet</div>
  return (
    <div className="border rounded-lg overflow-hidden">
      <table className="w-full text-[10px]">
        <thead><tr className="bg-muted/30 border-b">
          <th className="text-left px-3 py-2">ID</th>
          <th className="text-right px-3 py-2">Score</th>
          <th className="text-left px-3 py-2">Classification</th>
          <th className="text-left px-3 py-2">Sample Level</th>
          <th className="text-left px-3 py-2">Created</th>
          <th className="text-right px-3 py-2">Actions</th>
        </tr></thead>
        <tbody className="divide-y">
          {validations.map((v: any, i: number) => (
            <tr key={v.validation_id || i} className="hover:bg-muted/20 cursor-pointer" onClick={() => onSelect(v)}>
              <td className="px-3 py-1.5 font-mono text-muted-foreground">{v.validation_id?.slice(-8) || "—"}</td>
              <td className="px-3 py-1.5 text-right font-mono">{v.validation_score ?? "—"}</td>
              <td className="px-3 py-1.5">
                <span className={`px-1.5 py-0.5 rounded text-[8px] font-medium ${
                  v.classification === "excellent" || v.classification === "strong" ? "bg-emerald-500/10 text-emerald-500" :
                  v.classification === "acceptable" ? "bg-amber-500/10 text-amber-500" :
                  "bg-red-500/10 text-red-500"
                }`}>{v.classification}</span>
              </td>
              <td className="px-3 py-1.5 text-muted-foreground">{v.sample_level?.replace(/_/g, " ")}</td>
              <td className="px-3 py-1.5 text-muted-foreground">{v.created_at?.split("T")[0]}</td>
              <td className="px-3 py-1.5 text-right">
                <button onClick={e => { e.stopPropagation(); onDelete(v.validation_id) }} className="text-red-500 hover:text-red-700 text-[9px]">Delete</button>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}

function CompareTab() {
  return <div className="p-8 text-center text-[10px] text-muted-foreground">Select validations from history to compare (up to 5).</div>
}
