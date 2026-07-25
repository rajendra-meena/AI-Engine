"use client"

import { useState, useEffect, useCallback } from "react"
import {
  Activity, BarChart3, DollarSign, TrendingUp, Shield, RefreshCw,
  Play, Pause, Square, RotateCcw, XCircle, CheckCircle,
} from "lucide-react"
import { paperBrokerService } from "@/services/paperBrokerService"

type TabId = "overview" | "positions" | "orders" | "trades" | "events"

export function PaperTradingDashboard() {
  const [activeTab, setActiveTab] = useState<TabId>("overview")
  const [status, setStatus] = useState<any>(null)
  const [account, setAccount] = useState<any>(null)
  const [positions, setPositions] = useState<any[]>([])
  const [orders, setOrders] = useState<any[]>([])
  const [trades, setTrades] = useState<any[]>([])
  const [events, setEvents] = useState<any[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const fetchAll = useCallback(async () => {
    setError(null)
    try {
      const [s, a, p, o, t, e] = await Promise.all([
        paperBrokerService.getStatus().catch(() => null),
        paperBrokerService.getAccount().catch(() => null),
        paperBrokerService.getPositions().catch(() => null),
        paperBrokerService.getOrders().catch(() => null),
        paperBrokerService.getTrades().catch(() => null),
        paperBrokerService.getEvents().catch(() => null),
      ])
      if (s) setStatus(s)
      if (a) setAccount(a)
      if (p) setPositions(p.positions || [])
      if (o) setOrders(o.orders || [])
      if (t) setTrades(t.trades || [])
      if (e) setEvents(e.events || [])
    } catch { setError("Failed to load") }
    setLoading(false)
  }, [])

  useEffect(() => {
    fetchAll()
    const interval = setInterval(fetchAll, 5000)
    return () => clearInterval(interval)
  }, [fetchAll])

  const handleAction = async (action: string) => {
    try {
      if (action === "start") await paperBrokerService.start()
      else if (action === "pause") await paperBrokerService.pause()
      else if (action === "resume") await paperBrokerService.resume()
      else if (action === "stop") await paperBrokerService.stop()
      else if (action === "reset") await paperBrokerService.reset()
      await fetchAll()
    } catch { setError("Action failed") }
  }

  const running = status?.running
  const paused = status?.paused

  const tabs = [
    { id: "overview" as TabId, label: "Overview", icon: <Activity className="w-3.5 h-3.5" /> },
    { id: "positions" as TabId, label: "Positions", icon: <TrendingUp className="w-3.5 h-3.5" /> },
    { id: "orders" as TabId, label: "Orders", icon: <BarChart3 className="w-3.5 h-3.5" /> },
    { id: "trades" as TabId, label: "Closed Trades", icon: <DollarSign className="w-3.5 h-3.5" /> },
    { id: "events" as TabId, label: "Events", icon: <Activity className="w-3.5 h-3.5" /> },
  ]

  return (
    <div className="space-y-4">
      <div className="flex items-center gap-2">
        <DollarSign className="w-5 h-5 text-primary" />
        <h1 className="text-lg font-bold">Paper Trading</h1>
        <button onClick={fetchAll} className="ml-auto p-1 rounded text-muted-foreground hover:text-foreground hover:bg-accent">
          <RefreshCw className={`w-3.5 h-3.5 ${loading ? "animate-spin" : ""}`} />
        </button>
      </div>

      {/* Controls */}
      <div className="flex items-center gap-2 p-2 rounded-lg border bg-card text-[10px]">
        <span className={`font-medium ${running && !paused ? "text-emerald-500" : paused ? "text-amber-500" : "text-muted-foreground"}`}>
          {running && !paused ? "RUNNING" : paused ? "PAUSED" : "STOPPED"}
        </span>
        {!running && <button onClick={() => handleAction("start")} className="flex items-center gap-1 px-2 py-1 rounded bg-emerald-500/10 text-emerald-600 hover:bg-emerald-500/20"><Play className="w-3 h-3" /> Start</button>}
        {running && !paused && <button onClick={() => handleAction("pause")} className="flex items-center gap-1 px-2 py-1 rounded bg-amber-500/10 text-amber-600 hover:bg-amber-500/20"><Pause className="w-3 h-3" /> Pause</button>}
        {paused && <button onClick={() => handleAction("resume")} className="flex items-center gap-1 px-2 py-1 rounded bg-emerald-500/10 text-emerald-600 hover:bg-emerald-500/20"><Play className="w-3 h-3" /> Resume</button>}
        {running && <button onClick={() => handleAction("stop")} className="flex items-center gap-1 px-2 py-1 rounded bg-red-500/10 text-red-600 hover:bg-red-500/20"><Square className="w-3 h-3" /> Stop</button>}
        <button onClick={() => handleAction("reset")} className="flex items-center gap-1 px-2 py-1 rounded bg-muted/30 text-muted-foreground hover:bg-muted/50"><RotateCcw className="w-3 h-3" /> Reset</button>
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
            <MetricCard label="Equity" value={`$${(account?.equity || 0).toLocaleString()}`} />
            <MetricCard label="Available Cash" value={`$${(account?.available_cash || 0).toLocaleString()}`} color="text-emerald-500" />
            <MetricCard label="Total P&L" value={`$${(account?.total_pnl || 0).toFixed(2)}`}
              color={(account?.total_pnl || 0) >= 0 ? "text-emerald-500" : "text-red-500"} />
            <MetricCard label="Return" value={`${account?.return_pct || 0}%`}
              color={(account?.return_pct || 0) >= 0 ? "text-emerald-500" : "text-red-500"} />
          </div>
          <div className="grid grid-cols-4 gap-3">
            <MetricCard label="Open Positions" value={String(account?.open_positions || 0)} />
            <MetricCard label="Closed Trades" value={String(account?.closed_trades || 0)} />
            <MetricCard label="Win Rate" value={`${account?.win_rate || 0}%`} color={(account?.win_rate || 0) >= 50 ? "text-emerald-500" : "text-amber-500"} />
            <MetricCard label="Used Margin" value={`$${(account?.used_margin || 0).toLocaleString()}`} color="text-amber-500" />
          </div>
        </div>
      )}

      {activeTab === "positions" && (
        <div className="space-y-3">
          {positions.length === 0 ? (
            <div className="p-8 text-center text-[10px] text-muted-foreground">No open positions</div>
          ) : (
            <div className="border rounded-lg overflow-hidden">
              <table className="w-full text-[10px]">
                <thead><tr className="bg-muted/30 border-b">
                  <th className="text-left px-3 py-2">Symbol</th>
                  <th className="text-left px-3 py-2">Side</th>
                  <th className="text-right px-3 py-2">Qty</th>
                  <th className="text-right px-3 py-2">Entry</th>
                  <th className="text-right px-3 py-2">LTP</th>
                  <th className="text-right px-3 py-2">SL</th>
                  <th className="text-right px-3 py-2">Target</th>
                  <th className="text-right px-3 py-2">Unrealized P&L</th>
                </tr></thead>
                <tbody className="divide-y">
                  {positions.map((p: any, i: number) => (
                    <tr key={p.trade_id || i} className="hover:bg-muted/20">
                      <td className="px-3 py-1.5 font-medium">{p.symbol}</td>
                      <td className={`px-3 py-1.5 ${p.direction === "LONG" ? "text-emerald-500" : "text-red-500"}`}>{p.direction}</td>
                      <td className="px-3 py-1.5 text-right font-mono">{p.quantity}</td>
                      <td className="px-3 py-1.5 text-right font-mono">{p.entry_price?.toFixed(2)}</td>
                      <td className="px-3 py-1.5 text-right font-mono">{p.current_price?.toFixed(2)}</td>
                      <td className="px-3 py-1.5 text-right font-mono">{p.stop_loss?.toFixed(2) || "—"}</td>
                      <td className="px-3 py-1.5 text-right font-mono">{p.target?.toFixed(2) || "—"}</td>
                      <td className={`px-3 py-1.5 text-right font-mono ${(p.unrealized_pnl || 0) >= 0 ? "text-emerald-500" : "text-red-500"}`}>
                        ${(p.unrealized_pnl || 0).toFixed(2)}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      )}

      {activeTab === "orders" && <OrdersTab orders={orders} />}
      {activeTab === "trades" && <TradesTab trades={trades} />}
      {activeTab === "events" && <EventsTab events={events} />}
    </div>
  )
}

function MetricCard({ label, value, color }: { label: string; value: string; color?: string }) {
  return <div className="rounded-lg border bg-card p-3">
    <div className="text-[9px] text-muted-foreground uppercase tracking-wider">{label}</div>
    <div className={`text-lg font-bold font-mono mt-0.5 ${color || ""}`}>{value}</div>
  </div>
}

function OrdersTab({ orders }: { orders: any[] }) {
  if (orders.length === 0) return <div className="p-8 text-center text-[10px] text-muted-foreground">No orders</div>
  return <div className="border rounded-lg overflow-hidden">
    <table className="w-full text-[10px]">
      <thead><tr className="bg-muted/30 border-b">
        <th className="text-left px-3 py-2">Order ID</th>
        <th className="text-left px-3 py-2">Symbol</th>
        <th className="text-left px-3 py-2">Side</th>
        <th className="text-right px-3 py-2">Qty</th>
        <th className="text-right px-3 py-2">Price</th>
        <th className="text-left px-3 py-2">Status</th>
      </tr></thead>
      <tbody className="divide-y">
        {orders.map((o: any, i: number) => (
          <tr key={o.id || i} className="hover:bg-muted/20">
            <td className="px-3 py-1.5 font-mono text-muted-foreground text-[9px]">{o.id?.slice(-8)}</td>
            <td className="px-3 py-1.5 font-medium">{o.symbol}</td>
            <td className={`px-3 py-1.5 ${o.side === "BUY" ? "text-emerald-500" : "text-red-500"}`}>{o.side}</td>
            <td className="px-3 py-1.5 text-right font-mono">{o.quantity}</td>
            <td className="px-3 py-1.5 text-right font-mono">{o.price?.toFixed(2)}</td>
            <td className="px-3 py-1.5">
              <span className="px-1.5 py-0.5 rounded text-[8px] font-medium bg-emerald-500/10 text-emerald-500">{o.status}</span>
            </td>
          </tr>
        ))}
      </tbody>
    </table>
  </div>
}

function TradesTab({ trades }: { trades: any[] }) {
  if (trades.length === 0) return <div className="p-8 text-center text-[10px] text-muted-foreground">No closed trades yet</div>
  return <div className="border rounded-lg overflow-hidden">
    <table className="w-full text-[10px]">
      <thead><tr className="bg-muted/30 border-b">
        <th className="text-left px-3 py-2">Symbol</th>
        <th className="text-left px-3 py-2">Direction</th>
        <th className="text-right px-3 py-2">Entry</th>
        <th className="text-right px-3 py-2">Exit</th>
        <th className="text-right px-3 py-2">Qty</th>
        <th className="text-right px-3 py-2">P&L</th>
        <th className="text-left px-3 py-2">Reason</th>
      </tr></thead>
      <tbody className="divide-y">
        {trades.map((t: any, i: number) => (
          <tr key={i} className="hover:bg-muted/20">
            <td className="px-3 py-1.5 font-medium">{t.symbol}</td>
            <td className={`px-3 py-1.5 ${t.direction === "LONG" ? "text-emerald-500" : "text-red-500"}`}>{t.direction}</td>
            <td className="px-3 py-1.5 text-right font-mono">{t.entry_price?.toFixed(2)}</td>
            <td className="px-3 py-1.5 text-right font-mono">{t.exit_price?.toFixed(2)}</td>
            <td className="px-3 py-1.5 text-right font-mono">{t.quantity}</td>
            <td className={`px-3 py-1.5 text-right font-mono ${(t.realized_pnl || 0) >= 0 ? "text-emerald-500" : "text-red-500"}`}>
              ${(t.realized_pnl || 0).toFixed(2)}
            </td>
            <td className="px-3 py-1.5 text-muted-foreground">{t.exit_reason || "—"}</td>
          </tr>
        ))}
      </tbody>
    </table>
  </div>
}

function EventsTab({ events }: { events: any[] }) {
  if (events.length === 0) return <div className="p-8 text-center text-[10px] text-muted-foreground">No events yet</div>
  return <div className="border rounded-lg overflow-auto max-h-[500px]">
    <div className="divide-y text-[10px]">
      {events.map((e: any, i: number) => (
        <div key={i} className="flex items-center gap-2 px-3 py-1.5 hover:bg-muted/20">
          <span className="font-mono text-muted-foreground w-20">{e.timestamp?.split("T")[1]?.slice(0, 8) || ""}</span>
          <span className={`px-1.5 py-0.5 rounded text-[8px] font-medium ${
            e.type?.includes("closed") ? "bg-red-500/10 text-red-500" : "bg-blue-500/10 text-blue-500"
          }`}>{e.type}</span>
          <span className="font-medium">{e.symbol}</span>
          {e.pnl != null && <span className={`ml-auto font-mono ${e.pnl >= 0 ? "text-emerald-500" : "text-red-500"}`}>${e.pnl.toFixed(2)}</span>}
        </div>
      ))}
    </div>
  </div>
}
