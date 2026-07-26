"use client"

import { useState, useEffect, useCallback } from "react"
import {
  Brain, Activity, Target, BarChart3, AlertTriangle,
  CheckCircle, XCircle, Shield, RefreshCw, FileText, BookOpen,
  Database,
} from "lucide-react"
import { learningService } from "@/services/learningService"

type TabId = "overview" | "predictions" | "feedback" | "regimes" | "errors" | "calibration" | "ai-vs-ml" | "blocked" | "recommendations" | "data-quality"

interface MetricCardProps {
  label: string
  value: string
  sub?: string
  color?: string
}

function MetricCard({ label, value, sub, color }: MetricCardProps) {
  return (
    <div className="rounded-lg border bg-card p-3">
      <div className="text-[9px] text-muted-foreground uppercase tracking-wider">{label}</div>
      <div className={`text-lg font-bold font-mono mt-0.5 ${color || ""}`}>{value}</div>
      {sub && <div className="text-[9px] text-muted-foreground mt-0.5">{sub}</div>}
    </div>
  )
}

export function LearningDashboard() {
  const [activeTab, setActiveTab] = useState<TabId>("overview")
  const [data, setData] = useState<any>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const fetchAll = useCallback(async () => {
    try {
      const d = await learningService.getDashboard()
      setData(d)
    } catch (e) {
      setError("Failed to load learning data. Ensure the backend is running.")
    }
    setLoading(false)
  }, [])

  useEffect(() => {
    const t = setTimeout(() => fetchAll(), 0)
    const interval = setInterval(fetchAll, 30000)
    return () => { clearTimeout(t); clearInterval(interval) }
  }, [fetchAll])

  const tabs: { id: TabId; label: string; icon: React.ReactNode }[] = [
    { id: "overview", label: "Overview", icon: <Brain className="w-3.5 h-3.5" /> },
    { id: "predictions", label: "Journal", icon: <BookOpen className="w-3.5 h-3.5" /> },
    { id: "feedback", label: "Trade Feedback", icon: <Activity className="w-3.5 h-3.5" /> },
    { id: "regimes", label: "Regimes", icon: <BarChart3 className="w-3.5 h-3.5" /> },
    { id: "errors", label: "Errors", icon: <AlertTriangle className="w-3.5 h-3.5" /> },
    { id: "calibration", label: "Calibration", icon: <Target className="w-3.5 h-3.5" /> },
    { id: "ai-vs-ml", label: "AI vs ML", icon: <Brain className="w-3.5 h-3.5" /> },
    { id: "blocked", label: "Blocked", icon: <Shield className="w-3.5 h-3.5" /> },
    { id: "recommendations", label: "Recommendations", icon: <FileText className="w-3.5 h-3.5" /> },
    { id: "data-quality", label: "Data Quality", icon: <Database className="w-3.5 h-3.5" /> },
  ]

  if (error) {
    return (
      <div className="space-y-4">
        <div className="flex items-center gap-2"><Brain className="w-5 h-5 text-primary" /><h1 className="text-lg font-bold">AI Learning</h1></div>
        <div className="rounded-lg border border-red-500/20 bg-red-500/5 p-6 text-center">
          <AlertTriangle className="w-8 h-8 text-red-500 mx-auto mb-2" />
          <p className="text-sm text-red-600 font-medium">{error}</p>
          <button onClick={fetchAll} className="mt-3 px-3 py-1.5 rounded text-[10px] font-medium bg-red-500/10 text-red-600 hover:bg-red-500/20">Retry</button>
        </div>
      </div>
    )
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center gap-2">
        <Brain className="w-5 h-5 text-primary" />
        <h1 className="text-lg font-bold">AI Learning & Trade Feedback</h1>
        <button onClick={fetchAll} className="ml-auto p-1 rounded text-muted-foreground hover:text-foreground hover:bg-accent" disabled={loading}>
          <RefreshCw className={`w-3.5 h-3.5 ${loading ? "animate-spin" : ""}`} />
        </button>
      </div>

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

      <div className="min-h-[400px]">
        {loading && !data && <div className="p-8 text-center text-[10px] text-muted-foreground">Loading learning data...</div>}
        {!loading && !data && <div className="p-8 text-center text-[10px] text-muted-foreground">No learning data available. Start the backend and make predictions.</div>}
        {data && (
          <>
            {activeTab === "overview" && <OverviewTab data={data} />}
            {activeTab === "predictions" && <PredictionsTab />}
            {activeTab === "feedback" && <TradeFeedbackTab />}
            {activeTab === "regimes" && <RegimesTab data={data} />}
            {activeTab === "errors" && <ErrorsTab data={data} />}
            {activeTab === "calibration" && <CalibrationTab data={data} />}
            {activeTab === "ai-vs-ml" && <AiVsMlTab data={data} />}
            {activeTab === "blocked" && <BlockedTab />}
            {activeTab === "recommendations" && <RecommendationsTab />}
            {activeTab === "data-quality" && <DataQualityTab data={data} />}
          </>
        )}
      </div>
    </div>
  )
}

function OverviewTab({ data }: { data: any }) {
  const p = data.performance || {}
  return (
    <div className="space-y-4">
      <div className="grid grid-cols-5 gap-3">
        <MetricCard label="Total Predictions" value={String(p.total_predictions || 0)} />
        <MetricCard label="Accuracy" value={`${p.accuracy || 0}%`} color={p.accuracy >= 60 ? "text-emerald-500" : "text-amber-500"} />
        <MetricCard label="Win Rate" value={`${p.win_rate || 0}%`} color={p.win_rate >= 50 ? "text-emerald-500" : "text-red-500"} />
        <MetricCard label="Avg Confidence" value={`${p.average_confidence || 0}%`} />
        <MetricCard label="Avg Return" value={`${p.average_return || 0}%`} color={(p.average_return || 0) >= 0 ? "text-emerald-500" : "text-red-500"} />
      </div>
      <div className="grid grid-cols-4 gap-3">
        <MetricCard label="Evaluated" value={String(p.evaluated_predictions || 0)} sub={`of ${p.total_predictions || 0}`} />
        <MetricCard label="Correct" value={String(p.correct_predictions || 0)} color="text-emerald-500" />
        <MetricCard label="Incorrect" value={String(p.incorrect_predictions || 0)} color="text-red-500" />
        <MetricCard label="Total Trades" value={String(p.total_trades || 0)} />
      </div>
      <div className="grid grid-cols-4 gap-3">
        <MetricCard label="Blocked Trades" value={String(p.blocked_trades || 0)} />
        <MetricCard label="Pending Recs" value={String(data.recommendations_pending || 0)} color={(data.recommendations_pending || 0) > 0 ? "text-amber-500" : ""} />
        <MetricCard label="AI vs ML Samples" value={String(data.ai_vs_ml?.total || 0)} />
        <MetricCard label="Data Quality" value={data.data_quality?.has_issues ? "Issues Found" : "OK"} color={data.data_quality?.has_issues ? "text-amber-500" : "text-emerald-500"} />
      </div>
      <div className="rounded-lg border p-4">
        <h3 className="text-xs font-bold mb-3 flex items-center gap-2"><Shield className="w-3.5 h-3.5" /> Risk Firewall Integration</h3>
        <p className="text-[10px] text-muted-foreground">
          Learning observations NEVER modify risk limits, disable emergency controls, or directly execute trades.
          All recommendations require explicit human approval before affecting production trading.
          Blocked trades are analyzed separately from executed trades.
        </p>
      </div>
    </div>
  )
}

function PredictionsTab() {
  const [predictions, setPredictions] = useState<any[]>([])
  const [loading, setLoading] = useState(true)
  useEffect(() => {
    learningService.getPredictions(100).then(d => setPredictions(d.predictions || [])).catch(() => {}).finally(() => setLoading(false))
  }, [])
  if (loading) return <div className="p-8 text-center text-[10px] text-muted-foreground">Loading predictions...</div>
  if (predictions.length === 0) return <div className="p-8 text-center text-[10px] text-muted-foreground">No predictions recorded yet. Predictions appear here after the AI engine generates them.</div>
  return (
    <div className="border rounded-lg overflow-hidden">
      <table className="w-full text-[10px]">
        <thead>
          <tr className="bg-muted/30 border-b">
            <th className="text-left px-3 py-2 font-medium text-muted-foreground">Time</th>
            <th className="text-left px-3 py-2 font-medium text-muted-foreground">Symbol</th>
            <th className="text-left px-3 py-2 font-medium text-muted-foreground">Direction</th>
            <th className="text-right px-3 py-2 font-medium text-muted-foreground">Score</th>
            <th className="text-right px-3 py-2 font-medium text-muted-foreground">Conf</th>
            <th className="text-left px-3 py-2 font-medium text-muted-foreground">Outcome</th>
            <th className="text-right px-3 py-2 font-medium text-muted-foreground">Return</th>
            <th className="text-left px-3 py-2 font-medium text-muted-foreground">Error</th>
          </tr>
        </thead>
        <tbody className="divide-y">
          {predictions.map((p: any) => (
            <tr key={p.id} className="hover:bg-muted/20">
              <td className="px-3 py-1.5 font-mono text-muted-foreground">{p.timestamp?.split("T")[1]?.slice(0, 8) || ""}</td>
              <td className="px-3 py-1.5 font-medium">{p.symbol}</td>
              <td className="px-3 py-1.5">
                <span className={p.direction === "BUY" ? "text-emerald-500" : "text-red-500"}>{p.direction || "—"}</span>
              </td>
              <td className="px-3 py-1.5 text-right font-mono">{p.score}</td>
              <td className="px-3 py-1.5 text-right font-mono">{p.confidence}</td>
              <td className="px-3 py-1.5">
                {p.target_hit ? <span className="text-emerald-500 font-medium">TARGET</span> : p.stop_loss_hit ? <span className="text-red-500 font-medium">SL</span> : p.actual_return != null ? <span className="text-muted-foreground">CLOSED</span> : "—"}
              </td>
              <td className={`px-3 py-1.5 text-right font-mono ${(p.actual_return || 0) > 0 ? "text-emerald-500" : (p.actual_return || 0) < 0 ? "text-red-500" : ""}`}>
                {p.actual_return != null ? `${Number(p.actual_return).toFixed(1)}%` : "—"}
              </td>
              <td className="px-3 py-1.5 text-muted-foreground max-w-[120px] truncate">{p.error_category || "—"}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}

function TradeFeedbackTab() {
  const [predictions, setPredictions] = useState<any[]>([])
  const [loading, setLoading] = useState(true)
  useEffect(() => {
    learningService.getPredictions(100).then(d => {
      const withTrades = (d.predictions || []).filter((p: any) => p.gross_pnl != null)
      setPredictions(withTrades)
    }).catch(() => {}).finally(() => setLoading(false))
  }, [])
  if (loading) return <div className="p-8 text-center text-[10px] text-muted-foreground">Loading trade feedback...</div>
  if (predictions.length === 0) return <div className="p-8 text-center text-[10px] text-muted-foreground">No trade feedback data yet. Trades appear here after execution and closing.</div>
  return (
    <div className="border rounded-lg overflow-hidden">
      <table className="w-full text-[10px]">
        <thead>
          <tr className="bg-muted/30 border-b">
            <th className="text-left px-3 py-2">Symbol</th>
            <th className="text-right px-3 py-2">Gross PnL</th>
            <th className="text-right px-3 py-2">Net PnL</th>
            <th className="text-right px-3 py-2">Actual RR</th>
            <th className="text-right px-3 py-2">Return</th>
            <th className="text-left px-3 py-2">Exit Reason</th>
          </tr>
        </thead>
        <tbody className="divide-y">
          {predictions.map((p: any) => (
            <tr key={p.id} className="hover:bg-muted/20">
              <td className="px-3 py-1.5 font-medium">{p.symbol}</td>
              <td className={`px-3 py-1.5 text-right font-mono ${p.gross_pnl > 0 ? "text-emerald-500" : "text-red-500"}`}>{Number(p.gross_pnl).toFixed(2)}</td>
              <td className={`px-3 py-1.5 text-right font-mono ${p.net_pnl > 0 ? "text-emerald-500" : "text-red-500"}`}>{p.net_pnl != null ? Number(p.net_pnl).toFixed(2) : "—"}</td>
              <td className="px-3 py-1.5 text-right font-mono">{p.actual_rr != null ? Number(p.actual_rr).toFixed(2) : "—"}</td>
              <td className={`px-3 py-1.5 text-right font-mono ${(p.actual_return || 0) > 0 ? "text-emerald-500" : "text-red-500"}`}>
                {p.actual_return != null ? `${Number(p.actual_return).toFixed(1)}%` : "—"}
              </td>
              <td className="px-3 py-1.5 text-muted-foreground">{p.exit_reason || "—"}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}

function RegimesTab({ data }: { data: any }) {
  const regimes = data?.regime_performance || []
  if (regimes.length === 0) return <div className="p-8 text-center text-[10px] text-muted-foreground">Insufficient Data — No regime breakdown available. Make predictions across different market conditions.</div>
  return (
    <div className="grid grid-cols-2 gap-3">
      {regimes.map((r: any) => (
        <div key={r.regime} className="rounded-lg border bg-card p-3">
          <div className="text-xs font-bold mb-2">{r.regime}</div>
          <div className="grid grid-cols-2 gap-2 text-[10px]">
            <div><span className="text-muted-foreground">Predictions:</span> <span className="font-mono">{r.total_predictions || 0}</span></div>
            <div><span className="text-muted-foreground">Avg Return:</span> <span className={`font-mono ${(r.avg_return || 0) > 0 ? "text-emerald-500" : "text-red-500"}`}>{(r.avg_return || 0).toFixed(2)}%</span></div>
            <div><span className="text-muted-foreground">Wins:</span> <span className="font-mono text-emerald-500">{r.wins || 0}</span></div>
            <div><span className="text-muted-foreground">Losses:</span> <span className="font-mono text-red-500">{r.losses || 0}</span></div>
            <div className="col-span-2">
              <span className="text-muted-foreground">Win Rate:</span>{" "}
              <span className="font-mono">{(r.total_predictions > 0 ? ((r.wins || 0) / r.total_predictions * 100) : 0).toFixed(1)}%</span>
            </div>
          </div>
        </div>
      ))}
    </div>
  )
}

function ErrorsTab({ data }: { data: any }) {
  const errors = data?.error_analysis || []
  if (errors.length === 0) return <div className="p-8 text-center text-[10px] text-muted-foreground">Insufficient Data — No errors classified yet. Errors appear after predictions are evaluated.</div>
  return (
    <div className="border rounded-lg overflow-hidden">
      <table className="w-full text-[10px]">
        <thead>
          <tr className="bg-muted/30 border-b">
            <th className="text-left px-3 py-2">Error Category</th>
            <th className="text-right px-3 py-2">Count</th>
            <th className="text-right px-3 py-2">Percentage</th>
            <th className="text-right px-3 py-2">Avg Loss</th>
          </tr>
        </thead>
        <tbody className="divide-y">
          {errors.map((e: any) => (
            <tr key={e.error_category} className="hover:bg-muted/20">
              <td className="px-3 py-1.5 font-medium">{e.error_category}</td>
              <td className="px-3 py-1.5 text-right font-mono">{e.count}</td>
              <td className="px-3 py-1.5 text-right font-mono">{Number(e.pct || 0).toFixed(1)}%</td>
              <td className="px-3 py-1.5 text-right font-mono text-red-500">{e.avg_loss ? `${Number(e.avg_loss).toFixed(2)}%` : "—"}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}

function CalibrationTab({ data }: { data: any }) {
  const buckets = data?.calibration || []
  if (buckets.length === 0) return (
    <div className="p-8 text-center text-[10px] text-muted-foreground">
      Insufficient Data — No calibration data yet. Run a learning cycle or make predictions with outcomes to populate buckets.
    </div>
  )

  const maxCount = Math.max(...buckets.map((b: any) => b.total_predictions || 1), 1)

  return (
    <div className="space-y-4">
      <div className="grid grid-cols-2 gap-3">
        {buckets.map((b: any) => {
          const conf = b.average_confidence || 0
          const acc = b.actual_accuracy || 0
          const diff = conf - acc
          const isOver = diff > 5
          const isUnder = diff < -5
          return (
            <div key={b.bucket} className="rounded-lg border bg-card p-3">
              <div className="flex items-center justify-between mb-2">
                <span className="text-xs font-bold">{b.bucket}% Confidence</span>
                {b.total_predictions < 10 && <span className="text-[8px] text-muted-foreground">Low sample</span>}
                {isOver && <span className="text-[9px] text-amber-500 font-medium">Overconfident</span>}
                {isUnder && <span className="text-[9px] text-red-500 font-medium">Underconfident</span>}
                {!isOver && !isUnder && b.total_predictions >= 10 && <span className="text-[9px] text-emerald-500 font-medium">Well calibrated</span>}
              </div>
              <div className="space-y-1 text-[10px]">
                <div className="flex justify-between">
                  <span className="text-muted-foreground">Predictions</span>
                  <span className="font-mono">{b.total_predictions || 0}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-muted-foreground">Avg Confidence</span>
                  <span className="font-mono">{conf.toFixed(1)}%</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-muted-foreground">Actual Accuracy</span>
                  <span className={`font-mono ${acc >= conf ? "text-emerald-500" : "text-amber-500"}`}>{acc.toFixed(1)}%</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-muted-foreground">Correct</span>
                  <span className="font-mono">{b.correct_count || 0}/{b.total_predictions || 0}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-muted-foreground">Calibration Gap</span>
                  <span className={`font-mono ${Math.abs(diff) > 10 ? "text-red-500" : Math.abs(diff) > 5 ? "text-amber-500" : "text-emerald-500"}`}>
                    {diff > 0 ? "+" : ""}{diff.toFixed(1)}%
                  </span>
                </div>
              </div>
              <div className="mt-2 h-2 bg-muted/30 rounded-full overflow-hidden">
                <div className="h-full bg-primary rounded-full" style={{ width: `${Math.min(100, (b.total_predictions / maxCount) * 100)}%` }} />
              </div>
            </div>
          )
        })}
      </div>
    </div>
  )
}

function AiVsMlTab({ data }: { data: any }) {
  const cmp = data?.ai_vs_ml || {}
  if (!cmp.total || cmp.total === 0) return <div className="p-8 text-center text-[10px] text-muted-foreground">Insufficient Data — Need predictions with both AI and ML outputs to compare.</div>
  return (
    <div className="space-y-4">
      <div className="grid grid-cols-4 gap-3">
        <MetricCard label="Total Samples" value={String(cmp.total)} />
        <MetricCard label="AI Accuracy" value={`${cmp.ai_accuracy || 0}%`} color={(cmp.ai_accuracy || 0) >= 60 ? "text-emerald-500" : "text-amber-500"} />
        <MetricCard label="ML Accuracy" value={`${cmp.ml_accuracy || 0}%`} color={(cmp.ml_accuracy || 0) >= 60 ? "text-emerald-500" : "text-amber-500"} />
        <MetricCard label="Agreement Rate" value={`${cmp.agreement_rate || 0}%`} color={(cmp.agreement_rate || 0) >= 70 ? "text-emerald-500" : "text-amber-500"} />
      </div>
      <div className="grid grid-cols-4 gap-3">
        <MetricCard label="Both Correct" value={String(cmp.both_correct || 0)} color="text-emerald-500" />
        <MetricCard label="Both Wrong" value={String(cmp.both_wrong || 0)} color="text-red-500" />
        <MetricCard label="AI Only Correct" value={String(cmp.ai_correct_ml_wrong || 0)} color="text-blue-500" />
        <MetricCard label="ML Only Correct" value={String(cmp.ai_wrong_ml_correct || 0)} color="text-purple-500" />
      </div>
    </div>
  )
}

function BlockedTab() {
  const [blocked, setBlocked] = useState<any>(null)
  const [loading, setLoading] = useState(true)
  useEffect(() => {
    learningService.getBlocked().then(setBlocked).catch(() => {}).finally(() => setLoading(false))
  }, [])
  if (loading) return <div className="p-8 text-center text-[10px] text-muted-foreground">Loading blocked trade data...</div>
  if (!blocked || blocked.total_blocked === 0) return <div className="p-8 text-center text-[10px] text-muted-foreground">No blocked trades recorded. Blocked trades appear here when the Risk Firewall prevents an order.</div>
  return (
    <div className="space-y-4">
      <div className="grid grid-cols-3 gap-3">
        <MetricCard label="Total Blocked" value={String(blocked.total_blocked)} />
        <MetricCard label="Correctly Blocked" value={`${blocked.correctly_blocked_pct || 0}%`} color="text-emerald-500"
          sub={`${blocked.would_have_been_loss} would have been losses`} />
        <MetricCard label="Missed Opportunities" value={`${blocked.missed_opportunities_pct || 0}%`} color="text-amber-500"
          sub={`${blocked.would_have_been_profitable} would have been profitable`} />
      </div>
      {blocked.by_rule?.length > 0 && (
        <div className="border rounded-lg overflow-hidden">
          <div className="px-3 py-2 border-b bg-muted/20 text-[10px] font-medium text-muted-foreground">Rejected by Rule</div>
          <table className="w-full text-[10px]">
            <thead><tr className="bg-muted/30 border-b">
              <th className="text-left px-3 py-2">Blocking Rule</th>
              <th className="text-right px-3 py-2">Count</th>
            </tr></thead>
            <tbody className="divide-y">
              {blocked.by_rule.map((r: any) => (
                <tr key={r.blocked_by} className="hover:bg-muted/20">
                  <td className="px-3 py-1.5 font-medium">{r.blocked_by}</td>
                  <td className="px-3 py-1.5 text-right font-mono">{r.c}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  )
}

function RecommendationsTab() {
  const [recs, setRecs] = useState<any[]>([])
  const [filter, setFilter] = useState<string | undefined>()
  const [loading, setLoading] = useState(true)
  const [refresh, setRefresh] = useState(0)

  useEffect(() => {
    const t = setTimeout(() => {
      learningService.getRecommendations(filter).then(d => setRecs(d.recommendations || [])).catch(() => {}).finally(() => setLoading(false))
    }, 0)
    return () => clearTimeout(t)
  }, [filter, refresh])

  const handleApprove = async (id: string) => {
    await learningService.approveRecommendation(id)
    setRefresh(s => s + 1)
  }
  const handleReject = async (id: string) => {
    await learningService.rejectRecommendation(id, "Rejected by user")
    setRefresh(s => s + 1)
  }

  const statusFilter = ["NEW", "APPROVED", "REJECTED", "IMPLEMENTED"]

  if (loading && recs.length === 0) return <div className="p-8 text-center text-[10px] text-muted-foreground">Loading recommendations...</div>

  return (
    <div className="space-y-3">
      <div className="flex gap-1">
        <button onClick={() => setFilter(undefined)}
          className={`px-2 py-1 rounded text-[9px] font-medium ${!filter ? "bg-primary/20 text-primary" : "text-muted-foreground hover:bg-accent"}`}>ALL</button>
        {statusFilter.map(s => (
          <button key={s} onClick={() => setFilter(s)}
            className={`px-2 py-1 rounded text-[9px] font-medium ${filter === s ? "bg-primary/20 text-primary" : "text-muted-foreground hover:bg-accent"}`}>{s}</button>
        ))}
      </div>
      {recs.length === 0 && <div className="p-8 text-center text-[10px] text-muted-foreground">Insufficient Data — No recommendations yet. Recommendations are generated after sufficient prediction data exists.</div>}
      <div className="grid grid-cols-2 gap-3">
        {recs.map((r: any) => (
          <div key={r.id} className={`rounded-lg border bg-card p-3 ${r.status === "NEW" ? "ring-1 ring-primary/20" : ""}`}>
            <div className="flex items-center justify-between mb-1">
              <h3 className="text-xs font-bold">{r.title}</h3>
              <span className={`px-1.5 py-0.5 rounded text-[8px] font-bold ${
                r.status === "NEW" ? "bg-blue-500/10 text-blue-500" :
                r.status === "APPROVED" ? "bg-emerald-500/10 text-emerald-500" :
                r.status === "REJECTED" ? "bg-red-500/10 text-red-500" :
                r.status === "IMPLEMENTED" ? "bg-green-500/10 text-green-500" :
                "bg-muted/30 text-muted-foreground"
              }`}>{r.status}</span>
            </div>
            <p className="text-[9px] text-muted-foreground mb-2">{r.finding}</p>
            <div className="flex gap-2 text-[8px] text-muted-foreground mb-2">
              <span>Sample: {r.sample_count || 0}</span>
              <span>Confidence: {r.confidence != null ? `${r.confidence}%` : "—"}</span>
              <span>Impact: {r.expected_impact || "—"}</span>
            </div>
            <p className="text-[9px] bg-muted/20 rounded p-2 mb-2">{r.recommendation}</p>
            <div className="flex gap-1 text-[8px] text-muted-foreground">
              <span>Category: {r.category || "—"}</span>
              {r.approved_at && <span>Approved: {r.approved_at?.split("T")[0]}</span>}
              {r.rejected_at && <span>Rejected: {r.rejected_at?.split("T")[0]}</span>}
            </div>
            {r.status === "NEW" && (
              <div className="flex gap-1 mt-2">
                <button onClick={() => handleApprove(r.id)} className="flex items-center gap-1 px-2 py-1 rounded text-[8px] font-medium bg-emerald-500/10 text-emerald-600 hover:bg-emerald-500/20">
                  <CheckCircle className="w-2.5 h-2.5" /> Approve
                </button>
                <button onClick={() => handleReject(r.id)} className="flex items-center gap-1 px-2 py-1 rounded text-[8px] font-medium bg-red-500/10 text-red-600 hover:bg-red-500/20">
                  <XCircle className="w-2.5 h-2.5" /> Reject
                </button>
              </div>
            )}
          </div>
        ))}
      </div>
    </div>
  )
}

function DataQualityTab({ data }: { data: any }) {
  const dq = data?.data_quality || {}
  const issues: string[] = []
  if (dq.orphan_outcomes > 0) issues.push(`${dq.orphan_outcomes} orphaned outcome records`)
  if (dq.orphan_feedback > 0) issues.push(`${dq.orphan_feedback} orphaned trade feedback records`)
  if (dq.duplicate_outcomes > 0) issues.push(`${dq.duplicate_outcomes} duplicate outcome records`)

  return (
    <div className="space-y-4">
      <div className="grid grid-cols-3 gap-3">
        <MetricCard label="Predictions" value={String(dq.prediction_journal_count || 0)} />
        <MetricCard label="Outcomes" value={String(dq.outcome_count || 0)} />
        <MetricCard label="Data Completeness" value={`${dq.data_completeness_pct || 0}%`} color={(dq.data_completeness_pct || 0) >= 80 ? "text-emerald-500" : "text-amber-500"} />
      </div>
      <div className="grid grid-cols-3 gap-3">
        <MetricCard label="Trade Feedback" value={String(dq.trade_feedback_count || 0)} />
        <MetricCard label="Blocked Trades" value={String(dq.blocked_trade_count || 0)} />
        <MetricCard label="Status" value={dq.has_issues ? "Issues Found" : "Clean"} color={dq.has_issues ? "text-amber-500" : "text-emerald-500"} />
      </div>
      {issues.length > 0 && (
        <div className="rounded-lg border border-amber-500/20 bg-amber-500/5 p-3">
          <h3 className="text-xs font-bold text-amber-600 mb-2">Data Issues Found</h3>
          <ul className="list-disc list-inside text-[10px] text-amber-600 space-y-1">
            {issues.map((issue, i) => <li key={i}>{issue}</li>)}
          </ul>
        </div>
      )}
      {!dq.has_issues && dq.prediction_journal_count > 0 && (
        <div className="rounded-lg border border-emerald-500/20 bg-emerald-500/5 p-3 text-[10px] text-emerald-600">
          All data integrity checks passed. No orphaned records, no duplicates.
        </div>
      )}
      {(!dq.prediction_journal_count || dq.prediction_journal_count === 0) && (
        <div className="p-8 text-center text-[10px] text-muted-foreground">No data available to check quality metrics.</div>
      )}
    </div>
  )
}
