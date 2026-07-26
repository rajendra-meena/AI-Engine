"use client"

import { useState, useMemo } from "react"
import { Activity, GitBranch, History, Route, BarChart3, MessageSquare, RefreshCw } from "lucide-react"
import { useRegime, useRegimeHistory, useRegimeStrategies, useRegimePerformance, useRegimeExplanation, useStrategyComparison } from "@/hooks/useRegime"
import { RegimeBadge, StabilityMeter, ConfidenceGauge, StrategyScore, MetricCard } from "./RegimeBadge"
import { cn } from "@/lib/utils"

const TABS = [
  { id: "current", label: "Current Regime", icon: <Activity className="w-3.5 h-3.5" /> },
  { id: "strategy", label: "Strategy Recommendation", icon: <GitBranch className="w-3.5 h-3.5" /> },
  { id: "timeline", label: "Regime Timeline", icon: <History className="w-3.5 h-3.5" /> },
  { id: "transitions", label: "Transition History", icon: <Route className="w-3.5 h-3.5" /> },
  { id: "comparison", label: "Strategy Comparison", icon: <BarChart3 className="w-3.5 h-3.5" /> },
  { id: "performance", label: "Performance Analytics", icon: <BarChart3 className="w-3.5 h-3.5" /> },
  { id: "explain", label: "AI Explanation", icon: <MessageSquare className="w-3.5 h-3.5" /> },
]

export function MarketRegimeDashboard() {
  const [activeTab, setActiveTab] = useState("current")
  const { data: currentRegime, isLoading: loading1 } = useRegime()
  const { data: regimeHistory } = useRegimeHistory()
  const { data: regimeStrategies } = useRegimeStrategies()
  const { data: regimePerf } = useRegimePerformance()
  const { data: explanation } = useRegimeExplanation()
  const { data: comparison } = useStrategyComparison()
  const { refetch: refetchCurrent } = useRegime()

  const tabContent = useMemo(() => {
    switch (activeTab) {
      case "current":
        return <CurrentRegimeView data={currentRegime} />
      case "strategy":
        return <StrategyRecommendationView data={regimeStrategies} />
      case "timeline":
        return <RegimeTimelineView data={regimeHistory} />
      case "transitions":
        return <TransitionHistoryView />
      case "comparison":
        return <StrategyComparisonView data={comparison} />
      case "performance":
        return <PerformanceAnalyticsView data={regimePerf} />
      case "explain":
        return <AIExplanationView data={explanation} />
      default:
        return null
    }
  }, [activeTab, currentRegime, regimeHistory, regimeStrategies, regimePerf, explanation, comparison])

  return (
    <div className="space-y-4">
      {/* Header */}
      <div className="flex items-center gap-2">
        <Activity className="w-5 h-5 text-primary" />
        <h1 className="text-lg font-bold">Market Regime Center</h1>
        {currentRegime && <RegimeBadge regime={currentRegime.regime} />}
        <button onClick={() => refetchCurrent()} className="ml-auto p-1 rounded text-muted-foreground hover:text-foreground hover:bg-accent">
          <RefreshCw className="w-3.5 h-3.5" />
        </button>
      </div>

      {/* Tabs */}
      <div className="flex gap-1 border-b pb-1 overflow-x-auto">
        {TABS.map((tab) => (
          <button key={tab.id} onClick={() => setActiveTab(tab.id)}
            className={cn("flex items-center gap-1.5 px-3 py-1.5 text-[10px] font-medium rounded-t-md transition-colors whitespace-nowrap",
              activeTab === tab.id ? "bg-primary/10 text-primary border-b-2 border-primary" : "text-muted-foreground hover:bg-accent"
            )}>
            {tab.icon}{tab.label}
          </button>
        ))}
      </div>

      {/* Content */}
      <div className="min-h-[400px]">
        {loading1 ? (
          <div className="p-8 text-center text-[10px] text-muted-foreground">Loading regime data...</div>
        ) : tabContent}
      </div>
    </div>
  )
}

/* ── Tab Views ── */

function CurrentRegimeView({ data }: { data: any }) {
  if (!data) return <div className="p-8 text-center text-[10px] text-muted-foreground">No regime data available</div>

  return (
    <div className="space-y-4">
      <div className="grid grid-cols-4 gap-3">
        <MetricCard label="Regime" value={data.regime?.replace(/_/g, " ") || "—"} />
        <MetricCard label="Confidence" value={`${data.confidence ?? 0}%`}
          color={(data.confidence ?? 0) >= 70 ? "text-emerald-500" : (data.confidence ?? 0) >= 40 ? "text-amber-500" : "text-red-500"} />
        <MetricCard label="Duration" value={`${data.regime_age_bars ?? 0} bars`} />
        <MetricCard label="Previous" value={data.previous_regime?.replace(/_/g, " ") || "—"} />
      </div>

      <div className="grid grid-cols-3 gap-3">
        <div className="rounded-lg border bg-card p-3">
          <StabilityMeter value={data.stability_score} />
        </div>
        <div className="rounded-lg border bg-card p-3">
          <ConfidenceGauge value={data.confidence ?? 0} label="Detection Confidence" />
        </div>
        <div className="rounded-lg border bg-card p-3">
          <div className="text-[9px] text-muted-foreground uppercase mb-1">Transition Prob.</div>
          <div className="text-lg font-bold font-mono">{(data.transition_probability * 100).toFixed(0)}%</div>
        </div>
      </div>

      {data.supporting_factors?.length > 0 && (
        <div className="rounded-lg border bg-card p-3">
          <div className="text-[9px] text-muted-foreground uppercase mb-2">Supporting Factors</div>
          <div className="flex flex-wrap gap-1">
            {data.supporting_factors.map((f: string, i: number) => (
              <span key={i} className="px-1.5 py-0.5 rounded text-[8px] font-medium bg-muted/30 text-muted-foreground border">
                {f.replace(/_/g, " ")}
              </span>
            ))}
          </div>
        </div>
      )}

      {data.strategy_recommendation && (
        <div className="rounded-lg border bg-card p-3">
          <div className="text-[9px] text-muted-foreground uppercase mb-2">Strategy Recommendation</div>
          <StrategyScore
            primary={data.strategy_recommendation.primary}
            secondary={data.strategy_recommendation.secondary}
            avoid={data.strategy_recommendation.avoid}
          />
          <div className="text-[10px] text-muted-foreground mt-1">{data.strategy_recommendation.reasoning}</div>
        </div>
      )}
    </div>
  )
}

function StrategyRecommendationView({ data }: { data: any }) {
  if (!data) return <div className="p-8 text-center text-[10px] text-muted-foreground">No strategy recommendation</div>

  return (
    <div className="space-y-4">
      <div className="grid grid-cols-4 gap-3">
        <MetricCard label="Primary" value={data.primary?.replace(/_/g, " ") || "—"} color="text-emerald-500" />
        <MetricCard label="Secondary" value={data.secondary?.replace(/_/g, " ") || "—"} />
        <MetricCard label="Win Rate" value={`${((data.expected_win_rate ?? 0) * 100).toFixed(0)}%`} />
        <MetricCard label="Confidence" value={`${data.confidence ?? 0}%`} color={(data.confidence ?? 0) >= 60 ? "text-emerald-500" : "text-amber-500"} />
      </div>

      {data.avoid?.length > 0 && (
        <div className="rounded-lg border bg-red-500/10 p-3">
          <div className="text-[9px] text-red-500 uppercase font-medium mb-1">Avoid Strategies</div>
          <div className="flex flex-wrap gap-1">
            {data.avoid.map((s: string, i: number) => (
              <span key={i} className="px-1.5 py-0.5 rounded text-[8px] font-medium bg-red-500/10 text-red-500 border border-red-500/20">
                {s.replace(/_/g, " ")}
              </span>
            ))}
          </div>
        </div>
      )}

      <div className="rounded-lg border bg-card p-3">
        <div className="text-[9px] text-muted-foreground uppercase mb-1">Reasoning</div>
        <p className="text-[10px] text-muted-foreground">{data.reasoning}</p>
      </div>
    </div>
  )
}

function RegimeTimelineView({ data }: { data: any }) {
  const snapshots = data?.snapshots ?? []
  if (snapshots.length === 0) return <div className="p-8 text-center text-[10px] text-muted-foreground">No regime history yet</div>

  return (
    <div className="space-y-1">
      {snapshots.slice(0, 30).map((s: any, i: number) => (
        <div key={s.id || i} className="flex items-center gap-2 p-1.5 rounded text-[10px] hover:bg-muted/20">
          <span className="font-mono text-muted-foreground w-16 text-[9px]">{s.timestamp?.split("T")[1]?.slice(0, 5) || ""}</span>
          <RegimeBadge regime={s.regime} />
          <span className="text-muted-foreground">{s.confidence}%</span>
          <span className="text-muted-foreground ml-auto">{s.regime_age_bars}b</span>
        </div>
      ))}
    </div>
  )
}

function TransitionHistoryView() {
  return <div className="p-8 text-center text-[10px] text-muted-foreground">Transition data will appear as regimes change over time</div>
}

function StrategyComparisonView({ data }: { data: any }) {
  const list = data?.comparison ?? []
  if (list.length === 0) return <div className="p-8 text-center text-[10px] text-muted-foreground">No comparison data available</div>

  return (
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
          <th className="text-right px-3 py-2">Consistency</th>
        </tr></thead>
        <tbody className="divide-y">
          {list.map((s: any) => (
            <tr key={s.strategy_id} className="hover:bg-muted/20">
              <td className="px-3 py-1.5 font-medium">{s.strategy_name}</td>
              <td className="px-3 py-1.5 text-right font-mono">{s.trade_count ?? s.total_trades}</td>
              <td className={`px-3 py-1.5 text-right font-mono ${s.win_rate >= 50 ? "text-emerald-500" : "text-red-500"}`}>{s.win_rate}%</td>
              <td className="px-3 py-1.5 text-right font-mono">{s.profit_factor}</td>
              <td className={`px-3 py-1.5 text-right font-mono ${(s.expectancy ?? 0) >= 0 ? "text-emerald-500" : "text-red-500"}`}>{s.expectancy}</td>
              <td className="px-3 py-1.5 text-right font-mono">{s.sharpe_ratio ?? "—"}</td>
              <td className="px-3 py-1.5 text-right font-mono text-red-500">{s.max_drawdown}</td>
              <td className="px-3 py-1.5 text-right font-mono">{s.consistency_score}%</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}

function PerformanceAnalyticsView({ data }: { data: any }) {
  const regimes = data?.regimes ?? {}
  const entries = Object.entries(regimes)
  if (entries.length === 0) return <div className="p-8 text-center text-[10px] text-muted-foreground">No performance data by regime</div>

  return (
    <div className="border rounded-lg overflow-hidden">
      <table className="w-full text-[10px]">
        <thead><tr className="bg-muted/30 border-b">
          <th className="text-left px-3 py-2">Regime</th>
          <th className="text-right px-3 py-2">Trades</th>
          <th className="text-right px-3 py-2">Win Rate</th>
          <th className="text-right px-3 py-2">Net P&L</th>
          <th className="text-right px-3 py-2">Profit Factor</th>
          <th className="text-right px-3 py-2">Avg Conf.</th>
          <th className="text-right px-3 py-2">Avg Hold</th>
          <th className="text-right px-3 py-2">Max DD</th>
        </tr></thead>
        <tbody className="divide-y">
          {entries.map(([regime, r]: [string, any]) => (
            <tr key={regime} className="hover:bg-muted/20">
              <td className="px-3 py-1.5"><RegimeBadge regime={regime} /></td>
              <td className="px-3 py-1.5 text-right font-mono">{r.total_trades}</td>
              <td className={`px-3 py-1.5 text-right font-mono ${r.win_rate >= 50 ? "text-emerald-500" : "text-red-500"}`}>{r.win_rate}%</td>
              <td className={`px-3 py-1.5 text-right font-mono ${r.net_pnl >= 0 ? "text-emerald-500" : "text-red-500"}`}>${r.net_pnl}</td>
              <td className="px-3 py-1.5 text-right font-mono">{r.profit_factor}</td>
              <td className="px-3 py-1.5 text-right font-mono">{r.avg_confidence}%</td>
              <td className="px-3 py-1.5 text-right font-mono">{r.avg_holding_hours}h</td>
              <td className="px-3 py-1.5 text-right font-mono text-red-500">{r.max_drawdown}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}

function AIExplanationView({ data }: { data: any }) {
  if (!data) return <div className="p-8 text-center text-[10px] text-muted-foreground">No explanation available</div>

  return (
    <div className="space-y-4">
      <div className="rounded-lg border bg-card p-4">
        <div className="text-[9px] text-muted-foreground uppercase mb-1">Primary Reason</div>
        <div className="text-sm font-medium">{data.primary_reason}</div>
      </div>

      {data.supporting_evidence?.length > 0 && (
        <div className="rounded-lg border bg-card p-3">
          <div className="text-[9px] text-muted-foreground uppercase mb-2">Supporting Evidence</div>
          <div className="space-y-1">
            {data.supporting_evidence.map((e: string, i: number) => (
              <div key={i} className="flex items-center gap-2 text-[10px]">
                <span className="w-1.5 h-1.5 rounded-full bg-emerald-500" />
                <span className="text-muted-foreground">{e}</span>
              </div>
            ))}
          </div>
        </div>
      )}

      <div className="grid grid-cols-2 gap-3">
        <div className="rounded-lg border border-emerald-500/20 bg-emerald-500/5 p-3">
          <div className="text-[9px] text-emerald-500 uppercase font-medium">Recommended</div>
          <div className="text-sm font-bold text-emerald-600 mt-1">{data.recommended_strategy?.replace(/_/g, " ").title() || "—"}</div>
        </div>
        {data.avoid_strategies?.length > 0 && (
          <div className="rounded-lg border border-red-500/20 bg-red-500/5 p-3">
            <div className="text-[9px] text-red-500 uppercase font-medium">Avoid</div>
            <div className="text-xs font-medium text-red-600 mt-1">{data.avoid_strategies.map((s: string) => s.replace(/_/g, " ")).join(", ")}</div>
          </div>
        )}
      </div>

      {data.strategy_reasoning && (
        <div className="rounded-lg border bg-card p-3">
          <div className="text-[9px] text-muted-foreground uppercase mb-1">Strategy Reasoning</div>
          <p className="text-[10px] text-muted-foreground">{data.strategy_reasoning}</p>
        </div>
      )}

      <div className="rounded-lg border bg-muted/30 p-3">
        <div className="text-[9px] text-muted-foreground uppercase mb-1">Market Summary</div>
        <p className="text-[10px] text-muted-foreground">{data.market_conditions_summary}</p>
      </div>
    </div>
  )
}
