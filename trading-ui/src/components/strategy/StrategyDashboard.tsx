"use client"

import { useCallback } from "react"
import { useStrategyStore, type Strategy, type StrategyTemplate } from "@/store/useStrategyStore"
import { StrategyBuilder } from "./StrategyBuilder"
import { strategyService } from "@/services/strategyService"
import { Plus, Layers, BarChart3, Settings, Play, History, GitBranch, LayoutGrid } from "lucide-react"
import { cn } from "@/lib/utils"

const TABS = [
  { id: "builder", label: "Builder", icon: <Settings className="w-3.5 h-3.5" /> },
  { id: "strategies", label: "Strategies", icon: <Layers className="w-3.5 h-3.5" /> },
  { id: "templates", label: "Templates", icon: <LayoutGrid className="w-3.5 h-3.5" /> },
  { id: "optimizer", label: "Optimizer", icon: <BarChart3 className="w-3.5 h-3.5" /> },
  { id: "deploy", label: "Deploy", icon: <Play className="w-3.5 h-3.5" /> },
  { id: "history", label: "History", icon: <History className="w-3.5 h-3.5" /> },
]

export function StrategyDashboard() {
  const store = useStrategyStore()


  const createNew = useCallback(() => {
    const s: Strategy = {
      id: `str_${Date.now()}`,
      name: "New Strategy",
      description: "",
      template: null, version: 1, status: "draft",
      entryRules: [], exitRules: [], riskRules: [], params: [],
      tags: [], notes: "", createdAt: new Date().toISOString(),
      updatedAt: new Date().toISOString(), versions: [],
    }
    store.addStrategy(s)
    store.setCurrentStrategy(s)
    store.setActiveTab("builder")
  }, [store])

  const loadTemplate = useCallback((tpl: StrategyTemplate) => {
    const s: Strategy = {
      id: `str_${Date.now()}`,
      name: tpl.name,
      description: tpl.description,
      template: tpl.id, version: 1, status: "draft",
      entryRules: tpl.entryRules,
      exitRules: tpl.exitRules,
      riskRules: tpl.riskRules,
      params: tpl.params,
      tags: [tpl.category],
      notes: "", createdAt: new Date().toISOString(),
      updatedAt: new Date().toISOString(), versions: [],
    }
    store.addStrategy(s)
    store.setCurrentStrategy(s)
    store.setActiveTab("builder")
  }, [store])

  const handleSave = useCallback(async () => {
    if (!store.currentStrategy) return
    const version = {
      ...store.currentStrategy,
      version: (store.currentStrategy.version || 0) + 1,
      updatedAt: new Date().toISOString(),
    }
    store.updateStrategy(store.currentStrategy.id, version)
  }, [store])

  const handleExplain = useCallback(async () => {
    if (!store.currentStrategy) return
    const result = await strategyService.explain({
      entryRules: store.currentStrategy.entryRules,
      exitRules: store.currentStrategy.exitRules,
    })
    if (result.analysis) {
      store.updateStrategy(store.currentStrategy.id, {
        notes: result.analysis + "\n\nSuggestions: " + result.suggestions.join(", "),
      })
    }
  }, [store])

  const handleValidate = useCallback(async () => {
    if (!store.currentStrategy) return
    const result = await strategyService.validate({
      entryRules: store.currentStrategy.entryRules,
      exitRules: store.currentStrategy.exitRules,
    })
    if (result.errors.length > 0) {
      store.updateStrategy(store.currentStrategy.id, {
        notes: "Validation errors:\n" + result.errors.join("\n"),
      })
    } else {
      store.updateStrategy(store.currentStrategy.id, {
        notes: "✓ Strategy validated successfully",
      })
    }
  }, [store])

  return (
    <div className="space-y-3">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <GitBranch className="w-4 h-4 text-primary" />
          <h2 className="text-sm font-bold">Strategy Studio</h2>
        </div>
        <button onClick={createNew} className="flex items-center gap-1 rounded-md bg-primary/20 text-primary px-3 py-1.5 text-[10px] font-medium hover:bg-primary/30 transition-colors">
          <Plus className="w-3 h-3" /> New Strategy
        </button>
      </div>

      {/* Tabs */}
      <div className="flex items-center gap-1 border-b">
        {TABS.map((tab) => (
          <button
            key={tab.id}
            onClick={() => store.setActiveTab(tab.id)}
            className={cn("flex items-center gap-1 px-3 py-1.5 text-[9px] font-medium transition-colors border-b-2 -mb-px", store.activeTab === tab.id ? "text-primary border-primary" : "text-muted-foreground hover:text-foreground border-transparent")}
          >
            {tab.icon} {tab.label}
          </button>
        ))}
      </div>

      {/* Content */}
      {store.activeTab === "builder" && store.currentStrategy && (
        <StrategyBuilder
          strategy={store.currentStrategy}
          onUpdate={(update) => store.updateStrategy(store.currentStrategy!.id, update)}
          onSave={handleSave}
          onValidate={handleValidate}
          onExplain={handleExplain}
        />
      )}

      {store.activeTab === "builder" && !store.currentStrategy && (
        <div className="flex flex-col items-center justify-center h-48 gap-2">
          <GitBranch className="w-8 h-8 text-muted-foreground/30" />
          <div className="text-[10px] text-muted-foreground">Select or create a strategy to start building</div>
        </div>
      )}

      {store.activeTab === "strategies" && (
        <div className="space-y-1">
          {store.strategies.length === 0 ? (
            <div className="text-center text-[10px] text-muted-foreground py-8">No strategies yet. Create one from templates or start fresh.</div>
          ) : (
            store.strategies.map((s) => (
              <div key={s.id} onClick={() => { store.setCurrentStrategy(s); store.setActiveTab("builder") }}
                className="flex items-center gap-2 rounded-lg border bg-card p-2 cursor-pointer hover:bg-accent transition-colors">
                <div className={cn("w-2 h-2 rounded-full", s.status === "active" ? "bg-emerald-500" : s.status === "paused" ? "bg-amber-500" : "bg-muted-foreground/30")} />
                <span className="text-[10px] font-medium flex-1">{s.name}</span>
                <span className="text-[8px] text-muted-foreground">v{s.version}</span>
                <span className={cn("text-[8px] px-1 py-0.5 rounded", s.status === "active" ? "bg-emerald-500/10 text-emerald-500" : "bg-muted/30 text-muted-foreground")}>{s.status}</span>
                <span className="text-[8px] text-muted-foreground">{s.entryRules.length} entry / {s.exitRules.length} exit</span>
              </div>
            ))
          )}
        </div>
      )}

      {store.activeTab === "templates" && (
        <div className="grid grid-cols-2 lg:grid-cols-3 gap-2">
          {store.templates.map((tpl) => (
            <div key={tpl.id} onClick={() => loadTemplate(tpl)}
              className="rounded-lg border bg-card p-3 cursor-pointer hover:bg-accent transition-colors space-y-1">
              <div className="text-[10px] font-medium">{tpl.name}</div>
              <div className="text-[8px] text-muted-foreground">{tpl.description}</div>
              <div className="flex items-center gap-1 text-[8px] text-muted-foreground">
                <span className="rounded bg-muted/30 px-1 py-0.5">{tpl.category}</span>
                <span>{tpl.entryRules.length} entry rules</span>
              </div>
            </div>
          ))}
        </div>
      )}

      {store.activeTab === "optimizer" && (
        <div className="rounded-lg border bg-card p-6 text-center text-[10px] text-muted-foreground">
          Select a strategy and configure optimization parameters to begin.
        </div>
      )}

      {store.activeTab === "deploy" && (
        <div className="rounded-lg border bg-card p-6 text-center text-[10px] text-muted-foreground">
          Deploy strategies to paper trading or live trading from here.
        </div>
      )}

      {store.activeTab === "history" && (
        <div className="rounded-lg border bg-card p-6 text-center text-[10px] text-muted-foreground">
          Version history and change log will appear here.
        </div>
      )}
    </div>
  )
}
