"use client"

import { useState, useEffect, useCallback } from "react"
import { Shield, BarChart3, Activity, Lock, RefreshCw, FileText, Server, CheckCircle } from "lucide-react"

type TabId = "certification" | "readiness" | "benchmarks" | "security" | "recovery" | "release"

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"

export function ProductionReadinessDashboard() {
  const [activeTab, setActiveTab] = useState<TabId>("certification")
  const [report, setReport] = useState<any>(null)
  const [readiness, setReadiness] = useState<any>(null)
  const [benchmarks, setBenchmarks] = useState<any>(null)
  const [security, setSecurity] = useState<any>(null)
  const [recovery, setRecovery] = useState<any>(null)
  const [release, setRelease] = useState<any>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const fetchAll = useCallback(async () => {
    setError(null)
    try {
      const [r, rd, b, s, rec, rel] = await Promise.all([
        fetch(`${API_BASE}/api/certification/report`).then(r => r.json()).catch(() => null),
        fetch(`${API_BASE}/api/certification/readiness`).then(r => r.json()).catch(() => null),
        fetch(`${API_BASE}/api/certification/benchmarks`).then(r => r.json()).catch(() => null),
        fetch(`${API_BASE}/api/certification/security`).then(r => r.json()).catch(() => null),
        fetch(`${API_BASE}/api/certification/recovery`).then(r => r.json()).catch(() => null),
        fetch(`${API_BASE}/api/certification/release`).then(r => r.json()).catch(() => null),
      ])
      if (r) setReport(r)
      if (rd) setReadiness(rd)
      if (b) setBenchmarks(b)
      if (s) setSecurity(s)
      if (rec) setRecovery(rec)
      if (rel) setRelease(rel)
    } catch { setError("Failed to load certification data") }
    setLoading(false)
  }, [])

  useEffect(() => {
    const t = setTimeout(() => fetchAll(), 0)
    return () => clearTimeout(t)
  }, [fetchAll])

  const tabs = [
    { id: "certification" as TabId, label: "Certification", icon: <Shield className="w-3.5 h-3.5" /> },
    { id: "readiness" as TabId, label: "Readiness", icon: <CheckCircle className="w-3.5 h-3.5" /> },
    { id: "benchmarks" as TabId, label: "Benchmarks", icon: <BarChart3 className="w-3.5 h-3.5" /> },
    { id: "security" as TabId, label: "Security", icon: <Lock className="w-3.5 h-3.5" /> },
    { id: "recovery" as TabId, label: "Recovery", icon: <Activity className="w-3.5 h-3.5" /> },
    { id: "release" as TabId, label: "Release", icon: <FileText className="w-3.5 h-3.5" /> },
  ]

  return (
    <div className="space-y-4">
      <div className="flex items-center gap-2">
        <Shield className="w-5 h-5 text-primary" />
        <h1 className="text-lg font-bold">Production Readiness Center</h1>
        {report && <span className={`ml-auto px-2 py-0.5 rounded text-[10px] font-bold ${report.score >= 80 ? "bg-emerald-500/10 text-emerald-500" : "bg-amber-500/10 text-amber-500"}`}>{report.score}% Certified</span>}
        <button onClick={fetchAll} className="p-1 rounded text-muted-foreground hover:bg-accent"><RefreshCw className={`w-3.5 h-3.5 ${loading ? "animate-spin" : ""}`} /></button>
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
        {activeTab === "certification" && <CertificationTab data={report} />}
        {activeTab === "readiness" && <ReadinessTab data={readiness} />}
        {activeTab === "benchmarks" && <BenchmarksTab data={benchmarks} />}
        {activeTab === "security" && <SecurityTab data={security} />}
        {activeTab === "recovery" && <RecoveryTab data={recovery} />}
        {activeTab === "release" && <ReleaseTab data={release} />}
      </div>
    </div>
  )
}

function CertificationTab({ data }: { data: any }) {
  if (!data) return <div className="p-8 text-center text-[10px] text-muted-foreground">Run certification to see results</div>
  return (
    <div className="space-y-4">
      <div className="grid grid-cols-4 gap-3">
        <MetricCard label="Score" value={`${data.score}%`} color={data.score >= 80 ? "text-emerald-500" : "text-amber-500"} />
        <MetricCard label="Passed" value={String(data.passed_systems)} color="text-emerald-500" />
        <MetricCard label="Failed" value={String(data.failed_systems)} color={data.failed_systems > 0 ? "text-red-500" : "text-muted-foreground"} />
        <MetricCard label="Total" value={String(data.total_systems)} />
      </div>
      {data.systems && Object.entries(data.systems).map(([name, sys]: [string, any]) => (
        <div key={name} className="rounded-lg border bg-card p-3">
          <div className="flex items-center gap-2 mb-1">
            {sys.passed ? <CheckCircle className="w-3 h-3 text-emerald-500" /> : <span className="w-3 h-3 rounded-full bg-red-500" />}
            <span className="text-[10px] font-medium capitalize">{name.replace(/_/g, " ")}</span>
            <span className="text-[9px] text-muted-foreground ml-auto">{sys.passed_checks}/{sys.total_checks} checks</span>
          </div>
          {sys.checks?.map((c: any, i: number) => (
            <div key={i} className="flex items-center gap-2 text-[9px] text-muted-foreground ml-5">
              <span>{c.passed ? "✓" : "✗"}</span>
              <span>{c.detail}</span>
            </div>
          ))}
        </div>
      ))}
    </div>
  )
}

function ReadinessTab({ data }: { data: any }) {
  if (!data) return <div className="p-8 text-center text-[10px] text-muted-foreground">No readiness data</div>
  return (
    <div className="space-y-4">
      <div className="grid grid-cols-2 gap-3">
        <MetricCard label="Readiness Score" value={`${data.score}%`} color={data.score >= 80 ? "text-emerald-500" : "text-amber-500"} />
        <MetricCard label="Overall" value={data.overall_ready ? "READY" : "NOT READY"} color={data.overall_ready ? "text-emerald-500" : "text-red-500"} />
      </div>
      {data.categories && Object.entries(data.categories).map(([cat, info]: [string, any]) => (
        <div key={cat} className="rounded-lg border bg-card p-3">
          <div className="text-[9px] text-muted-foreground uppercase mb-1">{cat}</div>
          <div className="grid grid-cols-2 gap-1 text-[10px]">
            {info.checks?.map((c: any, i: number) => (
              <div key={i} className="flex items-center gap-1">
                {c.passed ? <CheckCircle className="w-2.5 h-2.5 text-emerald-500" /> : <span className="w-2.5 h-2.5 rounded-full bg-red-500" />}
                <span>{c.name.replace(/_/g, " ").title()}</span>
              </div>
            ))}
          </div>
        </div>
      ))}
    </div>
  )
}

function BenchmarksTab({ data }: { data: any }) {
  if (!data?.benchmarks) return <div className="p-8 text-center text-[10px] text-muted-foreground">No benchmark data</div>
  const items = Object.entries(data.benchmarks)
  return (
    <div className="space-y-2">
      <div className="border rounded-lg overflow-hidden">
        <table className="w-full text-[10px]">
          <thead><tr className="bg-muted/30 border-b">
            <th className="text-left px-3 py-2">Subsystem</th>
            <th className="text-right px-3 py-2">P50</th>
            <th className="text-right px-3 py-2">P95</th>
            <th className="text-right px-3 py-2">P99</th>
            <th className="text-right px-3 py-2">Max</th>
          </tr></thead>
          <tbody className="divide-y">
            {items.map(([name, b]: [string, any]) => (
              <tr key={name} className="hover:bg-muted/20">
                <td className="px-3 py-1.5 font-medium capitalize">{name.replace(/_/g, " ")}</td>
                <td className="px-3 py-1.5 text-right font-mono">{b.p50_ms}ms</td>
                <td className={`px-3 py-1.5 text-right font-mono ${b.p95_ms > 200 ? "text-amber-500" : ""}`}>{b.p95_ms}ms</td>
                <td className="px-3 py-1.5 text-right font-mono">{b.p99_ms}ms</td>
                <td className="px-3 py-1.5 text-right font-mono">{b.max_ms}ms</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      {data.summary && (
        <div className="rounded-lg border bg-card p-2 text-[10px] text-muted-foreground">
          Average P50: {data.summary.average_p50_ms}ms | Slowest: {data.summary.slowest_subsystem} ({data.summary.slowest_p95_ms}ms)
        </div>
      )}
    </div>
  )
}

function SecurityTab({ data }: { data: any }) {
  if (!data) return <div className="p-8 text-center text-[10px] text-muted-foreground">No security data</div>
  return (
    <div className="space-y-3">
      <div className="grid grid-cols-3 gap-3">
        <MetricCard label="Score" value={`${data.score}%`} color={data.score >= 80 ? "text-emerald-500" : "text-red-500"} />
        <MetricCard label="Passed" value={String(data.passed_checks)} color="text-emerald-500" />
        <MetricCard label="Total" value={String(data.total_checks)} />
      </div>
      {data.checks?.map((c: any, i: number) => (
        <div key={i} className="flex items-center gap-2 p-2 rounded-lg border bg-card text-[10px]">
          {c.passed ? <CheckCircle className="w-3 h-3 text-emerald-500 shrink-0" /> : <span className="w-3 h-3 rounded-full bg-red-500 shrink-0" />}
          <span className="font-medium capitalize">{c.name.replace(/_/g, " ")}</span>
          <span className="text-muted-foreground flex-1">{c.detail}</span>
          {c.severity && <span className={`text-[8px] font-medium px-1 py-0.5 rounded ${c.severity === "critical" ? "bg-red-500/10 text-red-500" : "bg-amber-500/10 text-amber-500"}`}>{c.severity}</span>}
        </div>
      ))}
    </div>
  )
}

function RecoveryTab({ data }: { data: any }) {
  if (!data) return <div className="p-8 text-center text-[10px] text-muted-foreground">No recovery test data</div>
  return (
    <div className="space-y-3">
      <div className="grid grid-cols-3 gap-3">
        <MetricCard label="Passed" value={String(data.passed)} color="text-emerald-500" />
        <MetricCard label="Failed" value={String(data.failed)} color={data.failed > 0 ? "text-red-500" : "text-muted-foreground"} />
        <MetricCard label="Total" value={String(data.scenarios_tested)} />
      </div>
      {data.results?.map((r: any, i: number) => (
        <div key={i} className="flex items-center gap-2 p-2 rounded-lg border bg-card text-[10px]">
          {r.graceful_degradation ? <CheckCircle className="w-3 h-3 text-emerald-500 shrink-0" /> : <span className="w-3 h-3 rounded-full bg-red-500 shrink-0" />}
          <span className="font-medium capitalize w-32">{r.scenario.replace(/_/g, " ")}</span>
          <span className="text-muted-foreground flex-1 truncate">{r.detail}</span>
          <span className="text-[8px] font-medium text-muted-foreground bg-muted/30 px-1 py-0.5 rounded">{r.recovery_strategy}</span>
        </div>
      ))}
    </div>
  )
}

function ReleaseTab({ data }: { data: any }) {
  if (!data) return <div className="p-8 text-center text-[10px] text-muted-foreground">Generate release to see RC1 data</div>
  return (
    <div className="space-y-4">
      <div className="rounded-lg border bg-emerald-500/10 border-emerald-500/20 p-4 text-center">
        <div className="text-lg font-bold text-emerald-500">{data.release_candidate}</div>
        <div className="text-[10px] text-muted-foreground">Generated: {data.generated_at ? new Date(data.generated_at).toLocaleString() : "N/A"}</div>
      </div>
      <div className="grid grid-cols-2 gap-3">
        <MetricCard label="Certification Score" value={`${data.certification?.score ?? 0}%`} color={(data.certification?.score ?? 0) >= 80 ? "text-emerald-500" : "text-amber-500"} />
        <MetricCard label="Readiness Score" value={`${data.readiness?.score ?? 0}%`} color={(data.readiness?.score ?? 0) >= 80 ? "text-emerald-500" : "text-amber-500"} />
      </div>
      {data.known_limitations?.length > 0 && (
        <div className="rounded-lg border bg-amber-500/10 p-3">
          <div className="text-[9px] text-amber-500 uppercase mb-1">Known Limitations</div>
          {data.known_limitations.map((l: string, i: number) => <div key={i} className="text-[10px] text-amber-600">• {l}</div>)}
        </div>
      )}
      {data.deployment_checklist?.length > 0 && (
        <div className="rounded-lg border bg-card p-3">
          <div className="text-[9px] text-muted-foreground uppercase mb-1">Deployment Checklist</div>
          {data.deployment_checklist.map((item: string, i: number) => (
            <div key={i} className="flex items-center gap-2 text-[10px] text-muted-foreground">
              <span className="w-3 h-3 rounded border border-muted-foreground" />
              <span>{item}</span>
            </div>
          ))}
        </div>
      )}
      <div className="rounded-lg border bg-card p-3 text-center">
        <div className="text-[9px] text-muted-foreground uppercase mb-1">Approval Status</div>
        <div className="text-sm font-bold text-amber-500">{data.approval_status?.replace(/_/g, " ") || "PENDING"}</div>
      </div>
    </div>
  )
}

function MetricCard({ label, value, color }: { label: string; value: string; color?: string }) {
  return <div className="rounded-lg border bg-card p-3 text-center">
    <div className="text-[9px] text-muted-foreground uppercase">{label}</div>
    <div className={`text-lg font-bold font-mono mt-0.5 ${color || ""}`}>{value}</div>
  </div>
}
