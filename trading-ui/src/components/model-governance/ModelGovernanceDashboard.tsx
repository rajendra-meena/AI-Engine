"use client"

import { useState, useEffect, useCallback } from "react"
import { Database, GitBranch, BarChart3, Shield, History, RefreshCw, CircleCheck, CircleX } from "lucide-react"
import { modelRegistryService, type ModelRegistryEntry } from "@/services/modelRegistryService"

type TabId = "registry" | "champion" | "challenger" | "comparison" | "validation" | "promotion" | "rollback" | "lineage"

export function ModelGovernanceDashboard() {
  const [activeTab, setActiveTab] = useState<TabId>("registry")
  const [models, setModels] = useState<ModelRegistryEntry[]>([])
  const [champion, setChampion] = useState<ModelRegistryEntry | null>(null)
  const [challenger, setChallenger] = useState<ModelRegistryEntry | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const fetchAll = useCallback(async () => {
    setError(null)
    try {
      const [m, ch, cl] = await Promise.all([
        modelRegistryService.listModels().catch(() => ({ models: [], total: 0 })),
        modelRegistryService.getChampion().catch(() => null),
        modelRegistryService.getChallenger().catch(() => null),
      ])
      setModels(m.models)
      if (ch) setChampion(ch)
      if (cl) setChallenger(cl)
    } catch { setError("Failed to load model data") }
    setLoading(false)
  }, [])

  useEffect(() => {
    const t = setTimeout(() => fetchAll(), 0)
    const interval = setInterval(fetchAll, 60000)
    return () => { clearTimeout(t); clearInterval(interval) }
  }, [fetchAll])

  const tabs = [
    { id: "registry" as TabId, label: "Registry", icon: <Database className="w-3.5 h-3.5" /> },
    { id: "champion" as TabId, label: "Champion", icon: <Shield className="w-3.5 h-3.5" /> },
    { id: "challenger" as TabId, label: "Challenger", icon: <GitBranch className="w-3.5 h-3.5" /> },
    { id: "comparison" as TabId, label: "Comparison", icon: <BarChart3 className="w-3.5 h-3.5" /> },
    { id: "validation" as TabId, label: "Validation", icon: <BarChart3 className="w-3.5 h-3.5" /> },
    { id: "promotion" as TabId, label: "Promotion", icon: <CircleCheck className="w-3.5 h-3.5" /> },
    { id: "rollback" as TabId, label: "Rollback", icon: <History className="w-3.5 h-3.5" /> },
    { id: "lineage" as TabId, label: "Lineage", icon: <GitBranch className="w-3.5 h-3.5" /> },
  ]

  return (
    <div className="space-y-4">
      <div className="flex items-center gap-2">
        <Database className="w-5 h-5 text-primary" />
        <h1 className="text-lg font-bold">Model Governance Center</h1>
        {champion && <span className="px-1.5 py-0.5 rounded text-[8px] font-medium bg-emerald-500/10 text-emerald-500 border border-emerald-500/20">Champion: {champion.name} v{champion.version}</span>}
        {challenger && <span className="px-1.5 py-0.5 rounded text-[8px] font-medium bg-blue-500/10 text-blue-500 border border-blue-500/20">Challenger: {challenger.name} v{challenger.version}</span>}
        <button onClick={fetchAll} className="ml-auto p-1 rounded text-muted-foreground hover:bg-accent">
          <RefreshCw className={`w-3.5 h-3.5 ${loading ? "animate-spin" : ""}`} />
        </button>
      </div>

      {error && <div className="rounded border border-red-500/20 bg-red-500/5 p-2 text-[10px] text-red-600">{error}</div>}

      <div className="flex gap-1 border-b overflow-x-auto">
        {tabs.map(tab => (
          <button key={tab.id} onClick={() => setActiveTab(tab.id)}
            className={`flex items-center gap-1 px-3 py-1.5 text-[10px] font-medium border-b-2 shrink-0 ${activeTab === tab.id ? "border-primary text-foreground" : "border-transparent text-muted-foreground"}`}>
            {tab.icon} {tab.label}
          </button>
        ))}
      </div>

      <div className="min-h-[400px]">
        {activeTab === "registry" && <RegistryTab models={models} />}
        {activeTab === "champion" && <ModelDetailTab model={champion} title="Champion Model" />}
        {activeTab === "challenger" && <ModelDetailTab model={challenger} title="Challenger Model" />}
        {activeTab === "comparison" && <ComparisonTab />}
        {activeTab === "validation" && <ValidationTab />}
        {activeTab === "promotion" && <PromotionTab />}
        {activeTab === "rollback" && <RollbackTab />}
        {activeTab === "lineage" && <LineageTab />}
      </div>
    </div>
  )
}

function RegistryTab({ models }: { models: ModelRegistryEntry[] }) {
  return (
    <div className="space-y-2">
      {models.length === 0 ? (
        <div className="p-8 text-center text-[10px] text-muted-foreground">No models registered</div>
      ) : (
        <div className="border rounded-lg overflow-hidden">
          <table className="w-full text-[10px]">
            <thead><tr className="bg-muted/30 border-b">
              <th className="text-left px-3 py-2">Name</th>
              <th className="text-left px-3 py-2">Version</th>
              <th className="text-left px-3 py-2">Status</th>
              <th className="text-left px-3 py-2">Type</th>
              <th className="text-left px-3 py-2">Algorithm</th>
              <th className="text-left px-3 py-2">Created</th>
            </tr></thead>
            <tbody className="divide-y">
              {models.map(m => (
                <tr key={m.id} className="hover:bg-muted/20">
                  <td className="px-3 py-1.5 font-medium">{m.name}</td>
                  <td className="px-3 py-1.5 font-mono">v{m.version}</td>
                  <td className="px-3 py-1.5">
                    <StatusBadge status={m.status} />
                  </td>
                  <td className="px-3 py-1.5 text-muted-foreground">{m.model_type || "—"}</td>
                  <td className="px-3 py-1.5 text-muted-foreground">{m.algorithm || "—"}</td>
                  <td className="px-3 py-1.5 text-muted-foreground">{m.created_at?.split("T")[0]}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  )
}

function ModelDetailTab({ model, title }: { model: ModelRegistryEntry | null; title: string }) {
  if (!model) return <div className="p-8 text-center text-[10px] text-muted-foreground">No {title.toLowerCase()} set</div>

  return (
    <div className="space-y-4">
      <div className="grid grid-cols-3 gap-3">
        <MetricCard label="Name" value={model.name} />
        <MetricCard label="Version" value={`v${model.version}`} />
        <MetricCard label="Status" value={model.status} color={model.status === "champion" ? "text-emerald-500" : model.status === "challenger" ? "text-blue-500" : "text-muted-foreground"} />
      </div>
      <div className="rounded-lg border bg-card p-3 space-y-2 text-[10px]">
        <div className="flex justify-between"><span className="text-muted-foreground">Model Type</span><span className="font-medium">{model.model_type || "—"}</span></div>
        <div className="flex justify-between"><span className="text-muted-foreground">Algorithm</span><span className="font-medium">{model.algorithm || "—"}</span></div>
        <div className="flex justify-between"><span className="text-muted-foreground">Created</span><span className="font-medium">{model.created_at ? new Date(model.created_at).toLocaleString() : "—"}</span></div>
        <div className="flex justify-between"><span className="text-muted-foreground">Updated</span><span className="font-medium">{model.updated_at ? new Date(model.updated_at).toLocaleString() : "—"}</span></div>
        {model.parent_model_id && <div className="flex justify-between"><span className="text-muted-foreground">Parent Model</span><span className="font-medium font-mono">{model.parent_model_id.slice(-10)}</span></div>}
      </div>
    </div>
  )
}

function ComparisonTab() { return <div className="p-8 text-center text-[10px] text-muted-foreground">Champion vs Challenger comparison data</div> }
function ValidationTab() { return <div className="p-8 text-center text-[10px] text-muted-foreground">Walk-forward validation results</div> }
function PromotionTab() { return <div className="p-8 text-center text-[10px] text-muted-foreground">Promotion review recommendations</div> }
function RollbackTab() { return <div className="p-8 text-center text-[10px] text-muted-foreground">Rollback history and audit trail</div> }
function LineageTab() { return <div className="p-8 text-center text-[10px] text-muted-foreground">Model lineage graph</div> }

function StatusBadge({ status }: { status: string }) {
  const colors: Record<string, string> = {
    champion: "bg-emerald-500/10 text-emerald-500",
    challenger: "bg-blue-500/10 text-blue-500",
    draft: "bg-gray-500/10 text-gray-400",
    validation: "bg-amber-500/10 text-amber-500",
    candidate: "bg-violet-500/10 text-violet-500",
    archived: "bg-muted/30 text-muted-foreground",
    rolled_back: "bg-red-500/10 text-red-500",
  }
  return <span className={`px-1.5 py-0.5 rounded text-[8px] font-medium ${colors[status] || "bg-muted/30 text-muted-foreground"}`}>{status}</span>
}

function MetricCard({ label, value, color }: { label: string; value: string; color?: string }) {
  return <div className="rounded-lg border bg-card p-3 text-center">
    <div className="text-[9px] text-muted-foreground uppercase">{label}</div>
    <div className={`text-lg font-bold font-mono mt-0.5 ${color || ""}`}>{value}</div>
  </div>
}
