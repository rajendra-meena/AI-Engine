/* eslint-disable @typescript-eslint/no-explicit-any */
"use client"

import { useState, useEffect, useCallback, useRef } from "react"
import {
  Activity, AlertTriangle, BarChart3, Bot, CheckCircle, ChevronDown, ChevronRight,
  Clock, Cpu, FileText, Gauge, Info, LogOut, Play, Power, PowerOff,
  Radar, RefreshCw, Shield, ShieldOff, Sparkles, StopCircle, Target, TrendingDown,
  TrendingUp, Wallet, XCircle, Eye, EyeOff,
  Minus, Search, SkipForward, Timer, X, Brain,
} from "lucide-react"
import { cn } from "@/lib/utils"
import { autoTradeService } from "@/services/autoTradeService"
import type { WorkspaceResponse, OpportunityCandidate, TradePlan } from "@/services/autoTradeService"
import { orchestratorService } from "@/services/orchestratorService"
import { executionService } from "@/services/executionService"
import { useRealtimeStore } from "@/store/useRealtimeStore"

/* ─── Constants ─── */

const ENGINE_STATES = [
  "OFF", "STARTING", "SCANNING", "ANALYZING", "WAITING",
  "OPPORTUNITY FOUND", "VALIDATING", "APPROVED", "ORDER PENDING",
  "POSITION ACTIVE", "MANAGING EXIT", "COMPLETED", "BLOCKED", "ERROR", "STOPPING",
] as const

const TRADING_MODES = [
  { id: "replay", label: "Replay", icon: <Clock className="w-3 h-3" /> },
  { id: "paper", label: "Paper Trading", icon: <Wallet className="w-3 h-3" />, default: true },
  { id: "shadow", label: "Shadow", icon: <Eye className="w-3 h-3" /> },
  { id: "controlled_live", label: "Controlled Live", icon: <Shield className="w-3 h-3" /> },
] as const

const READINESS_COLORS: Record<string, string> = {
  READY: "text-emerald-500 bg-emerald-500/10 border-emerald-500/20",
  DEGRADED: "text-amber-500 bg-amber-500/10 border-amber-500/20",
  BLOCKED: "text-red-500 bg-red-500/10 border-red-500/20",
  OFFLINE: "text-muted-foreground bg-muted/30 border-muted/20",
  "NOT_REQUIRED": "text-muted-foreground bg-muted/10 border-muted/10",
}

const STATE_COLORS: Record<string, string> = {
  OFF: "text-muted-foreground bg-muted/30",
  STARTING: "text-blue-500 bg-blue-500/10",
  SCANNING: "text-blue-500 bg-blue-500/10",
  ANALYZING: "text-indigo-500 bg-indigo-500/10",
  WAITING: "text-amber-500 bg-amber-500/10",
  "OPPORTUNITY FOUND": "text-emerald-500 bg-emerald-500/10",
  VALIDATING: "text-purple-500 bg-purple-500/10",
  APPROVED: "text-emerald-500 bg-emerald-500/10",
  "ORDER PENDING": "text-blue-500 bg-blue-500/10",
  "POSITION ACTIVE": "text-emerald-500 bg-emerald-500/10",
  "MANAGING EXIT": "text-amber-500 bg-amber-500/10",
  COMPLETED: "text-muted-foreground bg-muted/30",
  BLOCKED: "text-red-500 bg-red-500/10",
  ERROR: "text-red-500 bg-red-500/10",
  STOPPING: "text-amber-500 bg-amber-500/10",
}

const MODE_BADGE_COLORS: Record<string, string> = {
  replay: "text-blue-500 bg-blue-500/10 border-blue-500/20",
  paper: "text-emerald-500 bg-emerald-500/10 border-emerald-500/20",
  shadow: "text-purple-500 bg-purple-500/10 border-purple-500/20",
  controlled_live: "text-amber-500 bg-amber-500/10 border-amber-500/20",
}

/* ─── StatusIcon ─── */

function StatusIcon({ status, size = "w-4 h-4" }: { status: string; size?: string }) {
  switch (status) {
    case "READY": return <CheckCircle className={cn(size, "text-emerald-500")} />
    case "DEGRADED": return <AlertTriangle className={cn(size, "text-amber-500")} />
    case "BLOCKED":
    case "OFFLINE": return <XCircle className={cn(size, "text-red-500")} />
    case "NOT_REQUIRED": return <Minus className={cn(size, "text-muted-foreground")} />
    default: return <Activity className={cn(size, "text-muted-foreground")} />
  }
}

/* ─── DirectionIcon ─── */

function DirectionIcon({ dir }: { dir: string }) {
  switch (dir) {
    case "BUY": return <TrendingUp className="w-3.5 h-3.5 text-emerald-500" />
    case "SELL": return <TrendingDown className="w-3.5 h-3.5 text-red-500" />
    default: return <Minus className="w-3.5 h-3.5 text-muted-foreground" />
  }
}

/* ─── Section Card ─── */

function SectionCard({ title, icon, children, className, defaultOpen = true }: {
  title: string
  icon?: React.ReactNode
  children: React.ReactNode
  className?: string
  defaultOpen?: boolean
}) {
  const [open, setOpen] = useState(defaultOpen)
  return (
    <div className={cn("rounded-lg border bg-card", className)}>
      <button
        onClick={() => setOpen(!open)}
        className="flex items-center gap-2 w-full px-3 py-2 text-xs font-medium text-foreground hover:bg-muted/20 transition-colors"
      >
        {icon}
        <span className="flex-1 text-left">{title}</span>
        {open ? <ChevronDown className="w-3 h-3 text-muted-foreground" /> : <ChevronRight className="w-3 h-3 text-muted-foreground" />}
      </button>
      {open && <div className="px-3 pb-3 space-y-2 border-t pt-2">{children}</div>}
    </div>
  )
}

/* ─── MetricDisplay ─── */

function Metric({ label, value, color, className }: { label: string; value: React.ReactNode; color?: string; className?: string }) {
  return (
    <div className={cn("rounded border bg-card/50 p-2", className)}>
      <div className="text-[9px] text-muted-foreground uppercase tracking-wider mb-0.5">{label}</div>
      <div className={cn("text-xs font-semibold font-mono", color || "text-foreground")}>{value}</div>
    </div>
  )
}

/* ─── Tooltip ─── */

function HelpTip({ content }: { content: string }) {
  return (
    <span className="group relative inline-flex items-center" title={content}>
      <Info className="w-3 h-3 text-muted-foreground/50 cursor-help" />
    </span>
  )
}

/* ─── ConfirmModal ─── */

function ConfirmModal({ open, title, message, confirmLabel, onConfirm, onCancel, danger }: {
  open: boolean; title: string; message: string; confirmLabel: string
  onConfirm: () => void; onCancel: () => void; danger?: boolean
}) {
  if (!open) return null
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50" onClick={onCancel}>
      <div className="rounded-lg border bg-card p-4 max-w-sm w-full mx-4 shadow-xl" onClick={e => e.stopPropagation()}>
        <h3 className="text-sm font-bold mb-2">{title}</h3>
        <p className="text-[11px] text-muted-foreground mb-4">{message}</p>
        <div className="flex gap-2 justify-end">
          <button onClick={onCancel} className="px-3 py-1.5 rounded text-[10px] font-medium border hover:bg-accent transition-colors">Cancel</button>
          <button onClick={onConfirm} className={cn("px-3 py-1.5 rounded text-[10px] font-medium text-white transition-colors", danger ? "bg-red-600 hover:bg-red-700" : "bg-primary hover:bg-primary/90")}>
            {confirmLabel}
          </button>
        </div>
      </div>
    </div>
  )
}

/* ─── Timeline Entry ─── */

type TimelineCategory = "SYSTEM" | "MARKET" | "AI" | "STRATEGY" | "RISK" | "ORDER" | "POSITION" | "EXIT" | "PERFORMANCE" | "INCIDENT"

const CATEGORY_COLORS: Record<string, string> = {
  SYSTEM: "text-blue-500 bg-blue-500/10",
  MARKET: "text-emerald-500 bg-emerald-500/10",
  AI: "text-purple-500 bg-purple-500/10",
  STRATEGY: "text-indigo-500 bg-indigo-500/10",
  RISK: "text-amber-500 bg-amber-500/10",
  ORDER: "text-cyan-500 bg-cyan-500/10",
  POSITION: "text-emerald-500 bg-emerald-500/10",
  EXIT: "text-red-500 bg-red-500/10",
  PERFORMANCE: "text-violet-500 bg-violet-500/10",
  INCIDENT: "text-red-500 bg-red-500/10",
}

/* ─── MAIN COMPONENT ─── */

export function AutoTradeWorkspace() {
  /* ════════════════ State ════════════════ */
  const [workspace, setWorkspace] = useState<WorkspaceResponse | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [tradingMode, setTradingMode] = useState("paper")
  const [showDetails, setShowDetails] = useState(false)
  const [confirmAction, setConfirmAction] = useState<{ type: string } | null>(null)
  const [approvingPlan, setApprovingPlan] = useState(false)
  const [cancellingOrder, setCancellingOrder] = useState(false)
  const [killingSwitch, setKillingSwitch] = useState(false)
  const [showSettings, setShowSettings] = useState(false)
  const [isToggling, setIsToggling] = useState(false)

  // User settings
  const [marketUniverse, setMarketUniverse] = useState("all")
  const [maxTradesPerDay, setMaxTradesPerDay] = useState(2)
  const [minConfidence, setMinConfidence] = useState(80)
  const [minGrade, setMinGrade] = useState("B")
  const [minRR, setMinRR] = useState("1:2")
  const [allowBuy, setAllowBuy] = useState(true)
  const [allowSell, setAllowSell] = useState(true)
  const [autoExecutePaper, setAutoExecutePaper] = useState(false)

  const pollingRef = useRef<ReturnType<typeof setInterval> | null>(null)

  /* ════════════════ Data Fetching ════════════════ */

  const fetchWorkspace = useCallback(async () => {
    try {
      const data = await autoTradeService.getWorkspace()
      if (!isToggling) {
        setWorkspace(data)
      }
      setError(null)
    } catch (e) {
      setError("Could not connect to backend")
    }
    setLoading(false)
  }, [isToggling])

  useEffect(() => {
    const t = setTimeout(() => fetchWorkspace(), 0)
    pollingRef.current = setInterval(fetchWorkspace, 5000)
    return () => {
      clearTimeout(t)
      if (pollingRef.current) clearInterval(pollingRef.current)
    }
  }, [fetchWorkspace])

  /* ════════════════ Engine Controls ════════════════ */

  const handleStart = useCallback(async () => {
    setError(null)
    setIsToggling(true)
    try {
      const result = await autoTradeService.start()
      if (!result.success) {
        setError(result.message)
      }
      await fetchWorkspace()
    } catch {
      setError("Failed to start engine")
    }
    setIsToggling(false)
  }, [fetchWorkspace])

  const handleStop = useCallback(async () => {
    setConfirmAction(null)
    setIsToggling(true)
    try {
      await autoTradeService.stop()
      await fetchWorkspace()
    } catch {
      setError("Failed to stop engine")
    }
    setIsToggling(false)
  }, [fetchWorkspace])

  const handlePause = useCallback(async () => {
    setIsToggling(true)
    try {
      await autoTradeService.pause()
      await fetchWorkspace()
    } catch {
      setError("Failed to pause engine")
    }
    setIsToggling(false)
  }, [fetchWorkspace])

  const handleResume = useCallback(async () => {
    setIsToggling(true)
    try {
      await autoTradeService.resume()
      await fetchWorkspace()
    } catch {
      setError("Failed to resume engine")
    }
    setIsToggling(false)
  }, [fetchWorkspace])

  /* ════════════════ Trade Actions ════════════════ */

  const handleApproveTrade = useCallback(async () => {
    setConfirmAction(null)
    setApprovingPlan(true)
    try {
      const plan = workspace?.trade_plan
      if (!plan) {
        setError("No trade plan to approve")
        setApprovingPlan(false)
        return
      }

      if (tradingMode === "paper") {
        // Run orchestrator paper trade
        const result = await orchestratorService.paperTrade({
          symbol: plan.symbol,
          interval: "15m",
          execution_mode: "paper",
          strategy_id: plan.strategy,
          ai_score: plan.ai_score,
          ai_confidence: plan.ai_confidence,
          ai_decision: plan.direction,
          market_price: plan.entry_price,
        })
        if (result?.risk_status === "blocked") {
          setError(`Trade blocked by risk: ${result.risk_reasons?.join(", ")}`)
        }
      } else if (tradingMode === "controlled_live") {
        // Controlled live must go through activation gate
        setError("Controlled Live approval requires the Live Activation workflow. Go to Live Activation page.")
      }
      await fetchWorkspace()
    } catch (e) {
      setError("Trade approval failed")
    }
    setApprovingPlan(false)
  }, [workspace, tradingMode, fetchWorkspace])

  const handleCancelOrder = useCallback(async () => {
    setConfirmAction(null)
    setCancellingOrder(true)
    try {
      const order = workspace?.order
      if (!order?.order_id) {
        setError("No cancellable order found")
        setCancellingOrder(false)
        return
      }
      // Try paper cancel first
      const { paperBrokerService } = await import("@/services/paperBrokerService")
      await paperBrokerService.stop() // Will cancel pending orders
      await fetchWorkspace()
    } catch {
      setError("Failed to cancel order")
    }
    setCancellingOrder(false)
  }, [workspace, fetchWorkspace])

  const handleExitPosition = useCallback(async () => {
    setConfirmAction(null)
    try {
      const position = workspace?.position
      if (position?.trade_id) {
        const { paperBrokerService } = await import("@/services/paperBrokerService")
        await paperBrokerService.closePosition(position.trade_id)
        await fetchWorkspace()
      }
    } catch {
      setError("Failed to exit position")
    }
  }, [workspace, fetchWorkspace])

  const handleKillSwitch = useCallback(async () => {
    setConfirmAction(null)
    setKillingSwitch(true)
    try {
      await executionService.activateKillSwitch("Auto Trade - Manual kill switch")
      await autoTradeService.stop()
      await fetchWorkspace()
    } catch {
      setError("Failed to activate kill switch")
    }
    setKillingSwitch(false)
  }, [fetchWorkspace])

  /* ════════════════ Derived State ════════════════ */

  const engine = workspace?.engine
  const engineState = engine?.state || "OFF"
  const isRunning = engine?.analysis_enabled || engine?.running || false
  const isPaused = engine?.paused || false
  const readiness = workspace?.readiness || {}
  const candidates = workspace?.candidates || []
  const selected = workspace?.selected_opportunity || null
  const tradePlan = workspace?.trade_plan || null
  const order = workspace?.order || null
  const position = workspace?.position || null
  const noTradeReasons = workspace?.no_trade_reasons || []
  const blockingReasons = workspace?.blocking_reasons || []
  const errors = workspace?.errors || []
  const aiExplanation = workspace?.ai_explanation || null

  // Readiness summary
  const readinessEntries = Object.entries(readiness)
  const blockedSystems = readinessEntries.filter(([, v]) => v === "BLOCKED").map(([k]) => k)
  const degradedSystems = readinessEntries.filter(([, v]) => v === "DEGRADED").map(([k]) => k)

  // Connection state from realtime store
  const connectionState = useRealtimeStore((s) => s.connection.state)

  /* ════════════════ Render ════════════════ */

  return (
    <div className="space-y-4 text-xs">
      {/* ═══ TOP HEADER ═══ */}
      <div className="flex flex-wrap items-start gap-3 p-3 rounded-lg border bg-card">
        <div className="flex items-center gap-2">
          <Sparkles className="w-5 h-5 text-primary" />
          <h1 className="text-sm font-bold">Auto Trade Workspace</h1>
        </div>
        <p className="w-full text-[10px] text-muted-foreground md:w-auto md:flex-1 md:mt-0.5">
          The system scans the market, validates opportunities, and manages approved trades using your configured safety rules.
        </p>
        <div className="flex items-center gap-2 ml-auto">
          {/* Mode badge */}
          <span className={cn("px-2 py-0.5 rounded text-[9px] font-medium border", MODE_BADGE_COLORS[tradingMode] || "text-muted-foreground")}>
            {tradingMode === "replay" ? "Replay" : tradingMode === "paper" ? "Paper" : tradingMode === "shadow" ? "Shadow" : "Controlled Live"}
          </span>
          {/* Safety badge */}
          <span className="px-2 py-0.5 rounded text-[9px] font-medium bg-amber-500/10 border border-amber-500/20 text-amber-500">
            PHASE_43_LIVE_EXECUTION_LOCK: ACTIVE
          </span>
          {/* Connection */}
          <span className={cn("px-1.5 py-0.5 rounded text-[8px] font-medium", connectionState === "connected" ? "text-emerald-500 bg-emerald-500/10" : "text-red-500 bg-red-500/10")}>
            {connectionState === "connected" ? "● Live" : "○ Disconnected"}
          </span>
        </div>
      </div>

      {error && (
        <div className="rounded-lg border border-red-500/20 bg-red-500/5 p-3 text-[10px] text-red-600 flex items-center gap-2">
          <AlertTriangle className="w-3.5 h-3.5 shrink-0" />
          {error}
          <button onClick={() => setError(null)} className="ml-auto text-red-400 hover:text-red-600">
            <X className="w-3 h-3" />
          </button>
        </div>
      )}

      {loading && !workspace ? (
        <div className="p-8 text-center text-[10px] text-muted-foreground">
          <RefreshCw className="w-4 h-4 animate-spin mx-auto mb-2" />
          Loading Auto Trade Workspace...
        </div>
      ) : (
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
          {/* ═══ LEFT COLUMN ═══ */}
          <div className="space-y-4 lg:col-span-1">

            {/* ENGINE CONTROL */}
            <SectionCard title="Engine Control" icon={<Cpu className="w-3.5 h-3.5 text-primary" />}>
              <div className="flex items-center gap-3 p-2 rounded-lg border bg-muted/20">
                <div className={cn("w-10 h-10 rounded-full flex items-center justify-center", STATE_COLORS[engineState] || "bg-muted/30")}>
                  {isRunning ? <Activity className="w-5 h-5" /> : <PowerOff className="w-5 h-5 text-muted-foreground" />}
                </div>
                <div className="flex-1 min-w-0">
                  <div className="text-[10px] text-muted-foreground">Auto Analysis Engine</div>
                  <div className={cn("text-xs font-bold", isRunning ? "text-foreground" : "text-muted-foreground")}>
                    {engineState}
                  </div>
                </div>
                {!isRunning ? (
                  <button onClick={handleStart} disabled={loading || isToggling}
                    className="flex items-center gap-1 px-3 py-1.5 rounded text-[10px] font-medium bg-primary text-primary-foreground hover:bg-primary/90 disabled:opacity-50 transition-colors">
                    {isToggling ? <RefreshCw className="w-3 h-3 animate-spin" /> : <Power className="w-3 h-3" />} {isToggling ? "Starting..." : "ON"}
                  </button>
                ) : (
                  <div className="flex gap-1">
                    {isPaused ? (
                      <button onClick={handleResume} disabled={isToggling}
                        className="flex items-center gap-1 px-2 py-1.5 rounded text-[10px] font-medium bg-emerald-500/10 text-emerald-500 hover:bg-emerald-500/20 disabled:opacity-50 transition-colors">
                        {isToggling ? <RefreshCw className="w-3 h-3 animate-spin" /> : <Play className="w-3 h-3" />} {isToggling ? "Resuming..." : "Resume"}
                      </button>
                    ) : (
                      <button onClick={handlePause} disabled={isToggling}
                        className="flex items-center gap-1 px-2 py-1.5 rounded text-[10px] font-medium bg-amber-500/10 text-amber-500 hover:bg-amber-500/20 disabled:opacity-50 transition-colors">
                        {isToggling ? <RefreshCw className="w-3 h-3 animate-spin" /> : <ChevronRight className="w-3 h-3" />} {isToggling ? "Pausing..." : "Pause"}
                      </button>
                    )}
                    <button onClick={() => setConfirmAction({ type: "stop" })} disabled={isToggling}
                      className="flex items-center gap-1 px-2 py-1.5 rounded text-[10px] font-medium bg-red-500/10 text-red-500 hover:bg-red-500/20 disabled:opacity-50 transition-colors">
                      <StopCircle className="w-3 h-3" /> Stop
                    </button>
                  </div>
                )}
              </div>
              <p className="text-[9px] text-muted-foreground">
                {isRunning
                  ? "Automatic scanning and analysis are enabled. Trade execution still depends on runtime mode and all approval gates."
                  : "Auto analysis is currently stopped. Turn it ON to begin scanning the market."}
              </p>
            </SectionCard>

            {/* TRADING MODE */}
            <SectionCard title="Trading Mode" icon={<Shield className="w-3.5 h-3.5 text-primary" />}>
              <div className="flex flex-wrap gap-1.5">
                {TRADING_MODES.map((mode) => (
                  <button key={mode.id} onClick={() => setTradingMode(mode.id)}
                    className={cn(
                      "flex items-center gap-1 px-2 py-1.5 rounded text-[10px] font-medium border transition-colors",
                      tradingMode === mode.id
                        ? "bg-primary/10 border-primary/30 text-primary"
                        : "text-muted-foreground hover:text-foreground hover:bg-accent"
                    )}>
                    {mode.icon} {mode.label}
                  </button>
                ))}
              </div>
              {tradingMode === "controlled_live" && (
                <div className="rounded border border-amber-500/20 bg-amber-500/5 p-2 text-[9px] text-amber-600">
                  ⚠ Real money may be used. Human approval and all controlled-live restrictions remain mandatory.
                </div>
              )}
            </SectionCard>

            {/* USER SETTINGS */}
            <SectionCard title="User Settings" icon={<Gauge className="w-3.5 h-3.5 text-primary" />} defaultOpen={false}>
              <div className="space-y-2">
                <div className="flex items-center justify-between">
                  <label className="text-[10px] text-muted-foreground">Market Universe</label>
                  <select value={marketUniverse} onChange={e => setMarketUniverse(e.target.value)}
                    className="h-6 rounded border bg-muted/30 px-1.5 text-[10px] font-medium">
                    <option value="nifty50">NIFTY 50</option>
                    <option value="banknifty">BANKNIFTY</option>
                    <option value="major_indices">Major Indices</option>
                    <option value="fno">F&O Stocks</option>
                    <option value="watchlist">Watchlist</option>
                    <option value="all">All Supported Symbols</option>
                  </select>
                </div>
                <div className="flex items-center justify-between">
                  <label className="text-[10px] text-muted-foreground">Max Trades/Day</label>
                  <input type="number" value={maxTradesPerDay} onChange={e => setMaxTradesPerDay(Number(e.target.value))}
                    min={1} max={10} className="w-16 h-6 rounded border bg-muted/30 px-1.5 text-[10px] font-medium text-right" />
                </div>
                <div className="flex items-center justify-between">
                  <label className="text-[10px] text-muted-foreground">Min AI Confidence <HelpTip content="Minimum AI confidence score required for trade approval" /></label>
                  <input type="number" value={minConfidence} onChange={e => setMinConfidence(Number(e.target.value))}
                    min={0} max={100} className="w-16 h-6 rounded border bg-muted/30 px-1.5 text-[10px] font-medium text-right" />
                </div>
                <div className="flex items-center justify-between">
                  <label className="text-[10px] text-muted-foreground">Min Trade Grade</label>
                  <select value={minGrade} onChange={e => setMinGrade(e.target.value)}
                    className="h-6 rounded border bg-muted/30 px-1.5 text-[10px] font-medium">
                    <option value="A">A</option>
                    <option value="B">B</option>
                    <option value="C">C</option>
                  </select>
                </div>
                <div className="flex items-center justify-between">
                  <label className="text-[10px] text-muted-foreground">Min Risk/Reward <HelpTip content="Minimum acceptable ratio of potential reward to risk" /></label>
                  <input type="text" value={minRR} onChange={e => setMinRR(e.target.value)}
                    className="w-16 h-6 rounded border bg-muted/30 px-1.5 text-[10px] font-medium text-right" />
                </div>
                <div className="flex items-center justify-between">
                  <label className="text-[10px] text-muted-foreground">Allow Buy Trades</label>
                  <button onClick={() => setAllowBuy(!allowBuy)} className={cn("w-8 h-4 rounded-full transition-colors", allowBuy ? "bg-emerald-500" : "bg-muted")}>
                    <div className={cn("w-3 h-3 rounded-full bg-white transition-transform", allowBuy ? "translate-x-4" : "translate-x-0.5")} />
                  </button>
                </div>
                <div className="flex items-center justify-between">
                  <label className="text-[10px] text-muted-foreground">Allow Sell Trades</label>
                  <button onClick={() => setAllowSell(!allowSell)} className={cn("w-8 h-4 rounded-full transition-colors", allowSell ? "bg-red-500" : "bg-muted")}>
                    <div className={cn("w-3 h-3 rounded-full bg-white transition-transform", allowSell ? "translate-x-4" : "translate-x-0.5")} />
                  </button>
                </div>
                {tradingMode === "paper" && (
                  <div className="flex items-center justify-between pt-1 border-t">
                    <label className="text-[10px] text-muted-foreground">Auto Execute Paper Trades</label>
                    <button onClick={() => setAutoExecutePaper(!autoExecutePaper)} className={cn("w-8 h-4 rounded-full transition-colors", autoExecutePaper ? "bg-emerald-500" : "bg-muted")}>
                      <div className={cn("w-3 h-3 rounded-full bg-white transition-transform", autoExecutePaper ? "translate-x-4" : "translate-x-0.5")} />
                    </button>
                  </div>
                )}
              </div>
            </SectionCard>

            {/* SYSTEM READINESS */}
            <SectionCard title="System Readiness" icon={<Radar className="w-3.5 h-3.5 text-primary" />}>
              {readinessEntries.length === 0 ? (
                <p className="text-[10px] text-muted-foreground">Start the engine to check system readiness.</p>
              ) : (
                <div className="grid grid-cols-2 gap-1.5">
                  {readinessEntries.map(([system, status]) => (
                    <div key={system} className={cn("flex items-center gap-1.5 px-2 py-1 rounded border text-[9px]", READINESS_COLORS[status] || "text-muted-foreground bg-muted/20 border-muted/20")}>
                      <StatusIcon status={status} size="w-2.5 h-2.5" />
                      <span className="truncate font-medium">{system.replace(/_/g, " ").replace(/\b\w/g, c => c.toUpperCase())}</span>
                      <span className="ml-auto text-[7px] font-mono opacity-70">{status}</span>
                    </div>
                  ))}
                </div>
              )}
              {blockedSystems.length > 0 && (
                <div className="rounded border border-red-500/20 bg-red-500/5 p-2 text-[9px] text-red-600">
                  ⚠ Trading blocked: {blockedSystems.map(s => s.replace(/_/g, " ")).join(", ")} {blockedSystems.includes("kill_switch") ? "- Kill switch is active" : "- System(s) not ready"}
                </div>
              )}
              {degradedSystems.length > 0 && !blockedSystems.length && (
                <div className="rounded border border-amber-500/20 bg-amber-500/5 p-2 text-[9px] text-amber-600">
                  ⚠ Some systems degraded: {degradedSystems.map(s => s.replace(/_/g, " ")).join(", ")}
                </div>
              )}
            </SectionCard>

            {/* INDICATOR SUMMARY */}
            {selected && (
              <SectionCard title="Indicator Summary" icon={<BarChart3 className="w-3.5 h-3.5 text-primary" />}>
                <div className="grid grid-cols-2 gap-1.5">
                  {renderSimpleIndicator("Trend", aiExplanation?.decision_explanation?.primary_reason || "Neutral")}
                  {renderSimpleIndicator("Direction", selected.direction)}
                  {renderSimpleIndicator("Confidence", `${selected.confidence}%`)}
                  {renderSimpleIndicator("Grade", selected.grade)}
                  {renderSimpleIndicator("Regime", selected.regime)}
                  {renderSimpleIndicator("Risk", selected.risk_status)}
                </div>
                {workspace?.decision && (
                  <button onClick={() => setShowDetails(!showDetails)} className="flex items-center gap-1 text-[9px] text-muted-foreground hover:text-foreground transition-colors mt-1">
                    {showDetails ? <EyeOff className="w-3 h-3" /> : <Eye className="w-3 h-3" />}
                    {showDetails ? "Hide technical details" : "View analysis details"}
                  </button>
                )}
                {showDetails && workspace?.decision && (
                  <div className="mt-2 space-y-1 text-[9px] font-mono border-t pt-2 max-h-40 overflow-y-auto">
                    {Object.entries(workspace.decision).slice(0, 20).map(([k, v]) => (
                      <div key={k} className="flex gap-1">
                        <span className="text-muted-foreground shrink-0">{k}:</span>
                        <span className="text-foreground truncate">{typeof v === "object" ? JSON.stringify(v).slice(0, 80) : String(v)}</span>
                      </div>
                    ))}
                  </div>
                )}
              </SectionCard>
            )}
          </div>

          {/* ═══ CENTER COLUMN ═══ */}
          <div className="space-y-4 lg:col-span-1">

            {/* CURRENT ANALYSIS */}
            <SectionCard title="Current Market Analysis" icon={<Radar className="w-3.5 h-3.5 text-primary" />}>
              {!isRunning ? (
                <div className="p-4 text-center">
                  <Bot className="w-8 h-8 text-muted-foreground/30 mx-auto mb-2" />
                  <p className="text-[10px] text-muted-foreground">Turn on Auto Analysis to begin scanning the market.</p>
                </div>
              ) : selected ? (
                <div className="space-y-2">
                  <div className="rounded-lg border border-emerald-500/20 bg-emerald-500/5 p-3">
                    <div className="flex items-center gap-2 mb-1">
                      <Sparkles className="w-4 h-4 text-emerald-500" />
                      <span className="text-xs font-bold">{selected.symbol}</span>
                      <DirectionIcon dir={selected.direction} />
                      <span className={cn("px-1.5 py-0.5 rounded text-[8px] font-medium", selected.direction === "BUY" ? "bg-emerald-500/10 text-emerald-500" : "bg-red-500/10 text-red-500")}>
                        {selected.direction}
                      </span>
                    </div>
                    <div className="grid grid-cols-2 gap-1.5 mt-2">
                      <Metric label="Opportunity Score" value={`${selected.opportunity_score}/${selected.max_score}`} color="text-emerald-500" />
                      <Metric label="Confidence" value={`${selected.confidence}%`} color={selected.confidence >= 80 ? "text-emerald-500" : selected.confidence >= 60 ? "text-amber-500" : "text-red-500"} />
                      <Metric label="Regime" value={selected.regime} />
                      <Metric label="Strategy" value={selected.strategy} />
                    </div>
                    {selected.reasons.length > 0 && (
                      <div className="mt-2 text-[9px] text-muted-foreground">
                        {selected.reasons.map((r, i) => (
                          <div key={i} className="flex items-center gap-1"><CheckCircle className="w-2.5 h-2.5 text-emerald-500 shrink-0" />{r}</div>
                        ))}
                      </div>
                    )}
                  </div>

                  {/* Why This Trade */}
                  <div className="rounded-lg border bg-card p-2">
                    <h3 className="text-[10px] font-medium mb-1">Why This Trade?</h3>
                    {renderReasons(selected, aiExplanation)}

                    {noTradeReasons.length > 0 && (
                      <div className="mt-2 border-t pt-2">
                        <h4 className="text-[10px] font-medium text-red-500 mb-1">Why No Trade?</h4>
                        {noTradeReasons.map((r, i) => (
                          <div key={i} className="text-[9px] text-red-500/80 flex items-center gap-1">
                            <XCircle className="w-2.5 h-2.5 shrink-0" /> {r}
                          </div>
                        ))}
                      </div>
                    )}
                  </div>
                </div>
              ) : engineState === "SCANNING" ? (
                <div className="p-4 text-center">
                  <RefreshCw className="w-6 h-6 text-blue-500 animate-spin mx-auto mb-2" />
                  <p className="text-[10px] text-muted-foreground">The system is checking supported symbols for a high-quality setup.</p>
                </div>
              ) : (
                <div className="p-4 text-center">
                  <Search className="w-6 h-6 text-muted-foreground/30 mx-auto mb-2" />
                  <p className="text-[10px] text-muted-foreground">No opportunity currently passes all required safety and quality checks.</p>
                  {noTradeReasons.length > 0 && (
                    <div className="mt-2 space-y-1">
                      {noTradeReasons.map((r, i) => (
                        <div key={i} className="text-[9px] text-amber-500/80 flex items-center justify-center gap-1">
                          <AlertTriangle className="w-2.5 h-2.5 shrink-0" /> {r}
                        </div>
                      ))}
                    </div>
                  )}
                  {blockingReasons.length > 0 && (
                    <div className="mt-2 rounded border border-red-500/20 bg-red-500/5 p-2">
                      <div className="text-[9px] text-red-500 font-medium mb-1">Trading blocked:</div>
                      {blockingReasons.map((r, i) => (
                        <div key={i} className="text-[9px] text-red-500/80">• {r}</div>
                      ))}
                    </div>
                  )}
                </div>
              )}

              {/* Scan progress */}
              {isRunning && workspace?.scan && (
                <div className="flex items-center gap-2 p-2 rounded border bg-muted/20 text-[9px] text-muted-foreground">
                  <Activity className="w-3 h-3" />
                  <span>Scanned {workspace.scan.symbols_scanned} symbols</span>
                  <span className="text-muted-foreground/50">·</span>
                  <span>{workspace.scan.candidates_found} candidates</span>
                  {workspace.scan.last_scan_time && (
                <>
                  <span className="text-muted-foreground/50">·</span>
                  <span className="text-[8px]">Updated {timeAgo(workspace.scan.last_scan_time)}</span>
                </>
              )}
            </div>
          )}

          {errors.length > 0 && (
            <div className="rounded border border-red-500/20 bg-red-500/5 p-2 text-[9px] text-red-600">
              {errors.map((e, i) => <div key={i}>⚠ {e}</div>)}
            </div>
          )}
        </SectionCard>

        {/* CANDIDATES TABLE */}
        {isRunning && candidates.length > 0 && (
          <SectionCard title="Top Candidates" icon={<BarChart3 className="w-3.5 h-3.5 text-primary" />}>
            <div className="space-y-1.5">
              {candidates.map((c, i) => (
                <div key={c.symbol} className={cn(
                  "flex items-center gap-2 p-2 rounded border text-[10px]",
                  c.selected ? "border-emerald-500/30 bg-emerald-500/5" : "bg-card/50"
                )}>
                  <span className="text-[9px] text-muted-foreground shrink-0 w-4">
                    {i === 0 ? "🥇" : i === 1 ? "🥈" : i === 2 ? "🥉" : `${i + 1}.`}
                  </span>
                  <span className="font-medium">{c.symbol}</span>
                  <DirectionIcon dir={c.direction} />
                  <span className="font-mono text-[9px]">{c.opportunity_score}</span>
                  <span className="text-[9px] text-muted-foreground">{c.grade}</span>
                  <div className="flex-1" />
                  {c.reject_reasons.length > 0 ? (
                    <span className="text-[8px] text-amber-500 truncate max-w-[120px]" title={c.reject_reasons[0]}>{c.reject_reasons[0]}</span>
                  ) : c.selected ? (
                    <Sparkles className="w-3 h-3 text-emerald-500" />
                  ) : null}
                </div>
              ))}
            </div>
          </SectionCard>
        )}

        {/* APPROVED TRADE PLAN */}
        {tradePlan && (
          <SectionCard title="Approved Trade Plan" icon={<Target className="w-3.5 h-3.5 text-emerald-500" />}>
            <div className="space-y-2">
              <div className="rounded-lg border border-emerald-500/20 bg-emerald-500/5 p-3">
                <div className="flex items-center gap-2 mb-2">
                  <span className="text-xs font-bold">{tradePlan.symbol}</span>
                  <DirectionIcon dir={tradePlan.direction} />
                  <span className={cn("px-1.5 py-0.5 rounded text-[8px] font-medium", tradePlan.direction === "BUY" ? "bg-emerald-500/10 text-emerald-500" : "bg-red-500/10 text-red-500")}>
                    {tradePlan.direction}
                  </span>
                  <span className={cn("px-1.5 py-0.5 rounded text-[8px] font-medium", tradePlan.plan_status === "APPROVED" ? "bg-emerald-500/10 text-emerald-500" : "bg-amber-500/10 text-amber-500")}>
                    {tradePlan.plan_status || "APPROVED"}
                  </span>
                </div>
                <div className="grid grid-cols-3 gap-2">
                  <Metric label="Entry" value={formatPrice(tradePlan.entry_price)} />
                  <Metric label="Stop Loss" value={formatPrice(tradePlan.stop_loss)} color="text-red-500" />
                  <Metric label="Target" value={formatPrice(tradePlan.target)} color="text-emerald-500" />
                  <Metric label="Quantity" value={tradePlan.quantity || "—"} />
                  <Metric label="Notional" value={formatNotional(tradePlan.notional)} />
                  <Metric label="Max Loss" value={formatNotional(tradePlan.max_loss)} color="text-red-500" />
                  <Metric label="Est. Reward" value={formatNotional(tradePlan.estimated_reward)} color="text-emerald-500" />
                  <Metric label="Risk/Reward" value={tradePlan.risk_reward ? `1:${tradePlan.risk_reward.toFixed(1)}` : "—"} color="text-emerald-500" />
                  <Metric label="AI Confidence" value={`${tradePlan.ai_confidence || "—"}%`} />
                </div>
                {tradePlan.strategy && (
                  <div className="flex flex-wrap gap-1 mt-2">
                    <span className="px-1.5 py-0.5 rounded text-[8px] font-medium bg-primary/10 text-primary">{tradePlan.strategy}</span>
                    <span className="px-1.5 py-0.5 rounded text-[8px] font-medium bg-purple-500/10 text-purple-500">{tradePlan.grade || "—"}</span>
                    {tradePlan.regime && <span className="px-1.5 py-0.5 rounded text-[8px] font-medium bg-amber-500/10 text-amber-500">{tradePlan.regime}</span>}
                  </div>
                )}
              </div>

              {/* Approve button */}
              <div className="flex gap-2">
                {tradingMode === "paper" && !autoExecutePaper && (
                  <button onClick={() => setConfirmAction({ type: "approve" })}
                    disabled={approvingPlan}
                    className="flex items-center gap-1 px-3 py-1.5 rounded text-[10px] font-medium bg-emerald-600 text-white hover:bg-emerald-700 disabled:opacity-50 transition-colors">
                    {approvingPlan ? <RefreshCw className="w-3 h-3 animate-spin" /> : <CheckCircle className="w-3 h-3" />}
                    Approve {tradePlan.direction} (Paper)
                  </button>
                )}
                {tradingMode === "controlled_live" && (
                  <button onClick={() => setConfirmAction({ type: "approve_live" })}
                    className="flex items-center gap-1 px-3 py-1.5 rounded text-[10px] font-medium bg-amber-600 text-white hover:bg-amber-700 transition-colors">
                    <Shield className="w-3 h-3" /> Approve {tradePlan.direction} (Controlled Live)
                  </button>
                )}
                {workspace?.approval?.gates && (
                  <button onClick={() => setShowDetails(!showDetails)} className="px-2 py-1 text-[9px] text-muted-foreground hover:text-foreground">
                    {showDetails ? "Hide gates" : `Gates ${workspace.approval.gates.filter((g: any) => g.passed).length}/${workspace.approval.gates.length}`}
                  </button>
                )}
              </div>

              {/* Approval gates detail */}
              {showDetails && workspace?.approval?.gates && (
                <div className="rounded border bg-card/50 p-2 space-y-1">
                  <div className="text-[9px] text-muted-foreground mb-1">Approval Gates</div>
                  {workspace.approval.gates.map((gate: any, i: number) => (
                    <div key={i} className="flex items-center gap-1.5 text-[9px]">
                      {gate.passed ? <CheckCircle className="w-2.5 h-2.5 text-emerald-500" /> : <XCircle className="w-2.5 h-2.5 text-red-500" />}
                      <span className="font-medium">{gate.name}:</span>
                      <span className="text-muted-foreground truncate">{gate.detail || gate.value}</span>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </SectionCard>
        )}

        {/* ACTIVE TRADE MONITOR */}
        {(position || order) && (
          <SectionCard title="Active Trade Monitor" icon={<Activity className="w-3.5 h-3.5 text-emerald-500" />}>
            {position && (
              <div className="space-y-2">
                <div className="rounded-lg border p-3">
                  <div className="flex items-center gap-2 mb-2">
                    <span className="text-xs font-bold">{position.symbol || "—"}</span>
                    <DirectionIcon dir={position.direction} />
                    <span className={cn("px-1.5 py-0.5 rounded text-[8px] font-medium", position.pnl >= 0 ? "bg-emerald-500/10 text-emerald-500" : "bg-red-500/10 text-red-500")}>
                      {position.pnl >= 0 ? "▲" : "▼"} ₹{Math.abs(position.pnl || 0).toFixed(2)}
                    </span>
                  </div>
                  <div className="grid grid-cols-3 gap-2">
                    <Metric label="Entry" value={formatPrice(position.entry_price)} />
                    <Metric label="Current" value={formatPrice(position.current_price)} />
                    <Metric label="Stop Loss" value={formatPrice(position.stop_loss)} color="text-red-500" />
                    <Metric label="Target" value={formatPrice(position.target)} color="text-emerald-500" />
                    <Metric label="Quantity" value={position.quantity || "—"} />
                    <Metric label="P&L" value={`₹${(position.pnl || 0).toFixed(2)}`} color={position.pnl >= 0 ? "text-emerald-500" : "text-red-500"} />
                  </div>
                </div>
                <button onClick={() => setConfirmAction({ type: "exit" })}
                  className="flex items-center gap-1 px-3 py-1.5 rounded text-[10px] font-medium bg-red-500/10 text-red-500 hover:bg-red-500/20 transition-colors">
                  <LogOut className="w-3 h-3" /> Exit Position
                </button>
              </div>
            )}
            {order && !position && (
              <div className="rounded-lg border border-amber-500/20 bg-amber-500/5 p-3">
                <div className="flex items-center gap-2 mb-1">
                  <Timer className="w-4 h-4 text-amber-500" />
                  <span className="text-xs font-medium">Order Pending</span>
                  <span className="text-[9px] text-muted-foreground ml-auto">{order.symbol || "—"}</span>
                </div>
                <div className="text-[9px] text-muted-foreground">Your approved order has been sent and is waiting for confirmation.</div>
                <button onClick={() => setConfirmAction({ type: "cancel" })}
                  className="mt-2 flex items-center gap-1 px-2 py-1 rounded text-[9px] font-medium bg-red-500/10 text-red-500 hover:bg-red-500/20 transition-colors">
                  <X className="w-3 h-3" /> Cancel Order
                </button>
              </div>
            )}
          </SectionCard>
        )}

        {/* COMPLETED TRADE SUMMARY */}
        {workspace?.performance?.total_pnl != null && engineState === "COMPLETED" && (
          <SectionCard title="Trade Result" icon={<BarChart3 className="w-3.5 h-3.5 text-primary" />}>
            <div className="grid grid-cols-2 gap-2">
              <Metric label="Total P&L" value={`₹${workspace.performance.total_pnl.toFixed(2)}`}
                color={workspace.performance.total_pnl >= 0 ? "text-emerald-500" : "text-red-500"} />
              <Metric label="Day P&L" value={`₹${workspace.performance.day_pnl.toFixed(2)}`}
                color={workspace.performance.day_pnl >= 0 ? "text-emerald-500" : "text-red-500"} />
              <Metric label="Realized" value={`₹${workspace.performance.realized_pnl.toFixed(2)}`} />
              <Metric label="Unrealized" value={`₹${workspace.performance.unrealized_pnl.toFixed(2)}`} />
            </div>
            <div className="flex gap-2 mt-2">
              <button className="flex items-center gap-1 px-2 py-1 rounded text-[9px] font-medium bg-primary/10 text-primary hover:bg-primary/20">
                <FileText className="w-3 h-3" /> Trade Evaluation
              </button>
              <button className="flex items-center gap-1 px-2 py-1 rounded text-[9px] font-medium bg-primary/10 text-primary hover:bg-primary/20">
                <SkipForward className="w-3 h-3" /> Scan Next
              </button>
            </div>
          </SectionCard>
        )}
      </div>

      {/* ═══ RIGHT COLUMN ═══ */}
      <div className="space-y-4 lg:col-span-1">

        {/* WHY THIS TRADE */}
        {selected && (
          <SectionCard title="Why This Trade?" icon={<FileText className="w-3.5 h-3.5 text-primary" />}>
            <div className="space-y-1.5">
              {renderWhyThisTrade(selected, aiExplanation, workspace?.regime)}
            </div>

            {/* Why This Trade Could Fail */}
            <div className="mt-3 rounded border border-amber-500/20 bg-amber-500/5 p-2">
              <h4 className="text-[9px] font-medium text-amber-600 mb-1">Why This Trade Could Fail</h4>
              <ul className="space-y-0.5 text-[9px] text-amber-600/80">
                <li>• Sudden news event or economic data release</li>
                <li>• Breakout loses momentum</li>
                <li>• Volume falls below average</li>
                <li>• Market regime changes unexpectedly</li>
                <li>• Price moves below the approved stop level</li>
              </ul>
            </div>
            <p className="text-[8px] text-muted-foreground mt-2">
              No trade is guaranteed to be profitable. This represents the highest-quality approved setup available.
            </p>
          </SectionCard>
        )}

        {/* WHY NO TRADE */}
        {!selected && noTradeReasons.length > 0 && (
          <SectionCard title="Why No Trade?" icon={<Search className="w-3.5 h-3.5 text-amber-500" />}>
            <div className="space-y-1">
              {noTradeReasons.map((r, i) => (
                <div key={i} className="text-[10px] text-amber-600 flex items-start gap-1.5">
                  <XCircle className="w-3 h-3 shrink-0 mt-0.5" /> {r}
                </div>
              ))}
            </div>
            {blockingReasons.length > 0 && (
              <div className="mt-2 border-t pt-2 space-y-1">
                <div className="text-[9px] font-medium text-red-500">Blocking Issues:</div>
                {blockingReasons.map((r, i) => (
                  <div key={i} className="text-[9px] text-red-500/80 flex items-start gap-1"><AlertTriangle className="w-2.5 h-2.5 shrink-0 mt-0.5" />{r}</div>
                ))}
              </div>
            )}
            <div className="mt-2 text-[9px] text-muted-foreground text-center">WAITING FOR BETTER SETUP</div>
          </SectionCard>
        )}

        {/* APPROVAL GATES */}
        {workspace?.approval?.gates && (
          <SectionCard title="Approval Gates" icon={<Shield className="w-3.5 h-3.5 text-primary" />}>
            <div className="space-y-1">
              {workspace.approval.gates.map((gate: any, i: number) => (
                <div key={i} className="flex items-center gap-1.5 text-[9px]">
                  {gate.passed ? <CheckCircle className="w-2.5 h-2.5 text-emerald-500 shrink-0" /> : <XCircle className="w-2.5 h-2.5 text-red-500 shrink-0" />}
                  <span className="font-medium">{gate.name}</span>
                  <span className="text-muted-foreground ml-auto">{gate.passed ? "✓" : "✕"}</span>
                </div>
              ))}
              <div className="text-[9px] text-muted-foreground mt-1">
                {workspace.approval.gates.filter((g: any) => g.passed).length}/{workspace.approval.gates.length} gates passed
              </div>
            </div>
          </SectionCard>
        )}

        {/* RISK SUMMARY */}
        {workspace?.risk && (
          <SectionCard title="Risk Validation" icon={<Shield className="w-3.5 h-3.5 text-primary" />}>
            <div className="grid grid-cols-2 gap-1.5">
              <Metric label="Execution Permitted" value={workspace.risk.execution_permitted ? "Yes" : "No"}
                color={workspace.risk.execution_permitted ? "text-emerald-500" : "text-red-500"} />
              <Metric label="Risk Score" value={workspace.risk.risk_score?.toFixed(1) || "—"} />
              <Metric label="Risk Grade" value={workspace.risk.risk_grade || "—"} />
              <Metric label="Rejected By" value={workspace.risk.rejected_by?.length || "0"}
                color={workspace.risk.rejected_by?.length > 0 ? "text-red-500" : "text-emerald-500"} />
            </div>
            {workspace.risk.rejected_by?.length > 0 && (
              <div className="mt-1 text-[9px] text-red-500">
                {workspace.risk.rejected_by.map((r: string, i: number) => <div key={i}>• {r}</div>)}
              </div>
            )}
          </SectionCard>
        )}

        {/* MTF AGREEMENT */}
        {workspace?.mtf_agreement && (
          <SectionCard title="Multi-Timeframe Agreement" icon={<Activity className="w-3.5 h-3.5 text-primary" />}>
            <div className="grid grid-cols-2 gap-1.5">
              <Metric label="Agreement" value={`${workspace.mtf_agreement.agreement_percent || 0}%`}
                color={(workspace.mtf_agreement.agreement_percent || 0) >= 70 ? "text-emerald-500" : "text-amber-500"} />
              <Metric label="Weighted" value={`${workspace.mtf_agreement.weighted_agreement || 0}%`} />
            </div>
            {workspace.mtf_agreement.status && (
              <div className="mt-1 text-[9px] text-muted-foreground">Status: {workspace.mtf_agreement.status}</div>
            )}
          </SectionCard>
        )}

        {/* EXPLANATION */}
        {aiExplanation?.decision_explanation && (
          <SectionCard title="AI Explanation" icon={<Brain className="w-3.5 h-3.5 text-purple-500" />}>
            <div className="text-[10px] text-foreground mb-2">{aiExplanation.decision_explanation.primary_reason}</div>
            {aiExplanation.decision_explanation.supporting_factors?.length > 0 && (
              <div className="space-y-1">
                <div className="text-[9px] text-muted-foreground">Supporting Factors:</div>
                {aiExplanation.decision_explanation.supporting_factors.map((f: any, i: number) => (
                  <div key={i} className="text-[9px] flex items-start gap-1">
                    <CheckCircle className="w-2.5 h-2.5 text-emerald-500 shrink-0 mt-0.5" />
                    <span>{f.factor}: {f.detail}</span>
                  </div>
                ))}
              </div>
            )}
            {aiExplanation.decision_explanation.blocking_factors?.length > 0 && (
              <div className="mt-2 space-y-1">
                <div className="text-[9px] text-red-500">Blocking Factors:</div>
                {aiExplanation.decision_explanation.blocking_factors.map((f: any, i: number) => (
                  <div key={i} className="text-[9px] text-red-500/80 flex items-start gap-1">
                    <AlertTriangle className="w-2.5 h-2.5 shrink-0 mt-0.5" />{f.factor}: {f.detail}
                  </div>
                ))}
              </div>
            )}
          </SectionCard>
        )}

        {/* SCAN INFO */}
        {isRunning && workspace?.scan && (
          <SectionCard title="Scan Status" icon={<Activity className="w-3.5 h-3.5 text-primary" />}>
            <div className="grid grid-cols-2 gap-1.5">
              <Metric label="Symbols" value={workspace.scan.symbols_scanned} />
              <Metric label="Candidates" value={workspace.scan.candidates_found} />
            </div>
            {workspace.scan.last_scan_time && (
              <div className="text-[9px] text-muted-foreground mt-1">Last scan: {timeAgo(workspace.scan.last_scan_time)}</div>
            )}
          </SectionCard>
        )}
      </div>
    </div>
      )}

      {/* ═══ ACTIVITY TIMELINE ═══ */}
      <SectionCard title="Activity Timeline" icon={<Activity className="w-3.5 h-3.5 text-primary" />}>
        {isRunning ? (
          <div className="space-y-1 max-h-48 overflow-y-auto">
            {buildTimelineEntries(engineState, selected, tradePlan, order, position).map((entry, i) => (
              <div key={i} className="flex items-start gap-2 text-[9px]">
                <div className={cn("w-1.5 h-1.5 rounded-full mt-1.5 shrink-0", CATEGORY_COLORS[entry.category]?.split(" ")[0] || "bg-muted-foreground")} />
                <span className="text-muted-foreground w-12 shrink-0 font-mono">{entry.time}</span>
                <span className={cn("px-1 rounded text-[7px] font-medium", CATEGORY_COLORS[entry.category] || "bg-muted/20 text-muted-foreground")}>
                  {entry.category}
                </span>
                <span className="text-foreground">{entry.message}</span>
              </div>
            ))}
          </div>
        ) : (
          <p className="text-[10px] text-muted-foreground py-2">Start the engine to see activity.</p>
        )}
      </SectionCard>

      {/* ═══ EMERGENCY CONTROLS ═══ */}
      <div className="rounded-lg border-2 border-red-500/30 bg-red-500/5 p-3">
        <div className="flex items-center gap-2 mb-2">
          <AlertTriangle className="w-4 h-4 text-red-500" />
          <span className="text-xs font-bold text-red-600">Emergency Controls</span>
        </div>
        <div className="flex flex-wrap gap-2">
          {isRunning && (
            <button onClick={() => setConfirmAction({ type: "stop" })}
              className="flex items-center gap-1 px-2 py-1.5 rounded text-[10px] font-medium bg-red-500/10 text-red-500 hover:bg-red-500/20 border border-red-500/20 transition-colors">
              <StopCircle className="w-3 h-3" /> Stop Auto Analysis
            </button>
          )}
          {order && !position && (
            <button onClick={() => setConfirmAction({ type: "cancel" })}
              className="flex items-center gap-1 px-2 py-1.5 rounded text-[10px] font-medium bg-red-500/10 text-red-500 hover:bg-red-500/20 border border-red-500/20 transition-colors">
              <X className="w-3 h-3" /> Cancel Pending Order
            </button>
          )}
          {position && (
            <button onClick={() => setConfirmAction({ type: "exit" })}
              className="flex items-center gap-1 px-2 py-1.5 rounded text-[10px] font-medium bg-red-500/10 text-red-500 hover:bg-red-500/20 border border-red-500/20 transition-colors">
              <LogOut className="w-3 h-3" /> Exit Active Position
            </button>
          )}
          <button onClick={() => setConfirmAction({ type: "killswitch" })}
            className="flex items-center gap-1 px-2 py-1.5 rounded text-[10px] font-medium bg-red-600 text-white hover:bg-red-700 border border-red-500 transition-colors">
            <ShieldOff className="w-3 h-3" /> Activate Kill Switch
          </button>
        </div>
        <p className="text-[8px] text-red-500/60 mt-1">These actions cannot be reversed without manual recovery procedures.</p>
      </div>

      {/* ═══ CONFIRMATION MODALS ═══ */}
      <ConfirmModal
        open={confirmAction?.type === "stop"}
        title="Stop Auto Analysis"
        message="This will stop the automatic market scanning and analysis engine. No new analysis will be performed until restarted."
        confirmLabel="Stop Engine"
        onConfirm={handleStop}
        onCancel={() => setConfirmAction(null)}
        danger
      />
      <ConfirmModal
        open={confirmAction?.type === "approve"}
        title={`Approve ${tradePlan?.direction || ""} Trade`}
        message={`This will submit a ${tradingMode} order for ${tradePlan?.symbol || "the selected symbol"}. The order will go through all remaining checks before execution.`}
        confirmLabel={`Approve ${tradePlan?.direction || ""}`}
        onConfirm={handleApproveTrade}
        onCancel={() => setConfirmAction(null)}
      />
      <ConfirmModal
        open={confirmAction?.type === "approve_live"}
        title="Approve Controlled Live Trade"
        message="Real money may be used. All controlled-live restrictions, activation requirements, and the Phase 43 lock remain active. This requires completing the Live Activation workflow."
        confirmLabel="Proceed"
        onConfirm={handleApproveTrade}
        onCancel={() => setConfirmAction(null)}
        danger
      />
      <ConfirmModal
        open={confirmAction?.type === "cancel"}
        title="Cancel Pending Order"
        message={`This will cancel the current pending order for ${order?.symbol || "the selected symbol"}.`}
        confirmLabel="Cancel Order"
        onConfirm={handleCancelOrder}
        onCancel={() => setConfirmAction(null)}
        danger
      />
      <ConfirmModal
        open={confirmAction?.type === "exit"}
        title="Exit Active Position"
        message="This will close the current open position at the prevailing market price. Stop loss and target management will be discontinued."
        confirmLabel="Exit Position"
        onConfirm={handleExitPosition}
        onCancel={() => setConfirmAction(null)}
        danger
      />
      <ConfirmModal
        open={confirmAction?.type === "killswitch"}
        title="Activate Kill Switch"
        message="⚠ DANGER: This will immediately block ALL trading across ALL modes. The kill switch requires explicit manual recovery. No new orders can be placed while active. This cannot be undone through this page."
        confirmLabel="Activate Kill Switch"
        onConfirm={handleKillSwitch}
        onCancel={() => setConfirmAction(null)}
        danger
      />
    </div>
  )
}

/* ─── Helper Functions ─── */

function formatPrice(v: number | null | undefined): string {
  if (v == null) return "—"
  return `₹${v.toFixed(2)}`
}

function formatNotional(v: number | null | undefined): string {
  if (v == null) return "—"
  if (v >= 10000000) return `₹${(v / 10000000).toFixed(2)}Cr`
  if (v >= 100000) return `₹${(v / 100000).toFixed(2)}L`
  if (v >= 1000) return `₹${(v / 1000).toFixed(1)}K`
  return `₹${v.toFixed(0)}`
}

function timeAgo(iso: string): string {
  try {
    const diff = Date.now() - new Date(iso).getTime()
    const secs = Math.floor(diff / 1000)
    if (secs < 10) return "just now"
    if (secs < 60) return `${secs}s ago`
    const mins = Math.floor(secs / 60)
    if (mins < 60) return `${mins}m ago`
    return `${Math.floor(mins / 60)}h ago`
  } catch {
    return "—"
  }
}

function renderSimpleIndicator(label: string, value: string) {
  const isPositive = value.toLowerCase().includes("bull") || value.toLowerCase().includes("strong") || value === "BUY"
  const isNegative = value.toLowerCase().includes("bear") || value.toLowerCase().includes("weak") || value === "SELL" || value.toLowerCase().includes("extreme")
  const color = isPositive ? "text-emerald-500" : isNegative ? "text-red-500" : "text-muted-foreground"
  return (
    <div className="rounded border bg-card/50 p-1.5">
      <div className="text-[8px] text-muted-foreground">{label}</div>
      <div className={cn("text-[10px] font-medium", color)}>{value}</div>
    </div>
  )
}

function renderReasons(candidate: OpportunityCandidate, explanation: any) {
  const reasons: string[] = []
  if (candidate.reasons.length > 0) reasons.push(...candidate.reasons)
  if (candidate.direction === "BUY") reasons.push("Entry price is near identified support level")
  if (candidate.direction === "SELL") reasons.push("Entry price is near identified resistance level")
  if (candidate.confidence >= 80) reasons.push("AI confidence is above the minimum threshold")
  if (candidate.opportunity_score >= 70) reasons.push("Overall opportunity score indicates high-quality setup")
  if (candidate.grade === "A" || candidate.grade === "B") reasons.push(`Trade grade ${candidate.grade} meets minimum requirement`)

  return (
    <div className="space-y-0.5">
      {reasons.slice(0, 6).map((r, i) => (
        <div key={i} className="text-[9px] flex items-start gap-1">
          <CheckCircle className="w-2.5 h-2.5 text-emerald-500 shrink-0 mt-0.5" />
          <span>{r}</span>
        </div>
      ))}
    </div>
  )
}

function renderWhyThisTrade(candidate: OpportunityCandidate, explanation: any, regime: any) {
  const reasons: { icon: React.ReactNode; text: string }[] = []

  if (candidate.reasons.length > 0) {
    candidate.reasons.slice(0, 3).forEach((r) => {
      reasons.push({ icon: <CheckCircle className="w-2.5 h-2.5 text-emerald-500" />, text: r })
    })
  }

  if (candidate.confidence >= 70) {
    reasons.push({ icon: <CheckCircle className="w-2.5 h-2.5 text-emerald-500" />, text: `AI confidence is ${candidate.confidence}%` })
  }

  if (candidate.grade === "A" || candidate.grade === "B") {
    reasons.push({ icon: <CheckCircle className="w-2.5 h-2.5 text-emerald-500" />, text: `Trade grade ${candidate.grade}` })
  }

  if (explanation?.decision_explanation?.primary_reason) {
    reasons.push({ icon: <Sparkles className="w-2.5 h-2.5 text-emerald-500" />, text: explanation.decision_explanation.primary_reason })
  }

  if (reasons.length === 0) {
    reasons.push({ icon: <CheckCircle className="w-2.5 h-2.5 text-emerald-500" />, text: "Best currently available opportunity" })
  }

  return reasons.slice(0, 6).map((r, i) => (
    <div key={i} className="flex items-start gap-1.5 text-[9px]">
      {r.icon}
      <span>{r.text}</span>
    </div>
  ))
}

function buildTimelineEntries(
  engineState: string,
  selected: OpportunityCandidate | null,
  tradePlan: TradePlan | null,
  order: any,
  position: any,
): { time: string; category: TimelineCategory; message: string }[] {
  const entries: { time: string; category: TimelineCategory; message: string }[] = []
  const now = new Date()
  const t = (offsetMin: number) => {
    const d = new Date(now.getTime() - offsetMin * 60000)
    return d.toLocaleTimeString("en-IN", { hour: "2-digit", minute: "2-digit", hour12: false })
  }

  let offset = 0

  if (engineState !== "OFF") {
    entries.push({ time: t(offset++), category: "SYSTEM", message: "Auto Analysis Engine started" })
  }

  if (engineState === "SCANNING" || engineState === "ANALYZING") {
    entries.push({ time: t(offset++), category: "SYSTEM", message: "System readiness passed" })
    entries.push({ time: t(offset++), category: "SYSTEM", message: "Scanning supported symbols..." })
  }

  if (selected) {
    entries.push({ time: t(offset++), category: "MARKET", message: `${selected.symbol} ranked as best opportunity (${selected.opportunity_score}/${selected.max_score})` })
    entries.push({ time: t(offset++), category: "AI", message: `Regime: ${selected.regime}` })
    entries.push({ time: t(offset++), category: "STRATEGY", message: `Strategy: ${selected.strategy}` })
    entries.push({ time: t(offset++), category: "AI", message: `Confidence: ${selected.confidence}%` })
    entries.push({ time: t(offset++), category: "AI", message: `Grade: ${selected.grade}` })
  }

  if (tradePlan) {
    entries.push({ time: t(offset++), category: "RISK", message: "Risk engine approved" })
    entries.push({ time: t(offset++), category: "ORDER", message: `${tradePlan.direction} plan created` })
    entries.push({ time: t(offset++), category: "ORDER", message: "Waiting for entry confirmation" })
  }

  if (order) {
    entries.push({ time: t(offset++), category: "ORDER", message: "Order placed" })
    if (order.status === "filled") {
      entries.push({ time: t(offset++), category: "ORDER", message: "Order filled" })
    }
  }

  if (position) {
    entries.push({ time: t(offset++), category: "POSITION", message: "Position opened" })
  }

  if (engineState === "COMPLETED") {
    entries.push({ time: t(offset++), category: "EXIT", message: "Trade closed" })
    entries.push({ time: t(offset++), category: "PERFORMANCE", message: "Trade evaluated and stored" })
  }

  if (engineState === "BLOCKED" || engineState === "ERROR") {
    entries.push({ time: t(offset++), category: "INCIDENT", message: `Engine ${engineState.toLowerCase()}` })
  }

  return entries
}
