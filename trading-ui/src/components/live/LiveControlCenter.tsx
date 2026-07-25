"use client"

import { useState, useEffect, useCallback } from "react"
import {
  Activity, AlertTriangle, BarChart3, DollarSign, RefreshCw,
  Shield, TrendingUp, Wallet, XCircle, Clock, Wifi, WifiOff,
} from "lucide-react"
import { liveControlService } from "@/services/liveControlService"
import { useBrokerStore } from "@/store/useBrokerStore"

type TabId = "overview" | "positions" | "orders" | "trades" | "events" | "reconciliation"

export function LiveControlCenter() {
  const [activeTab, setActiveTab] = useState<TabId>("overview")
  const [account, setAccount] = useState<any>(null)
  const [positions, setPositions] = useState<any>(null)
  const [orders, setOrders] = useState<any>(null)
  const [trades, setTrades] = useState<any>(null)
  const [events, setEvents] = useState<any>(null)
  const [reconciliation, setReconciliation] = useState<any>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const brokerConnected = useBrokerStore((s) => s.connected)
  const brokerUser = useBrokerStore((s) => s.user_id || s.user_name)

  const fetchAll = useCallback(async () => {
    setError(null)
    try {
      const [acct, pos, ord, trds, evts, recon] = await Promise.all([
        liveControlService.getAccount().catch(() => null),
        liveControlService.getPositions().catch(() => null),
        liveControlService.getOrders().catch(() => null),
        liveControlService.getTrades().catch(() => null),
        liveControlService.getEvents().catch(() => null),
        liveControlService.getReconciliation().catch(() => null),
      ])
      if (acct) setAccount(acct)
      if (pos) setPositions(pos)
      if (ord) setOrders(ord)
      if (trds) setTrades(trds)
      if (evts) setEvents(evts)
      if (recon) setReconciliation(recon)
    } catch {
      setError("Failed to load live data")
    }
    setLoading(false)
  }, [])

  useEffect(() => {
    fetchAll()
    const interval = setInterval(fetchAll, 10000)
    return () => clearInterval(interval)
  }, [fetchAll])

  const tabs = [
    { id: "overview" as TabId, label: "Overview", icon: <Activity className="w-3.5 h-3.5" /> },
    { id: "positions" as TabId, label: "Positions", icon: <TrendingUp className="w-3.5 h-3.5" /> },
    { id: "orders" as TabId, label: "Orders", icon: <BarChart3 className="w-3.5 h-3.5" /> },
    { id: "trades" as TabId, label: "Trades", icon: <DollarSign className="w-3.5 h-3.5" /> },
    { id: "events" as TabId, label: "Events", icon: <Activity className="w-3.5 h-3.5" /> },
    { id: "reconciliation" as TabId, label: "Reconciliation", icon: <Shield className="w-3.5 h-3.5" /> },
  ]

  return (
    <div className="space-y-4">
      {/* Header */}
      <div className="flex items-center gap-2">
        <Activity className="w-5 h-5 text-primary" />
        <h1 className="text-lg font-bold">Live Trading Control Center</h1>
        <button onClick={fetchAll} className="ml-auto p-1 rounded text-muted-foreground hover:text-foreground hover:bg-accent" disabled={loading}>
          <RefreshCw className={`w-3.5 h-3.5 ${loading ? "animate-spin" : ""}`} />
        </button>
      </div>

      {/* Status Bar */}
      <div className="flex items-center gap-3 p-2 rounded-lg border bg-card text-[10px]">
        <div className="flex items-center gap-1">
          {brokerConnected ? <Wifi className="w-3 h-3 text-emerald-500" /> : <WifiOff className="w-3 h-3 text-red-500" />}
          <span className={brokerConnected ? "text-emerald-500" : "text-red-500"}>
            {brokerConnected ? `${brokerUser || "Zerodha"} Connected` : "Disconnected"}
          </span>
        </div>
        <span className="text-muted-foreground">|</span>
        <span className="text-muted-foreground">Open Pos: {account?.open_positions || 0}</span>
        <span className="text-muted-foreground">|</span>
        <span className={`font-medium ${(account?.unrealized_pnl || 0) < 0 ? "text-red-500" : "text-emerald-500"}`}>
          P&L: ₹{(account?.total_pnl || 0).toFixed(2)}
        </span>
        <span className="text-muted-foreground">|</span>
        <span className="text-muted-foreground">Margin: {((account?.used_margin || 0) / ((account?.total_equity || 1)) * 100).toFixed(0)}%</span>
      </div>

      {error && (
        <div className="rounded-lg border border-red-500/20 bg-red-500/5 p-3 text-[10px] text-red-600">{error}</div>
      )}

      {/* Tabs */}
      <div className="flex gap-1 border-b overflow-x-auto">
        {tabs.map((tab) => (
          <button key={tab.id} onClick={() => setActiveTab(tab.id)}
            className={`flex items-center gap-1 px-3 py-1.5 text-[10px] font-medium border-b-2 transition-colors shrink-0 ${
              activeTab === tab.id ? "border-primary text-foreground" : "border-transparent text-muted-foreground hover:text-foreground"
            }`}>
            {tab.icon} {tab.label}
          </button>
        ))}
      </div>

      {/* Content */}
      {activeTab === "overview" && (
        <div className="space-y-4">
          <div className="grid grid-cols-4 gap-3">
            <MetricCard label="Total Equity" value={`₹${(account?.total_equity || 0).toLocaleString()}`} />
            <MetricCard label="Available Margin" value={`₹${(account?.available_margin || 0).toLocaleString()}`} color="text-emerald-500" />
            <MetricCard label="Used Margin" value={`₹${(account?.used_margin || 0).toLocaleString()}`} color="text-amber-500" />
            <MetricCard label="Exposure" value={`₹${(account?.exposure || 0).toLocaleString()}`} />
          </div>
          <div className="grid grid-cols-4 gap-3">
            <MetricCard label="Day P&L" value={`₹${(account?.day_pnl || 0).toFixed(2)}`}
              color={(account?.day_pnl || 0) >= 0 ? "text-emerald-500" : "text-red-500"} />
            <MetricCard label="Unrealized P&L" value={`₹${(account?.unrealized_pnl || 0).toFixed(2)}`}
              color={(account?.unrealized_pnl || 0) >= 0 ? "text-emerald-500" : "text-red-500"} />
            <MetricCard label="Realized P&L" value={`₹${(account?.realized_pnl || 0).toFixed(2)}`}
              color={(account?.realized_pnl || 0) >= 0 ? "text-emerald-500" : "text-red-500"} />
            <MetricCard label="Open Positions" value={String(account?.open_positions || 0)} />
          </div>
          <div className="rounded-lg border p-4">
            <h3 className="text-xs font-bold mb-3 flex items-center gap-2"><Shield className="w-3.5 h-3.5" /> Risk Status</h3>
            <div className="grid grid-cols-3 gap-3 text-[10px]">
              <div><span className="text-muted-foreground">Broker:</span> {brokerConnected ? "Connected" : "Disconnected"}</div>
              <div><span className="text-muted-foreground">Orders:</span> {orders?.orders?.length || 0} open</div>
              <div><span className="text-muted-foreground">Trades:</span> {trades?.open_count || 0} active of {trades?.total || 0}</div>
            </div>
          </div>
        </div>
      )}

      {activeTab === "positions" && (
        <div className="space-y-3">
          {(!positions?.positions || positions.positions.length === 0) ? (
            <div className="p-8 text-center text-[10px] text-muted-foreground">No open positions</div>
          ) : (
            <div className="border rounded-lg overflow-hidden">
              <table className="w-full text-[10px]">
                <thead><tr className="bg-muted/30 border-b">
                  <th className="text-left px-3 py-2">Symbol</th>
                  <th className="text-left px-3 py-2">Side</th>
                  <th className="text-right px-3 py-2">Qty</th>
                  <th className="text-right px-3 py-2">Entry</th>
                  <th className="text-right px-3 py-2">Unrealized P&L</th>
                  <th className="text-right px-3 py-2">P&L %</th>
                  <th className="text-left px-3 py-2">Status</th>
                </tr></thead>
                <tbody className="divide-y">
                  {positions.positions.map((p: any, i: number) => (
                    <tr key={i} className="hover:bg-muted/20">
                      <td className="px-3 py-1.5 font-medium">{p.symbol}</td>
                      <td className={`px-3 py-1.5 ${p.direction === "LONG" ? "text-emerald-500" : "text-red-500"}`}>{p.direction}</td>
                      <td className="px-3 py-1.5 text-right font-mono">{p.quantity}</td>
                      <td className="px-3 py-1.5 text-right font-mono">{p.entry_price?.toFixed(2) || "—"}</td>
                      <td className={`px-3 py-1.5 text-right font-mono ${(p.unrealized_pnl || 0) >= 0 ? "text-emerald-500" : "text-red-500"}`}>
                        {p.unrealized_pnl != null ? `₹${p.unrealized_pnl.toFixed(2)}` : "—"}
                      </td>
                      <td className={`px-3 py-1.5 text-right font-mono ${(p.pnl_percent || 0) >= 0 ? "text-emerald-500" : "text-red-500"}`}>
                        {p.pnl_percent != null ? `${p.pnl_percent.toFixed(2)}%` : "—"}
                      </td>
                      <td className="px-3 py-1.5">{p.status}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      )}

      {activeTab === "orders" && (
        <div className="space-y-3">
          {(!orders?.orders || orders.orders.length === 0) ? (
            <div className="p-8 text-center text-[10px] text-muted-foreground">No open orders</div>
          ) : (
            <div className="border rounded-lg overflow-hidden">
              <table className="w-full text-[10px]">
                <thead><tr className="bg-muted/30 border-b">
                  <th className="text-left px-3 py-2">Symbol</th>
                  <th className="text-left px-3 py-2">Type</th>
                  <th className="text-right px-3 py-2">Qty</th>
                  <th className="text-right px-3 py-2">Filled</th>
                  <th className="text-left px-3 py-2">Status</th>
                  <th className="text-left px-3 py-2">Broker ID</th>
                </tr></thead>
                <tbody className="divide-y">
                  {orders.orders.map((o: any, i: number) => (
                    <tr key={o.internal_id || i} className="hover:bg-muted/20">
                      <td className="px-3 py-1.5 font-medium">{o.symbol}</td>
                      <td className="px-3 py-1.5">{o.transaction_type}</td>
                      <td className="px-3 py-1.5 text-right font-mono">{o.quantity}</td>
                      <td className="px-3 py-1.5 text-right font-mono">{o.filled_quantity}</td>
                      <td className="px-3 py-1.5">
                        <span className={`px-1.5 py-0.5 rounded text-[8px] font-medium ${
                          o.status === "filled" ? "bg-emerald-500/10 text-emerald-500" :
                          o.status === "rejected" ? "bg-red-500/10 text-red-500" :
                          o.status === "submitting" ? "bg-amber-500/10 text-amber-500" :
                          "bg-muted/30 text-muted-foreground"
                        }`}>{o.status}</span>
                      </td>
                      <td className="px-3 py-1.5 font-mono text-muted-foreground text-[9px]">{o.broker_order_id || "—"}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      )}

      {activeTab === "trades" && <TradesTable trades={trades} />}
      {activeTab === "events" && <EventsTable events={events} />}

      {activeTab === "reconciliation" && (
        <div className="space-y-3">
          <div className="grid grid-cols-3 gap-3">
            <MetricCard label="Internal Trades" value={String(reconciliation?.internal_trades || 0)} />
            <MetricCard label="Internal Orders" value={String(reconciliation?.internal_orders || 0)} />
            <MetricCard label="Internal Positions" value={String(reconciliation?.internal_positions || 0)} />
          </div>
          <div className="rounded-lg border p-4">
            <h3 className="text-xs font-bold mb-2">Warnings</h3>
            {(!reconciliation?.warnings || reconciliation.warnings.length === 0) ? (
              <div className="text-[10px] text-emerald-500">No reconciliation issues detected</div>
            ) : (
              <div className="space-y-1">
                {reconciliation.warnings.map((w: any, i: number) => (
                  <div key={i} className="text-[10px] text-amber-600 bg-amber-500/5 rounded p-2">
                    <strong>{w.type}:</strong> {w.detail}
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  )
}

function MetricCard({ label, value, color }: { label: string; value: string; color?: string }) {
  return (
    <div className="rounded-lg border bg-card p-3">
      <div className="text-[9px] text-muted-foreground uppercase tracking-wider">{label}</div>
      <div className={`text-lg font-bold font-mono mt-0.5 ${color || ""}`}>{value}</div>
    </div>
  )
}

function TradesTable({ trades }: { trades: any }) {
  if (!trades?.trades || trades.trades.length === 0) {
    return <div className="p-8 text-center text-[10px] text-muted-foreground">No trades</div>
  }
  return (
    <div className="border rounded-lg overflow-hidden">
      <table className="w-full text-[10px]">
        <thead><tr className="bg-muted/30 border-b">
          <th className="text-left px-3 py-2">Symbol</th>
          <th className="text-left px-3 py-2">Direction</th>
          <th className="text-right px-3 py-2">Entry</th>
          <th className="text-right px-3 py-2">Exit</th>
          <th className="text-right px-3 py-2">Qty</th>
          <th className="text-right px-3 py-2">P&L</th>
          <th className="text-left px-3 py-2">Status</th>
          <th className="text-left px-3 py-2">Exit Reason</th>
        </tr></thead>
        <tbody className="divide-y">
          {trades.trades.map((t: any, i: number) => (
            <tr key={t.id || i} className="hover:bg-muted/20">
              <td className="px-3 py-1.5 font-medium">{t.symbol}</td>
              <td className={`px-3 py-1.5 ${t.direction === "LONG" ? "text-emerald-500" : "text-red-500"}`}>{t.direction}</td>
              <td className="px-3 py-1.5 text-right font-mono">{t.entry_price?.toFixed(2) || "—"}</td>
              <td className="px-3 py-1.5 text-right font-mono">{t.exit_price?.toFixed(2) || "—"}</td>
              <td className="px-3 py-1.5 text-right font-mono">{t.quantity}</td>
              <td className={`px-3 py-1.5 text-right font-mono ${(t.pnl || 0) >= 0 ? "text-emerald-500" : "text-red-500"}`}>
                {t.pnl != null ? `₹${t.pnl.toFixed(2)}` : "—"}
              </td>
              <td className="px-3 py-1.5">{t.status}</td>
              <td className="px-3 py-1.5 text-muted-foreground">{t.exit_reason || "—"}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}

function EventsTable({ events }: { events: any }) {
  if (!events?.events || events.events.length === 0) {
    return <div className="p-8 text-center text-[10px] text-muted-foreground">No events yet</div>
  }
  return (
    <div className="border rounded-lg overflow-y-auto max-h-[500px]">
      <div className="divide-y text-[10px]">
        {events.events.map((e: any, i: number) => (
          <div key={i} className="flex items-center gap-2 px-3 py-1.5 hover:bg-muted/20">
            <span className="font-mono text-muted-foreground w-20">
              {e.timestamp?.split("T")[1]?.slice(0, 8) || ""}
            </span>
            <span className={`px-1.5 py-0.5 rounded text-[8px] font-medium ${
              e.type?.includes("closed") || e.type?.includes("filled") ? "bg-emerald-500/10 text-emerald-500" :
              e.type?.includes("created") || e.type?.includes("opened") ? "bg-blue-500/10 text-blue-500" :
              e.type?.includes("rejected") || e.type?.includes("cancelled") ? "bg-red-500/10 text-red-500" :
              "bg-muted/30 text-muted-foreground"
            }`}>{e.type}</span>
            <span className="font-medium">{e.symbol}</span>
            {e.pnl != null && (
              <span className={`ml-auto font-mono ${e.pnl >= 0 ? "text-emerald-500" : "text-red-500"}`}>
                ₹{e.pnl.toFixed(2)}
              </span>
            )}
          </div>
        ))}
      </div>
    </div>
  )
}
