"use client"

import { useState, useMemo } from "react"
import { useQuery } from "@tanstack/react-query"
import { mlService } from "@/services/mlService"
import { BrainCircuit, Cpu, BarChart3, Layers, Database, Target, Activity } from "lucide-react"
import { cn } from "@/lib/utils"

const TABS = [
  { id: "overview", label: "Overview", icon: <BrainCircuit className="w-3.5 h-3.5" /> },
  { id: "models", label: "Models", icon: <Cpu className="w-3.5 h-3.5" /> },
  { id: "training", label: "Training", icon: <BarChart3 className="w-3.5 h-3.5" /> },
  { id: "features", label: "Features", icon: <Layers className="w-3.5 h-3.5" /> },
  { id: "evaluation", label: "Evaluation", icon: <Target className="w-3.5 h-3.5" /> },
  { id: "registry", label: "Registry", icon: <Database className="w-3.5 h-3.5" /> },
  { id: "drift", label: "Drift", icon: <Activity className="w-3.5 h-3.5" /> },
]

export function MLDashboard() {
  const [activeTab, setActiveTab] = useState("overview")

  const { data: models } = useQuery({ queryKey: ["ml-models"], queryFn: () => mlService.getModels(), refetchInterval: 60_000, staleTime: 30_000 })
  const { data: registry } = useQuery({ queryKey: ["ml-registry"], queryFn: () => mlService.getRegistry(), refetchInterval: 60_000, staleTime: 30_000 })
  const { data: drift } = useQuery({ queryKey: ["ml-drift"], queryFn: () => mlService.detectDrift(), refetchInterval: 60_000, staleTime: 30_000 })
  const { data: features } = useQuery({ queryKey: ["ml-features"], queryFn: () => mlService.getFeatures(), staleTime: 300_000 })

  const overviewContent = useMemo(() => (
    <div className="space-y-3">
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-2">
        <div className="rounded-lg border bg-card p-3">
          <div className="text-[8px] text-muted-foreground uppercase">Total Models</div>
          <div className="text-2xl font-bold font-mono mt-1">{models?.length ?? 0}</div>
        </div>
        <div className="rounded-lg border bg-card p-3">
          <div className="text-[8px] text-muted-foreground uppercase">Features</div>
          <div className="text-2xl font-bold font-mono mt-1">{features?.length ?? 0}</div>
        </div>
        <div className="rounded-lg border bg-card p-3">
          <div className="text-[8px] text-muted-foreground uppercase">Champion F1</div>
          <div className="text-2xl font-bold font-mono mt-1">{(registry?.champion?.metrics?.f1 ?? 0) * 100 > 0 ? ((registry?.champion?.metrics?.f1 ?? 0) * 100).toFixed(1) : "—"}</div>
        </div>
        <div className="rounded-lg border bg-card p-3">
          <div className="text-[8px] text-muted-foreground uppercase">Drift Score</div>
          <div className={cn("text-2xl font-bold font-mono mt-1", (drift?.driftScore ?? 0) > 0.5 ? "text-red-500" : "text-emerald-500")}>{drift ? (drift.driftScore * 100).toFixed(0) : "—"}</div>
        </div>
      </div>

      {registry?.champion && (
        <div className="rounded-lg border bg-card p-3">
          <div className="text-[9px] font-medium text-muted-foreground uppercase tracking-wider mb-2">Champion Model</div>
          <div className="grid grid-cols-2 sm:grid-cols-5 gap-2">
            <div><div className="text-[8px] text-muted-foreground">Name</div><div className="text-[10px] font-medium">{registry.champion.name}</div></div>
            <div><div className="text-[8px] text-muted-foreground">Type</div><div className="text-[10px]">{registry.champion.modelType}</div></div>
            <div><div className="text-[8px] text-muted-foreground">Accuracy</div><div className="text-[10px] font-mono">{((registry.champion.metrics?.accuracy ?? 0) * 100).toFixed(1)}%</div></div>
            <div><div className="text-[8px] text-muted-foreground">F1</div><div className="text-[10px] font-mono">{((registry.champion.metrics?.f1 ?? 0) * 100).toFixed(1)}%</div></div>
            <div><div className="text-[8px] text-muted-foreground">ROC AUC</div><div className="text-[10px] font-mono">{((registry.champion.metrics?.roc_auc ?? 0) * 100).toFixed(1)}%</div></div>
          </div>
        </div>
      )}

      {drift && (
        <div className={cn("rounded-lg border p-3", drift.driftDetected ? "border-red-500/30 bg-red-500/5" : "border-emerald-500/30 bg-emerald-500/5")}>
          <div className="flex items-center gap-2">
            <Activity className="w-4 h-4" />
            <span className="text-[10px] font-medium">{drift.driftDetected ? "Concept Drift Detected" : "No Drift Detected"}</span>
            {drift.recommendRetrain && <span className="rounded bg-amber-500/10 text-amber-500 px-1 py-0.5 text-[8px]">Retrain Recommended</span>}
          </div>
        </div>
      )}
    </div>
  ), [models, registry, drift, features])

  const modelsContent = useMemo(() => (
    <div className="space-y-1">
      {(!models || models.length === 0) ? (
        <div className="rounded-lg border bg-card p-6 text-center text-[10px] text-muted-foreground">No trained models yet</div>
      ) : (
        models.map((m) => (
          <div key={m.id} className="rounded-lg border bg-card p-2 flex items-center gap-2 text-[10px]">
            <span className={cn("w-2 h-2 rounded-full", m.status === "champion" ? "bg-emerald-500" : m.status === "challenger" ? "bg-amber-500" : "bg-muted-foreground/30")} />
            <span className="font-medium flex-1">{m.name}</span>
            <span className="text-muted-foreground">{m.modelType}</span>
            <span className="text-muted-foreground">v{m.version}</span>
            <span className="font-mono">F1: {((m.metrics?.f1 ?? 0) * 100).toFixed(1)}%</span>
            <span className="text-[8px] text-muted-foreground">{m.createdAt ? new Date(m.createdAt).toLocaleDateString() : ""}</span>
          </div>
        ))
      )}
    </div>
  ), [models])

  const featuresContent = useMemo(() => (
    <div className="rounded-lg border bg-card p-3">
      <div className="text-[9px] font-medium text-muted-foreground uppercase tracking-wider mb-2">Available Features ({features?.length ?? 0})</div>
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-1">
        {(features ?? []).map((f) => (
          <div key={f.name} className="rounded bg-muted/20 px-2 py-1 text-[9px] font-mono">{f.name}</div>
        ))}
      </div>
    </div>
  ), [features])

  return (
    <div className="space-y-3">
      <div className="flex items-center gap-2">
        <Cpu className="w-4 h-4 text-primary" />
        <h2 className="text-sm font-bold">Machine Learning Engine</h2>
      </div>

      <div className="flex items-center gap-1 border-b overflow-x-auto">
        {TABS.map((tab) => (
          <button key={tab.id} onClick={() => setActiveTab(tab.id)}
            className={cn("flex items-center gap-1 px-3 py-1.5 text-[9px] font-medium transition-colors border-b-2 -mb-px whitespace-nowrap", activeTab === tab.id ? "text-primary border-primary" : "text-muted-foreground hover:text-foreground border-transparent")}>
            {tab.icon} {tab.label}
          </button>
        ))}
      </div>

      {activeTab === "overview" && overviewContent}
      {activeTab === "models" && modelsContent}
      {activeTab === "features" && featuresContent}
      {(activeTab !== "overview" && activeTab !== "models" && activeTab !== "features") && (
        <div className="rounded-lg border bg-card p-6 text-center text-[10px] text-muted-foreground">
          {TABS.find((t) => t.id === activeTab)?.label} ready — train a model to see results.
        </div>
      )}
    </div>
  )
}
