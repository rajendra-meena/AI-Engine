"use client"

import { useState, useRef, useCallback, useEffect, useMemo } from "react"
import { useLayoutStore } from "@/store/useLayoutStore"
import { cn } from "@/lib/utils"
import {
  List, BarChart3, TrendingUp, Activity, Shield, AlertTriangle,
  Terminal, Radio, Server, History, Globe, Wifi, Play,
  BrainCircuit, GitBranch,
} from "lucide-react"

/* ─── Mode Detection ─── */

type RuntimeMode = "replay" | "paper" | "controlled_live" | "production" | "developer"

function detectMode(activeNav: string): RuntimeMode {
  if (["replay", "workspace", "backtest"].includes(activeNav)) return "replay"
  if (["paper-trading", "portfolio", "paper"].includes(activeNav)) return "paper"
  if (["live", "live-control", "live-activation", "live-execution", "pre-live"].includes(activeNav)) return "controlled_live"
  if (["production-readiness", "production"].includes(activeNav)) return "production"
  return "developer"
}

/* ─── Tab Definitions ─── */

interface TabDef {
  id: string
  label: string
  icon: React.ReactNode
  group: string
  visibleIn: RuntimeMode[]
}

const ALL_TABS: TabDef[] = [
  // Trading
  { id: "orders", label: "Orders", icon: <List className="w-3 h-3" />, group: "Trading", visibleIn: ["replay", "paper", "controlled_live", "production", "developer"] },
  { id: "positions", label: "Positions", icon: <BarChart3 className="w-3 h-3" />, group: "Trading", visibleIn: ["replay", "paper", "controlled_live", "production", "developer"] },
  { id: "trades", label: "Trades", icon: <TrendingUp className="w-3 h-3" />, group: "Trading", visibleIn: ["replay", "paper", "controlled_live", "production", "developer"] },
  { id: "executions", label: "Executions", icon: <Activity className="w-3 h-3" />, group: "Trading", visibleIn: ["controlled_live", "production", "developer"] },

  // AI
  { id: "ai-decision", label: "AI Decision", icon: <BrainCircuit className="w-3 h-3" />, group: "AI", visibleIn: ["replay", "paper", "controlled_live", "developer"] },
  { id: "market-regime", label: "Regime", icon: <GitBranch className="w-3 h-3" />, group: "AI", visibleIn: ["controlled_live", "developer"] },

  // Risk
  { id: "risk", label: "Risk", icon: <Shield className="w-3 h-3" />, group: "Risk", visibleIn: ["paper", "controlled_live", "production", "developer"] },
  { id: "alerts", label: "Alerts", icon: <AlertTriangle className="w-3 h-3" />, group: "Risk", visibleIn: ["paper", "controlled_live", "production", "developer"] },

  // Operations
  { id: "logs", label: "Logs", icon: <Terminal className="w-3 h-3" />, group: "Operations", visibleIn: ["paper", "controlled_live", "production", "developer"] },
  { id: "operations", label: "Operations", icon: <Server className="w-3 h-3" />, group: "Operations", visibleIn: ["production", "developer"] },

  // Live Monitor
  { id: "live-monitor", label: "Live Monitor", icon: <Radio className="w-3 h-3" />, group: "Live", visibleIn: ["controlled_live", "production", "developer"] },

  // Developer
  { id: "replay", label: "Replay", icon: <History className="w-3 h-3" />, group: "Developer", visibleIn: ["replay", "developer"] },
  { id: "api", label: "API", icon: <Globe className="w-3 h-3" />, group: "Developer", visibleIn: ["developer"] },
  { id: "websocket", label: "WebSocket", icon: <Wifi className="w-3 h-3" />, group: "Developer", visibleIn: ["developer"] },
]

const MODE_LABELS: Record<RuntimeMode, string> = {
  replay: "Replay Mode",
  paper: "Paper Trading",
  controlled_live: "Controlled Live",
  production: "Production",
  developer: "Developer Mode",
}

const MODE_COLORS: Record<RuntimeMode, string> = {
  replay: "text-blue-500 bg-blue-500/10",
  paper: "text-emerald-500 bg-emerald-500/10",
  controlled_live: "text-amber-500 bg-amber-500/10",
  production: "text-violet-500 bg-violet-500/10",
  developer: "text-muted-foreground bg-muted/30",
}

/* ─── Tab Panels ─── */

function OrdersTab() {
  return <div className="text-[11px] text-muted-foreground">
    <p className="font-medium text-foreground mb-2">Orders</p>
    <p>No open orders. Place orders from the trading panel.</p>
  </div>
}

function PositionsTab() {
  return <div className="text-[11px] text-muted-foreground">
    <p className="font-medium text-foreground mb-2">Open Positions</p>
    <p>No open positions. Positions appear here when you start trading.</p>
  </div>
}

function TradesTab() {
  return <div className="text-[11px] text-muted-foreground">
    <p className="font-medium text-foreground mb-2">Recent Trades</p>
    <p>No trades yet. Start paper trading from the Portfolio page.</p>
  </div>
}

function ExecutionsTab() {
  return <div className="space-y-2 text-[11px]">
    <div className="grid grid-cols-4 gap-2">
      <Metric label="Queue" value="0" />
      <Metric label="Pending" value="0" />
      <Metric label="Slippage" value="0.0bps" color="text-emerald-500" />
      <Metric label="Fill Quality" value="100%" color="text-emerald-500" />
    </div>
    <div className="grid grid-cols-3 gap-2">
      <Metric label="Latency" value="--ms" />
      <Metric label="Partial Fills" value="0" />
      <Metric label="Rejected" value="0" color="text-red-500" />
    </div>
    <div className="rounded border border-emerald-500/20 bg-emerald-500/5 p-2 text-center text-[10px] text-emerald-600">✓ Reconciliation: Synced</div>
  </div>
}

function AIDecisionTab() {
  return <div className="space-y-2 text-[11px]">
    <div className="grid grid-cols-3 gap-2">
      <Metric label="Decision" value="NO TRADE" color="text-muted-foreground" />
      <Metric label="Confidence" value="--%" />
      <Metric label="Grade" value="--" />
    </div>
    <div className="rounded border bg-card p-2">
      <div className="text-[9px] text-muted-foreground uppercase mb-1">Approval Gates</div>
      <div className="text-center text-muted-foreground">Waiting for AI decision...</div>
    </div>
  </div>
}

function MarketRegimeTab() {
  return <div className="space-y-2 text-[11px]">
    <div className="grid grid-cols-3 gap-2">
      <Metric label="Regime" value="--" />
      <Metric label="Confidence" value="--%" />
      <Metric label="Transition" value="0%" />
    </div>
    <div className="grid grid-cols-2 gap-2">
      <Metric label="Strategy" value="--" />
      <Metric label="Avoid" value="--" />
    </div>
  </div>
}

function RiskTab() {
  return <div className="space-y-2 text-[11px]">
    <div className="grid grid-cols-4 gap-2">
      <Metric label="Risk Score" value="0" color="text-emerald-500" />
      <Metric label="Daily Loss" value="₹0" />
      <Metric label="Exposure" value="0%" />
      <Metric label="Open Risk" value="₹0" />
    </div>
    <div className="flex items-center gap-2 p-1.5 rounded border border-emerald-500/20 bg-emerald-500/5 text-[10px] text-emerald-600">
      <Shield className="w-3 h-3" /> Trading Allowed
    </div>
  </div>
}

function AlertsTab() {
  return <div className="text-[11px] text-muted-foreground">
    <p className="font-medium text-foreground mb-2">Alerts</p>
    <p>No alerts configured. Set up alerts from the chart or settings page.</p>
  </div>
}

function LiveMonitorTab() {
  return <div className="space-y-2 text-[11px]">
    <div className="grid grid-cols-3 gap-2">
      <Metric label="Status" value="LOCKED" color="text-amber-500" />
      <Metric label="Canary" value="--" />
      <Metric label="Trades Left" value="0" />
    </div>
    <div className="rounded border border-amber-500/20 bg-amber-500/5 p-2 text-center text-[10px] text-amber-600">🔒 Phase 43 Execution Lock Active</div>
  </div>
}

function OperationsTab() {
  return <div className="space-y-2 text-[11px]">
    <div className="grid grid-cols-4 gap-2">
      <Metric label="Health" value="Good" color="text-emerald-500" />
      <Metric label="Incidents" value="0" color="text-emerald-500" />
      <Metric label="DB" value="Connected" color="text-emerald-500" />
      <Metric label="Event Bus" value="Active" color="text-emerald-500" />
    </div>
    <div className="flex items-center gap-2 p-1.5 rounded border border-emerald-500/20 bg-emerald-500/5 text-[10px] text-emerald-600">
      <Activity className="w-3 h-3" /> All systems operational
    </div>
  </div>
}

function LogsTab() {
  const [filter, setFilter] = useState<string>("all")
  const filters = ["all", "info", "warning", "error", "ai", "broker", "risk", "live", "system", "operations"]
  const [paused, setPaused] = useState(false)
  const logLines = [
    { level: "info", tag: "system", msg: "System initialized" },
    { level: "info", tag: "system", msg: "EventBus started" },
    { level: "info", tag: "system", msg: "WebSocket gateway connected" },
    { level: "warn", tag: "live", msg: "Phase 43 execution lock active" },
    { level: "info", tag: "broker", msg: "Broker session established" },
    { level: "info", tag: "ai", msg: "AI Decision Engine ready" },
    { level: "info", tag: "risk", msg: "Risk Engine initialized" },
    { level: "warn", tag: "market", msg: "Waiting for market data..." },
    { level: "info", tag: "system", msg: "All subsystems operational" },
  ]

  const levelColor = (lvl: string) => {
    switch (lvl) {
      case "error": return "text-red-500"
      case "warn": return "text-yellow-500"
      case "info": return "text-green-500"
      default: return "text-muted-foreground"
    }
  }

  const filtered = filter === "all" ? logLines : logLines.filter(l => l.level === filter || l.tag === filter)

  return (
    <div className="space-y-1.5 text-[11px] font-mono">
      {/* Toolbar */}
      <div className="flex items-center gap-1 pb-1 border-b overflow-x-auto">
        {filters.map(f => (
          <button key={f} onClick={() => setFilter(f)}
            className={cn("px-1.5 py-0.5 rounded text-[9px] font-medium transition-colors shrink-0",
              filter === f ? "bg-primary/20 text-primary" : "text-muted-foreground hover:bg-accent")}>
            {f.toUpperCase()}
          </button>
        ))}
        <div className="flex-1" />
        <button onClick={() => setPaused(!paused)}
          className={cn("px-1.5 py-0.5 rounded text-[9px] font-medium",
            paused ? "bg-amber-500/10 text-amber-500" : "text-muted-foreground hover:bg-accent")}>
          {paused ? "▶ Resume" : "⏸ Pause"}
        </button>
      </div>
      {/* Log lines */}
      <div className="max-h-[180px] overflow-y-auto space-y-0.5">
        {filtered.map((l, i) => (
          <div key={i} className="flex items-center gap-2">
            <span className={cn("w-12 shrink-0", levelColor(l.level))}>[{l.level.toUpperCase()}]</span>
            <span className="text-[9px] text-muted-foreground w-16 shrink-0">&lt;{l.tag}&gt;</span>
            <span className="text-foreground">{l.msg}</span>
          </div>
        ))}
      </div>
    </div>
  )
}

function ReplayTab() {
  return <div className="text-[11px] text-muted-foreground">
    <p className="font-medium text-foreground mb-2">Replay Controls</p>
    <p>Go to the Replay page to use the full Replay Studio.</p>
  </div>
}

function ApiTab() {
  return <div className="text-[11px] font-mono space-y-1">
    <p className="font-medium text-foreground mb-2">API Status</p>
    <p><span className="text-green-500">●</span> REST API: <span className="text-foreground">Connected</span></p>
    <p><span className="text-green-500">●</span> Market Data: <span className="text-foreground">Zerodha Kite</span></p>
    <p><span className="text-green-500">●</span> Predictions: <span className="text-foreground">Active</span></p>
  </div>
}

function WebSocketTab() {
  return <div className="text-[11px] font-mono space-y-1">
    <p className="font-medium text-foreground mb-2">WebSocket Connection</p>
    <p><span className="text-green-500">●</span> Status: <span className="text-foreground">Connected</span></p>
    <p><span className="text-green-500">●</span> Latency: <span className="text-foreground">-- ms</span></p>
  </div>
}

const TAB_COMPONENTS: Record<string, React.FC> = {
  orders: OrdersTab, positions: PositionsTab, trades: TradesTab, executions: ExecutionsTab,
  "ai-decision": AIDecisionTab, "market-regime": MarketRegimeTab,
  risk: RiskTab, alerts: AlertsTab,
  logs: LogsTab, operations: OperationsTab,
  "live-monitor": LiveMonitorTab,
  replay: ReplayTab, api: ApiTab, websocket: WebSocketTab,
}

/* ─── Notification Badge Store ─── */

const tabNotifications: Record<string, number> = {}

export function notifyTab(tabId: string) {
  tabNotifications[tabId] = (tabNotifications[tabId] || 0) + 1
}

/* ─── Metric Card Helper ─── */

function Metric({ label, value, color }: { label: string; value: string; color?: string }) {
  return (
    <div className="rounded border bg-card p-1.5">
      <div className="text-[9px] text-muted-foreground uppercase">{label}</div>
      <div className={cn("text-xs font-bold font-mono", color || "text-foreground")}>{value}</div>
    </div>
  )
}

/* ─── Main BottomPanel ─── */

export function BottomPanel() {
  const { bottomPanelOpen, bottomPanelHeight, toggleBottomPanel, setBottomPanelHeight, activeNav } = useLayoutStore()
  const mode = detectMode(activeNav)
  const [activeTab, setActiveTab] = useState("logs")
  const [badges, setBadges] = useState<Record<string, number>>({})
  const resizeRef = useRef<HTMLDivElement>(null)

  // Visible tabs for current mode
  const visibleTabs = useMemo(() => ALL_TABS.filter(t => t.visibleIn.includes(mode)), [mode])

  // Remember last tab per mode
  const lastTabKey = `bottomPanelTab_${mode}`
  useEffect(() => {
    const t = setTimeout(() => {
      const saved = localStorage.getItem(lastTabKey)
      if (saved && visibleTabs.some(t => t.id === saved)) {
        setActiveTab(saved)
      } else if (visibleTabs.length > 0) {
        setActiveTab(visibleTabs[0].id)
      }
    }, 0)
    return () => clearTimeout(t)
  }, [mode, lastTabKey, visibleTabs])

  useEffect(() => {
    localStorage.setItem(lastTabKey, activeTab)
  }, [activeTab, lastTabKey])

  // Keyboard shortcuts Ctrl+1..9
  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      if (e.ctrlKey && e.key >= "1" && e.key <= "9") {
        const idx = parseInt(e.key) - 1
        if (idx < visibleTabs.length) {
          setActiveTab(visibleTabs[idx].id)
        }
      }
    }
    window.addEventListener("keydown", handler)
    return () => window.removeEventListener("keydown", handler)
  }, [visibleTabs])

  // Poll for notification badges
  useEffect(() => {
    const interval = setInterval(() => {
      setBadges({ ...tabNotifications })
    }, 1000)
    return () => clearInterval(interval)
  }, [])

  // Resize handler
  const handleMouseDown = useCallback((e: React.MouseEvent) => {
    e.preventDefault()
    const startY = e.clientY
    const startH = bottomPanelHeight
    const onMove = (ev: MouseEvent) => setBottomPanelHeight(startH - (ev.clientY - startY))
    const onUp = () => { document.removeEventListener("mousemove", onMove); document.removeEventListener("mouseup", onUp) }
    document.addEventListener("mousemove", onMove)
    document.addEventListener("mouseup", onUp)
  }, [bottomPanelHeight, setBottomPanelHeight])

  const ActiveContent = TAB_COMPONENTS[activeTab] || LogsTab

  return (
    <div className="flex flex-col border-t bg-card shrink-0" style={{ height: bottomPanelOpen ? bottomPanelHeight : 28 }} role="region" aria-label="Bottom panel">
      {/* Resize handle */}
      <div ref={resizeRef} onMouseDown={handleMouseDown}
        className="h-1 cursor-row-resize hover:bg-primary/50 transition-colors shrink-0" role="separator" aria-orientation="horizontal" />

      {/* Tab bar */}
      <div className="flex items-center border-b shrink-0 overflow-x-auto">
        {visibleTabs.map((tab) => {
          const badge = badges[tab.id]
          return (
            <button key={tab.id} onClick={() => { setActiveTab(tab.id); tabNotifications[tab.id] = 0 }}
              className={cn(
                "relative flex items-center gap-1 px-2.5 py-1.5 text-[10px] font-medium transition-colors border-r shrink-0",
                activeTab === tab.id
                  ? "bg-muted/50 text-foreground"
                  : "text-muted-foreground hover:text-foreground hover:bg-accent/50"
              )}>
              {tab.icon}
              {tab.label}
              {badge ? <span className="ml-0.5 w-3.5 h-3.5 flex items-center justify-center rounded-full text-[8px] font-bold bg-primary text-primary-foreground">{badge}</span> : null}
            </button>
          )
        })}
        <div className="flex-1" />

        {/* Mode badge */}
        <span className={cn("hidden sm:inline-flex items-center gap-1 px-1.5 py-0.5 rounded text-[8px] font-medium border mx-1 shrink-0", MODE_COLORS[mode])}>
          <Play className="w-2 h-2" /> {MODE_LABELS[mode]}
        </span>

        <button onClick={toggleBottomPanel} className="px-2 py-1 text-[10px] text-muted-foreground hover:text-foreground shrink-0" aria-label={bottomPanelOpen ? "Minimize" : "Expand"}>
          {bottomPanelOpen ? "—" : "+"}
        </button>
      </div>

      {/* Content */}
      <div className="flex-1 overflow-y-auto p-2 text-xs text-muted-foreground">
        {bottomPanelOpen ? <ActiveContent /> : (
          <div className="flex items-center gap-2 text-[10px] text-muted-foreground/50">
            <span>{MODE_LABELS[mode]}</span>
            <span>·</span>
            <span className="capitalize">{activeTab} panel minimized</span>
          </div>
        )}
      </div>
    </div>
  )
}
