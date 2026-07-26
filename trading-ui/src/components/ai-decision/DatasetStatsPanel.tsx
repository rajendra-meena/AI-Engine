"use client"

import { useState, useEffect } from "react"
import { aiDecisionService, type DatasetStats } from "@/services/aiDecisionService"

export function DatasetStatsPanel() {
  const [stats, setStats] = useState<DatasetStats | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    aiDecisionService.getDatasetStats()
      .then(setStats)
      .catch(() => {})
      .finally(() => setLoading(false))
  }, [])

  if (loading) {
    return <div className="p-8 text-center text-[10px] text-muted-foreground">Loading dataset stats...</div>
  }

  if (!stats) {
    return <div className="p-8 text-center text-[10px] text-muted-foreground">No dataset data available</div>
  }

  return (
    <div className="space-y-4">
      <Metric label="Total Records" value={String(stats.total_records)} />

      <div className="grid grid-cols-2 gap-4">
        {Object.keys(stats.by_decision).length > 0 && (
          <div className="rounded-lg border bg-card p-3">
            <div className="text-[9px] text-muted-foreground uppercase mb-2">By Decision</div>
            <div className="space-y-1">
              {Object.entries(stats.by_decision).map(([k, v]) => (
                <div key={k} className="flex justify-between text-[10px]">
                  <span className="capitalize">{k.replace(/_/g, " ")}</span>
                  <span className="font-mono">{v}</span>
                </div>
              ))}
            </div>
          </div>
        )}

        {Object.keys(stats.by_grade).length > 0 && (
          <div className="rounded-lg border bg-card p-3">
            <div className="text-[9px] text-muted-foreground uppercase mb-2">By Grade</div>
            <div className="space-y-1">
              {Object.entries(stats.by_grade).map(([k, v]) => (
                <div key={k} className="flex justify-between text-[10px]">
                  <span>{k}</span>
                  <span className="font-mono">{v}</span>
                </div>
              ))}
            </div>
          </div>
        )}

        {Object.keys(stats.by_outcome).length > 0 && (
          <div className="rounded-lg border bg-card p-3">
            <div className="text-[9px] text-muted-foreground uppercase mb-2">By Outcome</div>
            <div className="space-y-1">
              {Object.entries(stats.by_outcome).map(([k, v]) => (
                <div key={k} className="flex justify-between text-[10px]">
                  <span>{k}</span>
                  <span className="font-mono">{v}</span>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>

      {stats.latest_timestamp && (
        <div className="text-[9px] text-muted-foreground">
          Latest record: {new Date(stats.latest_timestamp).toLocaleString()}
        </div>
      )}
    </div>
  )
}

function Metric({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-lg border bg-card p-3 text-center">
      <div className="text-[9px] text-muted-foreground uppercase">{label}</div>
      <div className="text-lg font-bold font-mono mt-0.5">{value}</div>
    </div>
  )
}
