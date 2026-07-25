"use client"

import { useState, useEffect, useCallback } from "react"
import { Activity, BarChart3, Target, DollarSign, RefreshCw, Play, Trash2 } from "lucide-react"
import { backtestService } from "@/services/backtestService"

export function BacktestDashboard() {
  const [backtests, setBacktests] = useState<any[]>([])
  const [loading, setLoading] = useState(true)
  const [selectedId, setSelectedId] = useState<string | null>(null)
  const [result, setResult] = useState<any>(null)
  const [trades, setTrades] = useState<any[]>([])
  const [newBt, setNewBt] = useState({
    symbol: "NIFTY 50", timeframe: "15m", start_date: "", end_date: "",
    initial_capital: 100000, name: "",
  })

  const fetchHistory = useCallback(async () => {
    try {
      const h = await backtestService.getHistory()
      setBacktests(h.backtests || [])
    } catch { /* ignore */ }
    setLoading(false)
  }, [])

  useEffect(() => { fetchHistory() }, [fetchHistory])

  const handleCreate = async () => {
    const result = await backtestService.create(newBt)
    if (result.success) {
      await backtestService.start(result.backtest_id)
      await fetchHistory()
      setSelectedId(result.backtest_id)
    }
  }

  const handleSelect = async (id: string) => {
    setSelectedId(id)
    try {
      const [r, t] = await Promise.all([
        backtestService.getResult(id),
        backtestService.getTrades(id),
      ])
      setResult(r)
      setTrades(t.trades || [])
    } catch { /* ignore */ }
  }

  const handleDelete = async (id: string) => {
    await backtestService.deleteBacktest(id)
    if (selectedId === id) { setSelectedId(null); setResult(null); setTrades([]) }
    await fetchHistory()
  }

  const m = result?.metrics || {}

  return (
    <div className="space-y-4">
      <div className="flex items-center gap-2">
        <Target className="w-5 h-5 text-primary" />
        <h1 className="text-lg font-bold">Backtesting Engine</h1>
        <button onClick={fetchHistory} className="ml-auto p-1 rounded text-muted-foreground hover:bg-accent">
          <RefreshCw className={`w-3.5 h-3.5 ${loading ? "animate-spin" : ""}`} />
        </button>
      </div>

      <div className="grid grid-cols-2 gap-4">
        {/* New Backtest */}
        <div className="rounded-lg border bg-card p-4 space-y-3">
          <h3 className="text-xs font-bold">New Backtest</h3>
          <div className="grid grid-cols-2 gap-2 text-[10px]">
            <div>
              <label className="text-muted-foreground block mb-0.5">Symbol</label>
              <select value={newBt.symbol} onChange={e => setNewBt({ ...newBt, symbol: e.target.value })}
                className="w-full h-7 rounded border bg-muted/30 px-2 text-[10px] font-medium">
                <option>NIFTY 50</option><option>BANKNIFTY</option><option>SENSEX</option>
              </select>
            </div>
            <div>
              <label className="text-muted-foreground block mb-0.5">Timeframe</label>
              <select value={newBt.timeframe} onChange={e => setNewBt({ ...newBt, timeframe: e.target.value })}
                className="w-full h-7 rounded border bg-muted/30 px-2 text-[10px] font-medium">
                {["1m","2m","3m","5m","10m","15m","30m","60m"].map(t => <option key={t}>{t}</option>)}
              </select>
            </div>
            <div>
              <label className="text-muted-foreground block mb-0.5">Start Date</label>
              <input type="date" value={newBt.start_date} onChange={e => setNewBt({ ...newBt, start_date: e.target.value })}
                className="w-full h-7 rounded border bg-muted/30 px-2 text-[10px]" />
            </div>
            <div>
              <label className="text-muted-foreground block mb-0.5">End Date</label>
              <input type="date" value={newBt.end_date} onChange={e => setNewBt({ ...newBt, end_date: e.target.value })}
                className="w-full h-7 rounded border bg-muted/30 px-2 text-[10px]" />
            </div>
            <div>
              <label className="text-muted-foreground block mb-0.5">Initial Capital</label>
              <input type="number" value={newBt.initial_capital} onChange={e => setNewBt({ ...newBt, initial_capital: Number(e.target.value) })}
                className="w-full h-7 rounded border bg-muted/30 px-2 text-[10px] font-mono" />
            </div>
            <div>
              <label className="text-muted-foreground block mb-0.5">Name (optional)</label>
              <input type="text" value={newBt.name} onChange={e => setNewBt({ ...newBt, name: e.target.value })}
                className="w-full h-7 rounded border bg-muted/30 px-2 text-[10px]" placeholder="My Backtest" />
            </div>
          </div>
          <button onClick={handleCreate} className="flex items-center gap-1 px-3 py-1.5 rounded text-[10px] font-medium bg-primary text-primary-foreground hover:bg-primary/90">
            <Play className="w-3 h-3" /> Create & Start
          </button>
        </div>

        {/* Results */}
        <div className="rounded-lg border bg-card p-4 space-y-3">
          <h3 className="text-xs font-bold">Results</h3>
          {selectedId && result ? (
            <div className="space-y-2">
              <div className="grid grid-cols-2 gap-2">
                <Metric label="Net P&L" value={`$${(m.net_pnl || 0).toFixed(2)}`} color={(m.net_pnl || 0) >= 0 ? "text-emerald-500" : "text-red-500"} />
                <Metric label="Win Rate" value={`${m.win_rate || 0}%`} color={(m.win_rate || 0) >= 50 ? "text-emerald-500" : "text-red-500"} />
                <Metric label="Profit Factor" value={String(m.profit_factor || 0)} />
                <Metric label="Max DD" value={`${m.max_drawdown_pct || 0}%`} color="text-red-500" />
                <Metric label="Total Trades" value={String(m.total_trades || 0)} />
                <Metric label="Avg Trade" value={`$${(m.avg_trade || 0).toFixed(2)}`} />
              </div>
              <div className="text-[9px] text-muted-foreground">Sample: {m.sample_level?.replace(/_/g, " ")}</div>
              {trades.length > 0 && (
                <div className="border-t pt-2 mt-2">
                  <div className="text-[9px] text-muted-foreground uppercase mb-1">Recent Trades</div>
                  <div className="max-h-32 overflow-y-auto space-y-1">
                    {trades.slice(-10).reverse().map((t: any, i: number) => (
                      <div key={i} className="flex gap-2 text-[9px]">
                        <span className="font-mono w-16">{t.exit_time?.split("T")[0] || ""}</span>
                        <span className={t.direction === "LONG" ? "text-emerald-500" : "text-red-500"}>{t.direction}</span>
                        <span className={(t.net_pnl || 0) >= 0 ? "text-emerald-500" : "text-red-500"}>${(t.net_pnl || 0).toFixed(2)}</span>
                        <span className="text-muted-foreground">{t.exit_reason}</span>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          ) : (
            <div className="p-4 text-center text-[10px] text-muted-foreground">Select a backtest to view results</div>
          )}
        </div>
      </div>

      {/* History */}
      <div className="rounded-lg border">
        <div className="px-3 py-2 border-b bg-muted/20 text-[10px] font-medium uppercase text-muted-foreground">Backtest History</div>
        {backtests.length === 0 ? (
          <div className="p-6 text-center text-[10px] text-muted-foreground">No backtests yet</div>
        ) : (
          <div className="divide-y text-[10px]">
            {backtests.map((bt: any) => (
              <div key={bt.run_id} className={`flex items-center gap-2 px-3 py-2 hover:bg-muted/20 cursor-pointer ${selectedId === bt.run_id ? "bg-muted/30" : ""}`}
                onClick={() => handleSelect(bt.run_id)}>
                <span className={`px-1.5 py-0.5 rounded text-[8px] font-medium ${
                  bt.status === "completed" ? "bg-emerald-500/10 text-emerald-500" :
                  bt.status === "running" ? "bg-blue-500/10 text-blue-500" :
                  bt.status === "failed" ? "bg-red-500/10 text-red-500" :
                  "bg-muted/30 text-muted-foreground"
                }`}>{bt.status}</span>
                <span className="font-medium">{bt.config?.symbol || bt.run_id?.slice(-8)}</span>
                <span className="text-muted-foreground">{bt.config?.timeframe}</span>
                <span className="text-muted-foreground ml-auto">{bt.created_at?.split("T")[0]}</span>
                <button onClick={e => { e.stopPropagation(); handleDelete(bt.run_id) }}
                  className="p-1 rounded text-muted-foreground hover:text-red-500 hover:bg-accent">
                  <Trash2 className="w-3 h-3" />
                </button>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  )
}

function Metric({ label, value, color }: { label: string; value: string; color?: string }) {
  return <div className="rounded border bg-muted/10 p-2">
    <div className="text-[8px] text-muted-foreground uppercase">{label}</div>
    <div className={`text-xs font-bold font-mono ${color || ""}`}>{value}</div>
  </div>
}
