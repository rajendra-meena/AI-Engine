"use client"

import { useState, useEffect, useCallback } from "react"
import {
  Activity, GitBranch, TrendingUp, Target, BarChart3, AlertCircle,
  List, History, RefreshCw, CircleCheck, CircleX,
} from "lucide-react"
import { aiPerformanceService } from "@/services/aiPerformanceService"
import type {
  AIPerformanceDashboard, TradeEvaluation, CalibrationMetrics,
} from "@/services/aiPerformanceService"

type TabId = "overview" | "strategies" | "patterns" | "calibration" | "market" | "mistakes" | "trades" | "timeline"

export function AIPerformanceDashboard() {
  const [activeTab, setActiveTab] = useState<TabId>("overview")
  const [data, setData] = useState<AIPerformanceDashboard | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [trades, setTrades] = useState<TradeEvaluation[]>([])
  const [evalCount, setEvalCount] = useState(0)

  const fetchAll = useCallback(async () => {
    setError(null)
    try {
      const d = await aiPerformanceService.getDashboard()
      setData(d)
      const t = await aiPerformanceService.getTrades()
      setTrades(t.trades)
    } catch {
      setError("Failed to load AI performance data")
    }
    setLoading(false)
  }, [])

  useEffect(() => {
    const t = setTimeout(() => fetchAll(), 0)
    const interval = setInterval(fetchAll, 30000)
    return () => { clearTimeout(t); clearInterval(interval) }
  }, [fetchAll])

  const handleEvaluate = async () => {
    try {
      const result = await aiPerformanceService.evaluateAll()
      setEvalCount(result.evaluated)
      await fetchAll()
    } catch { setError("Evaluation failed") }
  }

  const tabs: { id: TabId; label: string; icon: React.ReactNode }[] = [
    { id: "overview", label: "Overview", icon: <Activity className="w-3.5 h-3.5" /> },
    { id: "strategies", label: "Strategies", icon: <GitBranch className="w-3.5 h-3.5" /> },
    { id: "patterns", label: "Patterns", icon: <TrendingUp className="w-3.5 h-3.5" /> },
    { id: "calibration", label: "Calibration", icon: <Target className="w-3.5 h-3.5" /> },
    { id: "market", label: "Market", icon: <BarChart3 className="w-3.5 h-3.5" /> },
    { id: "mistakes", label: "Mistakes", icon: <AlertCircle className="w-3.5 h-3.5" /> },
    { id: "trades", label: "Trades", icon: <List className="w-3.5 h-3.5" /> },
    { id: "timeline", label: "Timeline", icon: <History className="w-3.5 h-3.5" /> },
  ]

  const ov = data?.overview

  return (
    <div className="space-y-4">
      {/* Header */}
      <div className="flex items-center gap-2">
        <Activity className="w-5 h-5 text-primary" />
        <h1 className="text-lg font-bold">AI Performance Center</h1>
        <button onClick={handleEvaluate} className="ml-2 px-2 py-0.5 rounded text-[9px] font-medium bg-primary/10 text-primary hover:bg-primary/20 border border-primary/20">
          Run Evaluation
        </button>
        {evalCount > 0 && <span className="text-[9px] text-muted-foreground">Evaluated {evalCount} trades</span>}
        <button onClick={fetchAll} className="ml-auto p-1 rounded text-muted-foreground hover:text-foreground hover:bg-accent" disabled={loading}>
          <RefreshCw className={`w-3.5 h-3.5 ${loading ? "animate-spin" : ""}`} />
        </button>
      </div>

      {error && <div className="rounded border border-red-500/20 bg-red-500/5 p-2 text-[10px] text-red-600">{error}</div>}

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

      <div className="min-h-[400px]">
        {/* Overview Tab */}
        {activeTab === "overview" && (
          <div className="space-y-4">
            <div className="grid grid-cols-4 gap-3">
              <MetricCard label="Total Evaluated" value={String(ov?.total_evaluated ?? 0)} />
              <MetricCard label="Avg Score" value={`${ov?.avg_score ?? 0}/100`}
                color={(ov?.avg_score ?? 0) >= 65 ? "text-emerald-500" : (ov?.avg_score ?? 0) >= 45 ? "text-amber-500" : "text-red-500"} />
              <MetricCard label="Strategies" value={String(data?.strategies?.length ?? 0)} />
              <MetricCard label="Patterns Tracked" value={String(data?.patterns?.length ?? 0)} />
            </div>
            {ov?.outcome_distribution && Object.keys(ov.outcome_distribution).length > 0 && (
              <div className="rounded-lg border bg-card p-3">
                <div className="text-[9px] text-muted-foreground uppercase mb-2">Outcome Distribution</div>
                <div className="grid grid-cols-5 gap-2 text-[10px]">
                  {(Object.entries(ov.outcome_distribution) as [string, number][]).map(([cls, count]) => (
                    <div key={cls} className="text-center p-2 rounded bg-muted/20">
                      <div className={`text-lg font-bold font-mono ${cls === "Excellent" ? "text-emerald-500" : cls === "Good" ? "text-blue-500" : cls === "Average" ? "text-amber-500" : cls === "Poor" ? "text-orange-500" : "text-red-500"}`}>
                        {count}
                      </div>
                      <div className="text-[9px] text-muted-foreground">{cls}</div>
                    </div>
                  ))}
                </div>
              </div>
            )}
            {data?.calibration && (
              <div className="rounded-lg border bg-card p-3">
                <div className="text-[9px] text-muted-foreground uppercase mb-2">Calibration Status</div>
                <div className="grid grid-cols-4 gap-2 text-[10px]">
                  <div>ECE: <span className="font-mono">{data.calibration.ece}</span></div>
                  <div>MCE: <span className="font-mono">{data.calibration.mce}</span></div>
                  <div>Bias: <span className={`font-mono ${data.calibration.bias === "overconfident" ? "text-red-500" : data.calibration.bias === "underconfident" ? "text-amber-500" : "text-emerald-500"}`}>{data.calibration.bias}</span></div>
                  <div>Accuracy: <span className="font-mono">{data.calibration.confidence_accuracy}%</span></div>
                </div>
              </div>
            )}
            {data?.mistakes?.summary && (
              <div className="rounded-lg border bg-card p-3">
                <div className="text-[9px] text-muted-foreground uppercase mb-2">Mistake Summary</div>
                <div className="grid grid-cols-3 gap-2 text-[10px]">
                  <div>Total: <span className="font-mono">{data.mistakes.summary.total_count}</span></div>
                  <div>Most Common: <span className="font-mono">{data.mistakes.summary.most_common}</span></div>
                  <div>Total Impact: <span className="font-mono">{data.mistakes.summary.total_impact}</span></div>
                </div>
              </div>
            )}
          </div>
        )}

        {/* Strategies Tab */}
        {activeTab === "strategies" && (
          <div className="space-y-2">
            {(!data?.strategies || data.strategies.length === 0) ? (
              <div className="p-8 text-center text-[10px] text-muted-foreground">No strategy data available</div>
            ) : (
              <div className="border rounded-lg overflow-hidden">
                <table className="w-full text-[10px]">
                  <thead><tr className="bg-muted/30 border-b">
                    <th className="text-left px-3 py-2">Strategy</th>
                    <th className="text-right px-3 py-2">Trades</th>
                    <th className="text-right px-3 py-2">Win Rate</th>
                    <th className="text-right px-3 py-2">Profit Factor</th>
                    <th className="text-right px-3 py-2">Expectancy</th>
                    <th className="text-right px-3 py-2">Sharpe</th>
                    <th className="text-right px-3 py-2">Max DD</th>
                    <th className="text-right px-3 py-2">Avg Hold</th>
                  </tr></thead>
                  <tbody className="divide-y">
                    {data.strategies.map((s) => (
                      <tr key={s.strategy_id} className="hover:bg-muted/20">
                        <td className="px-3 py-1.5 font-medium">{s.strategy_name}</td>
                        <td className="px-3 py-1.5 text-right font-mono">{s.total_trades}</td>
                        <td className={`px-3 py-1.5 text-right font-mono ${s.win_rate >= 50 ? "text-emerald-500" : "text-red-500"}`}>{s.win_rate}%</td>
                        <td className="px-3 py-1.5 text-right font-mono">{s.profit_factor}</td>
                        <td className={`px-3 py-1.5 text-right font-mono ${s.expectancy >= 0 ? "text-emerald-500" : "text-red-500"}`}>{s.expectancy}</td>
                        <td className="px-3 py-1.5 text-right font-mono">{s.sharpe_ratio ?? "—"}</td>
                        <td className="px-3 py-1.5 text-right font-mono text-red-500">{s.max_drawdown}%</td>
                        <td className="px-3 py-1.5 text-right font-mono">{s.avg_holding_hours}h</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        )}

        {/* Patterns Tab */}
        {activeTab === "patterns" && (
          <div className="space-y-2">
            {(!data?.patterns || data.patterns.length === 0) ? (
              <div className="p-8 text-center text-[10px] text-muted-foreground">No pattern data available</div>
            ) : (
              <div className="border rounded-lg overflow-hidden">
                <table className="w-full text-[10px]">
                  <thead><tr className="bg-muted/30 border-b">
                    <th className="text-left px-3 py-2">Pattern</th>
                    <th className="text-right px-3 py-2">Occurrences</th>
                    <th className="text-right px-3 py-2">Wins</th>
                    <th className="text-right px-3 py-2">Losses</th>
                    <th className="text-right px-3 py-2">Win Rate</th>
                    <th className="text-right px-3 py-2">Avg Return</th>
                    <th className="text-right px-3 py-2">Failure Rate</th>
                    <th className="text-right px-3 py-2">Avg Duration</th>
                  </tr></thead>
                  <tbody className="divide-y">
                    {data.patterns.map((p) => (
                      <tr key={p.pattern_name} className="hover:bg-muted/20">
                        <td className="px-3 py-1.5 font-medium capitalize">{p.pattern_name.replace(/_/g, " ")}</td>
                        <td className="px-3 py-1.5 text-right font-mono">{p.total_occurrences}</td>
                        <td className="px-3 py-1.5 text-right font-mono text-emerald-500">{p.win_count}</td>
                        <td className="px-3 py-1.5 text-right font-mono text-red-500">{p.loss_count}</td>
                        <td className={`px-3 py-1.5 text-right font-mono ${p.win_rate >= 50 ? "text-emerald-500" : "text-red-500"}`}>{p.win_rate}%</td>
                        <td className={`px-3 py-1.5 text-right font-mono ${p.avg_return >= 0 ? "text-emerald-500" : "text-red-500"}`}>{p.avg_return}</td>
                        <td className="px-3 py-1.5 text-right font-mono">{p.failure_rate}%</td>
                        <td className="px-3 py-1.5 text-right font-mono">{p.avg_duration_hours}h</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        )}

        {/* Calibration Tab */}
        {activeTab === "calibration" && (
          <CalibrationTab data={data?.calibration ?? null} />
        )}

        {/* Market Tab */}
        {activeTab === "market" && (
          <div className="space-y-4">
            {(!data?.market_conditions || data.market_conditions.length === 0) ? (
              <div className="p-8 text-center text-[10px] text-muted-foreground">No market condition data</div>
            ) : (
              ["volatility", "volume", "session", "trending"].map((ctype) => {
                const items = data.market_conditions.filter(c => c.condition_type === ctype)
                if (items.length === 0) return null
                return (
                  <div key={ctype} className="rounded-lg border bg-card p-3">
                    <div className="text-[9px] text-muted-foreground uppercase mb-2">{ctype}</div>
                    <div className="grid grid-cols-3 gap-2 text-[10px]">
                      {items.map((c) => (
                        <div key={c.condition_value} className="flex justify-between p-1.5 rounded bg-muted/20">
                          <span className="font-medium">{c.condition_value}</span>
                          <span className={`font-mono ${c.win_rate >= 50 ? "text-emerald-500" : "text-red-500"}`}>{c.win_rate}% ({c.total_trades})</span>
                        </div>
                      ))}
                    </div>
                  </div>
                )
              })
            )}
          </div>
        )}

        {/* Mistakes Tab */}
        {activeTab === "mistakes" && (
          <div className="space-y-4">
            {data?.mistakes?.summary ? (
              <div className="grid grid-cols-4 gap-3">
                <MetricCard label="Total Mistakes" value={String(data.mistakes.summary.total_count)} />
                <MetricCard label="Most Common" value={data.mistakes.summary.most_common} />
                <MetricCard label="Total Impact" value={String(data.mistakes.summary.total_impact)} />
                <MetricCard label="Most Severe" value={data.mistakes.summary.by_severity?.critical ? `Critical: ${data.mistakes.summary.by_severity.critical}` : "None"} color={data.mistakes.summary.by_severity?.critical ? "text-red-500" : "text-emerald-500"} />
              </div>
            ) : (
              <div className="p-8 text-center text-[10px] text-muted-foreground">No mistakes classified</div>
            )}
            {data?.mistakes?.mistakes && data.mistakes.mistakes.length > 0 && (
              <div className="border rounded-lg overflow-hidden">
                <table className="w-full text-[10px]">
                  <thead><tr className="bg-muted/30 border-b">
                    <th className="text-left px-3 py-2">Type</th>
                    <th className="text-left px-3 py-2">Severity</th>
                    <th className="text-left px-3 py-2">Description</th>
                    <th className="text-right px-3 py-2">Impact</th>
                    <th className="text-left px-3 py-2">Lesson</th>
                  </tr></thead>
                  <tbody className="divide-y">
                    {data.mistakes.mistakes.slice(0, 20).map((m) => (
                      <tr key={m.id || m.prediction_id} className="hover:bg-muted/20">
                        <td className="px-3 py-1.5 font-medium capitalize">{m.mistake_type.replace(/_/g, " ")}</td>
                        <td className={`px-3 py-1.5 font-medium ${m.severity === "critical" ? "text-red-500" : m.severity === "major" ? "text-amber-500" : "text-muted-foreground"}`}>{m.severity}</td>
                        <td className="px-3 py-1.5 text-muted-foreground max-w-[250px] truncate">{m.description}</td>
                        <td className="px-3 py-1.5 text-right font-mono">{m.impact}</td>
                        <td className="px-3 py-1.5 text-muted-foreground max-w-[200px] truncate">{m.lesson ?? "—"}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        )}

        {/* Trades Tab */}
        {activeTab === "trades" && (
          <div className="space-y-2">
            {trades.length === 0 ? (
              <div className="p-8 text-center text-[10px] text-muted-foreground">No trades evaluated yet. Click "Run Evaluation" to start.</div>
            ) : (
              <div className="border rounded-lg overflow-hidden">
                <table className="w-full text-[10px]">
                  <thead><tr className="bg-muted/30 border-b">
                    <th className="text-left px-3 py-2">ID</th>
                    <th className="text-right px-3 py-2">Score</th>
                    <th className="text-left px-3 py-2">Outcome</th>
                    <th className="text-right px-3 py-2">Entry</th>
                    <th className="text-right px-3 py-2">Exit</th>
                    <th className="text-right px-3 py-2">SL</th>
                    <th className="text-right px-3 py-2">Target</th>
                    <th className="text-right px-3 py-2">MFE/MAE</th>
                    <th className="text-right px-3 py-2">Slippage</th>
                  </tr></thead>
                  <tbody className="divide-y">
                    {trades.map((t) => (
                      <tr key={t.id} className="hover:bg-muted/20">
                        <td className="px-3 py-1.5 font-mono text-muted-foreground text-[9px]">{t.prediction_id?.slice(-8)}</td>
                        <td className="px-3 py-1.5 text-right font-mono">{t.overall_score}</td>
                        <td className="px-3 py-1.5">
                          <span className={`px-1.5 py-0.5 rounded text-[8px] font-medium ${
                            t.outcome_class === "Excellent" ? "bg-emerald-500/10 text-emerald-500" :
                            t.outcome_class === "Good" ? "bg-blue-500/10 text-blue-500" :
                            t.outcome_class === "Average" ? "bg-amber-500/10 text-amber-500" :
                            t.outcome_class === "Poor" ? "bg-orange-500/10 text-orange-500" :
                            "bg-red-500/10 text-red-500"
                          }`}>{t.outcome_class}</span>
                        </td>
                        <td className={`px-3 py-1.5 text-right font-mono ${t.entry_accuracy >= 70 ? "text-emerald-500" : "text-red-500"}`}>{t.entry_accuracy}</td>
                        <td className={`px-3 py-1.5 text-right font-mono ${t.exit_quality >= 70 ? "text-emerald-500" : "text-red-500"}`}>{t.exit_quality}</td>
                        <td className={`px-3 py-1.5 text-right font-mono ${t.sl_quality >= 70 ? "text-emerald-500" : "text-red-500"}`}>{t.sl_quality}</td>
                        <td className={`px-3 py-1.5 text-right font-mono ${t.target_quality >= 70 ? "text-emerald-500" : "text-red-500"}`}>{t.target_quality}</td>
                        <td className="px-3 py-1.5 text-right font-mono">{t.mfe_mae_ratio}</td>
                        <td className="px-3 py-1.5 text-right font-mono">{t.slippage_impact}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        )}

        {/* Timeline Tab */}
        {activeTab === "timeline" && (
          <div className="space-y-4">
            <div className="rounded-lg border bg-card p-3">
              <div className="text-[9px] text-muted-foreground uppercase mb-2">Performance Timeline</div>
              <p className="text-[10px] text-muted-foreground">
                Trade evaluation timeline will display here as more trades are evaluated.
                Currently {ov?.total_evaluated ?? 0} trades evaluated.
              </p>
            </div>
            {trades.length > 0 && (
              <div className="rounded-lg border bg-card p-3">
                <div className="text-[9px] text-muted-foreground uppercase mb-2">Recent Scores</div>
                <div className="space-y-1">
                  {trades.slice(0, 15).map((t) => (
                    <div key={t.id} className="flex items-center gap-2 text-[10px]">
                      <span className="font-mono text-muted-foreground w-16">{t.evaluated_at?.split("T")[0]}</span>
                      <div className="flex-1 h-2 rounded-full bg-muted/30 overflow-hidden">
                        <div className={`h-full rounded-full ${t.overall_score >= 65 ? "bg-emerald-500" : t.overall_score >= 45 ? "bg-amber-500" : "bg-red-500"}`}
                          style={{ width: `${t.overall_score}%` }} />
                      </div>
                      <span className="font-mono w-8 text-right">{t.overall_score}</span>
                      <span className={`w-16 text-right text-[8px] font-medium ${
                        t.outcome_class === "Excellent" ? "text-emerald-500" : t.outcome_class === "Good" ? "text-blue-500" : t.outcome_class === "Average" ? "text-amber-500" : "text-red-500"
                      }`}>{t.outcome_class}</span>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  )
}

/* ─── Calibration Tab ─── */

function CalibrationTab({ data }: { data: CalibrationMetrics | null }) {
  if (!data) {
    return <div className="p-8 text-center text-[10px] text-muted-foreground">No calibration data</div>
  }

  return (
    <div className="space-y-4">
      <div className="grid grid-cols-4 gap-3">
        <MetricCard label="ECE" value={String(data.ece)} color={data.ece <= 10 ? "text-emerald-500" : data.ece <= 20 ? "text-amber-500" : "text-red-500"} />
        <MetricCard label="MCE" value={String(data.mce)} color={data.mce <= 15 ? "text-emerald-500" : data.mce <= 30 ? "text-amber-500" : "text-red-500"} />
        <MetricCard label="Bias" value={data.bias} color={data.bias === "calibrated" ? "text-emerald-500" : data.bias === "overconfident" ? "text-red-500" : "text-amber-500"} />
        <MetricCard label="Conf. Accuracy" value={`${data.confidence_accuracy}%`} color={data.confidence_accuracy >= 70 ? "text-emerald-500" : "text-amber-500"} />
      </div>

      <div className="rounded-lg border bg-card p-3">
        <div className="text-[9px] text-muted-foreground uppercase mb-2">Reliability Curve</div>
        {data.reliability_curve && data.reliability_curve.length > 0 ? (
          <div className="space-y-1.5">
            {data.reliability_curve.map((b, i) => (
              <div key={i}>
                <div className="flex justify-between text-[10px] mb-0.5">
                  <span className="font-medium w-16">{b.bucket_label}</span>
                  <span className="text-muted-foreground">n={b.count}</span>
                </div>
                <div className="flex items-center gap-2">
                  {/* Predicted confidence bar */}
                  <div className="flex-1 h-3 rounded bg-muted/30 overflow-hidden relative">
                    <div className="absolute inset-0 h-full rounded bg-indigo-500/30" style={{ width: `${b.avg_confidence}%` }} />
                    <div className="absolute inset-0 h-full rounded bg-emerald-500/60" style={{ width: `${b.actual_accuracy}%` }} />
                  </div>
                  <span className="text-[9px] font-mono w-16 text-right">{b.avg_confidence}/{b.actual_accuracy}</span>
                </div>
                {b.calibration_error > 0 && (
                  <div className="text-[8px] text-muted-foreground text-right">err: {b.calibration_error}</div>
                )}
              </div>
            ))}
          </div>
        ) : (
          <p className="text-[10px] text-muted-foreground">No reliability curve data</p>
        )}
      </div>

      <div className="rounded-lg border bg-card p-3">
        <div className="text-[9px] text-muted-foreground uppercase mb-1">Interpretation</div>
        <p className="text-[10px] text-muted-foreground">
          {data.bias === "calibrated" && "The AI is well-calibrated — confidence levels match actual success rates."}
          {data.bias === "overconfident" && `The AI tends to be overconfident by ${Math.abs(data.bias_magnitude).toFixed(1)} points on average. Consider adjusting confidence thresholds upward.`}
          {data.bias === "underconfident" && `The AI tends to be underconfident by ${Math.abs(data.bias_magnitude).toFixed(1)} points. Actual success rates exceed predictions.`}
          {' '}ECE of {data.ece} means average calibration error across all confidence levels.
        </p>
      </div>
    </div>
  )
}

/* ─── MetricCard ─── */

function MetricCard({ label, value, color }: { label: string; value: string; color?: string }) {
  return (
    <div className="rounded-lg border bg-card p-3 text-center">
      <div className="text-[9px] text-muted-foreground uppercase tracking-wider">{label}</div>
      <div className={`text-lg font-bold font-mono mt-0.5 ${color || ""}`}>{value}</div>
    </div>
  )
}
