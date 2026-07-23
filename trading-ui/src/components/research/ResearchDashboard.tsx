"use client"

import { useResearchStore } from "@/store/useResearchStore"
import { useCallback } from "react"
import { researchService } from "@/services/researchService"
import { FlaskConical, BarChart3, GitCompare, Layers, TrendingUp, PieChart, FileText } from "lucide-react"
import { cn } from "@/lib/utils"

const TABS = [
  { id: "home", label: "Home", icon: <FlaskConical className="w-3.5 h-3.5" /> },
  { id: "backtest", label: "Backtest", icon: <BarChart3 className="w-3.5 h-3.5" /> },
  { id: "walkforward", label: "Walk Forward", icon: <GitCompare className="w-3.5 h-3.5" /> },
  { id: "montecarlo", label: "Monte Carlo", icon: <Layers className="w-3.5 h-3.5" /> },
  { id: "optimization", label: "Optimizer", icon: <TrendingUp className="w-3.5 h-3.5" /> },
  { id: "portfolio", label: "Portfolio", icon: <PieChart className="w-3.5 h-3.5" /> },
  { id: "history", label: "History", icon: <FileText className="w-3.5 h-3.5" /> },
]

export function ResearchDashboard() {
  const store = useResearchStore()

  const runBacktest = useCallback(async () => {
    const expId = `exp_${Date.now()}`
    const exp = { id: expId, name: `Backtest ${new Date().toLocaleDateString()}`, author: "User", strategyId: "", strategyVersion: 1, type: "backtest" as const, config: store.config as unknown as Record<string, unknown>, status: "running" as const, results: null, duration: 0, seed: 42, tags: [], notes: "", createdAt: new Date().toISOString(), updatedAt: new Date().toISOString() }
    store.addExperiment(exp)
    store.setActiveTab("history")
    try {
      const result = await researchService.runBacktest(store.config)
      store.updateExperiment(expId, { status: "completed", results: result })
    } catch { store.updateExperiment(expId, { status: "failed" }) }
  }, [store])

  return (
    <div className="space-y-3">
      <div className="flex items-center gap-2">
        <FlaskConical className="w-4 h-4 text-primary" />
        <h2 className="text-sm font-bold">Quant Research Lab</h2>
      </div>

      <div className="flex items-center gap-1 border-b">
        {TABS.map((tab) => (
          <button key={tab.id} onClick={() => store.setActiveTab(tab.id)}
            className={cn("flex items-center gap-1 px-3 py-1.5 text-[9px] font-medium transition-colors border-b-2 -mb-px", store.activeTab === tab.id ? "text-primary border-primary" : "text-muted-foreground hover:text-foreground border-transparent")}>
            {tab.icon} {tab.label}
          </button>
        ))}
      </div>

      {store.activeTab === "home" && (
        <div className="grid grid-cols-2 lg:grid-cols-3 gap-3">
          {TABS.slice(1).map((tab) => (
            <button key={tab.id} onClick={() => store.setActiveTab(tab.id)}
              className="rounded-lg border bg-card p-4 text-left hover:bg-accent transition-colors space-y-1">
              <div className="text-primary">{tab.icon}</div>
              <div className="text-[11px] font-medium">{tab.label}</div>
              <div className="text-[8px] text-muted-foreground">Run and analyze {tab.label.toLowerCase()} experiments</div>
            </button>
          ))}
        </div>
      )}

      {store.activeTab === "backtest" && (
        <div className="space-y-3 max-w-2xl">
          <div className="rounded-lg border bg-card p-3 space-y-2">
            <div className="text-[9px] font-medium text-muted-foreground uppercase tracking-wider">Backtest Configuration</div>
            <div className="grid grid-cols-2 gap-2">
              <div><label className="text-[8px] text-muted-foreground block mb-0.5">Symbol</label>
                <select value={store.config.symbol} onChange={(e) => store.setConfig({ symbol: e.target.value })}
                  className="w-full h-7 rounded border bg-muted/50 px-1.5 text-[10px] focus:outline-none">
                  {["NIFTY 50", "BANK NIFTY", "SENSEX"].map((s) => <option key={s} value={s}>{s}</option>)}
                </select></div>
              <div><label className="text-[8px] text-muted-foreground block mb-0.5">Interval</label>
                <select value={store.config.interval} onChange={(e) => store.setConfig({ interval: e.target.value })}
                  className="w-full h-7 rounded border bg-muted/50 px-1.5 text-[10px] focus:outline-none">
                  {["1m","3m","5m","15m","30m","60m","1d"].map((tf) => <option key={tf} value={tf}>{tf}</option>)}
                </select></div>
              <div><label className="text-[8px] text-muted-foreground block mb-0.5">Start Date</label>
                <input type="date" value={store.config.startDate} onChange={(e) => store.setConfig({ startDate: e.target.value })}
                  className="w-full h-7 rounded border bg-muted/50 px-1.5 text-[10px] font-mono focus:outline-none" /></div>
              <div><label className="text-[8px] text-muted-foreground block mb-0.5">End Date</label>
                <input type="date" value={store.config.endDate} onChange={(e) => store.setConfig({ endDate: e.target.value })}
                  className="w-full h-7 rounded border bg-muted/50 px-1.5 text-[10px] font-mono focus:outline-none" /></div>
              <div><label className="text-[8px] text-muted-foreground block mb-0.5">Capital</label>
                <input type="number" value={store.config.initialCapital} onChange={(e) => store.setConfig({ initialCapital: Number(e.target.value) })}
                  className="w-full h-7 rounded border bg-muted/50 px-1.5 text-[10px] font-mono focus:outline-none" /></div>
              <div><label className="text-[8px] text-muted-foreground block mb-0.5">Commission %</label>
                <input type="number" value={store.config.commission} onChange={(e) => store.setConfig({ commission: Number(e.target.value) })}
                  className="w-full h-7 rounded border bg-muted/50 px-1.5 text-[10px] font-mono focus:outline-none" step={0.01} /></div>
              <div><label className="text-[8px] text-muted-foreground block mb-0.5">Slippage %</label>
                <input type="number" value={store.config.slippage} onChange={(e) => store.setConfig({ slippage: Number(e.target.value) })}
                  className="w-full h-7 rounded border bg-muted/50 px-1.5 text-[10px] font-mono focus:outline-none" step={0.01} /></div>
              <div><label className="text-[8px] text-muted-foreground block mb-0.5">Leverage</label>
                <input type="number" value={store.config.leverage} onChange={(e) => store.setConfig({ leverage: Number(e.target.value) })}
                  className="w-full h-7 rounded border bg-muted/50 px-1.5 text-[10px] font-mono focus:outline-none" min={1} max={5} /></div>
            </div>
            <button onClick={runBacktest} className="w-full h-8 rounded bg-primary/20 text-primary text-[10px] font-bold hover:bg-primary/30 transition-colors">Run Backtest</button>
          </div>
        </div>
      )}

      {store.activeTab === "walkforward" && (
        <div className="max-w-2xl space-y-2">
          <div className="rounded-lg border bg-card p-3 space-y-2">
            <div className="text-[9px] font-medium text-muted-foreground uppercase tracking-wider">Walk Forward Settings</div>
            <div className="grid grid-cols-2 gap-2">
              <div><label className="text-[8px] text-muted-foreground block mb-0.5">Method</label>
                <select value={store.walkForwardType} onChange={(e) => store.setWalkForwardType(e.target.value as "rolling" | "anchored" | "expanding")}
                  className="w-full h-7 rounded border bg-muted/50 px-1.5 text-[10px] focus:outline-none">
                  <option value="rolling">Rolling Window</option>
                  <option value="anchored">Anchored</option>
                  <option value="expanding">Expanding</option>
                </select></div>
              <div><label className="text-[8px] text-muted-foreground block mb-0.5">Training Window (days)</label>
                <input type="number" value={store.trainWindow} onChange={(e) => store.setTrainWindow(Number(e.target.value))}
                  className="w-full h-7 rounded border bg-muted/50 px-1.5 text-[10px] font-mono focus:outline-none" /></div>
              <div><label className="text-[8px] text-muted-foreground block mb-0.5">Testing Window (days)</label>
                <input type="number" value={store.testWindow} onChange={(e) => store.setTestWindow(Number(e.target.value))}
                  className="w-full h-7 rounded border bg-muted/50 px-1.5 text-[10px] font-mono focus:outline-none" /></div>
            </div>
            <button onClick={async () => {
              const expId = `exp_${Date.now()}`; store.addExperiment({ id: expId, name: `WalkForward ${new Date().toLocaleDateString()}`, author: "User", strategyId: "", strategyVersion: 1, type: "walkforward", config: store.config as unknown as Record<string, unknown>, status: "running", results: null, duration: 0, seed: 42, tags: [], notes: "", createdAt: new Date().toISOString(), updatedAt: new Date().toISOString() }); store.setActiveTab("history")
              try { const r = await researchService.runWalkForward(store.config, store.walkForwardType, store.trainWindow, store.testWindow); store.updateExperiment(expId, { status: "completed", results: r }) } catch { store.updateExperiment(expId, { status: "failed" }) }
            }} className="w-full h-8 rounded bg-primary/20 text-primary text-[10px] font-bold hover:bg-primary/30 transition-colors">Run Walk Forward</button>
          </div>
        </div>
      )}

      {store.activeTab === "montecarlo" && (
        <div className="max-w-2xl space-y-2">
          <div className="rounded-lg border bg-card p-3 space-y-2">
            <div className="text-[9px] font-medium text-muted-foreground uppercase tracking-wider">Monte Carlo Settings</div>
            <div><label className="text-[8px] text-muted-foreground block mb-0.5">Simulations</label>
              <select value={store.mcSimulations} onChange={(e) => store.setMcSimulations(Number(e.target.value))}
                className="w-full h-7 rounded border bg-muted/50 px-1.5 text-[10px] focus:outline-none">
                <option value={100}>100</option><option value={500}>500</option><option value={1000}>1000</option><option value={5000}>5000</option><option value={10000}>10000</option>
              </select></div>
            <button onClick={async () => {
              const trades = Array.from({ length: 50 }, () => Math.random() * 2000 - 1000)
              void researchService.simulateMonteCarlo(trades, store.mcSimulations)
              const expId = `exp_${Date.now()}`; store.addExperiment({ id: expId, name: `MonteCarlo ${store.mcSimulations}`, author: "User", strategyId: "", strategyVersion: 1, type: "montecarlo", config: { simulations: store.mcSimulations } as unknown as Record<string, unknown>, status: "completed", results: null, duration: 0, seed: 42, tags: [], notes: "", createdAt: new Date().toISOString(), updatedAt: new Date().toISOString() }); store.setActiveTab("history")
            }} className="w-full h-8 rounded bg-primary/20 text-primary text-[10px] font-bold hover:bg-primary/30 transition-colors">Run {store.mcSimulations} Simulations</button>
          </div>
        </div>
      )}

      {store.activeTab === "optimization" && (
        <div className="rounded-lg border bg-card p-6 text-center text-[10px] text-muted-foreground">Configure optimization parameters and method then run.</div>
      )}

      {store.activeTab === "portfolio" && (
        <div className="rounded-lg border bg-card p-6 text-center text-[10px] text-muted-foreground">Select strategies to optimize portfolio allocation.</div>
      )}

      {store.activeTab === "history" && (
        <div className="space-y-1">
          {store.experiments.length === 0 ? (
            <div className="text-center text-[10px] text-muted-foreground py-8">No experiments yet. Run a backtest or simulation to begin.</div>
          ) : (
            [...store.experiments].reverse().map((exp) => (
              <div key={exp.id} className="flex items-center gap-2 rounded-lg border bg-card p-2 text-[10px]">
                <div className={cn("w-2 h-2 rounded-full", exp.status === "completed" ? "bg-emerald-500" : exp.status === "failed" ? "bg-red-500" : "bg-amber-500")} />
                <span className="font-medium flex-1">{exp.name}</span>
                <span className="text-muted-foreground">{exp.type}</span>
                <span className={cn("px-1 py-0.5 rounded text-[8px]", exp.status === "completed" ? "bg-emerald-500/10 text-emerald-500" : "bg-amber-500/10 text-amber-500")}>{exp.status}</span>
                <span className="text-muted-foreground">{new Date(exp.createdAt).toLocaleDateString()}</span>
              </div>
            ))
          )}
        </div>
      )}
    </div>
  )
}
