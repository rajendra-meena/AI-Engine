"use client"
/* eslint-disable @typescript-eslint/no-explicit-any */

import { useSR } from "@/hooks/useSR"
import { MetricCard } from "./MetricCard"
import { ProgressBar } from "./RiskBadge"
import { Skeleton } from "@/components/ui/skeleton"
import { AlertCircle, RefreshCw } from "lucide-react"

export function SupportResistancePanel() {
  const { data, isLoading, error, refetch } = useSR()

  if (isLoading) return <div className="space-y-2 p-3"><Skeleton className="h-3 w-full" /><Skeleton className="h-3 w-5/6" /></div>
  if (error) return <div className="p-3 text-[10px] text-red-500 flex items-center gap-2"><AlertCircle className="w-3 h-3" /> Failed <button onClick={() => refetch()}><RefreshCw className="w-3 h-3" /></button></div>
  if (!data) return <div className="p-3 text-[10px] text-muted-foreground">No S/R data</div>

  return (
    <div className="space-y-1.5">
      <div className="flex items-center gap-2 mb-1">
        <span className="text-[10px] font-semibold text-emerald-500">S: {data.nearest_support?.toFixed(2) ?? "--"}</span>
        <span className="text-[9px] text-muted-foreground">|</span>
        <span className="text-[10px] font-semibold text-red-500">R: {data.nearest_resistance?.toFixed(2) ?? "--"}</span>
      </div>

      <ProgressBar value={data.confidence || 0} className="mb-1" />

      <div className="text-[9px] font-medium text-muted-foreground uppercase tracking-wider mb-1">Major Supports</div>
      {data.major_supports?.slice(0, 3).map((s: any, i: number) => (
        <MetricCard key={i} label={s.label || `S ${i + 1}`} value={s.price?.toFixed(2)} />
      )) || <div className="text-[9px] text-muted-foreground/50">None</div>}

      <div className="text-[9px] font-medium text-muted-foreground uppercase tracking-wider mt-1">Major Resistances</div>
      {data.major_resistances?.slice(0, 3).map((r: any, i: number) => (
        <MetricCard key={i} label={r.label || `R ${i + 1}`} value={r.price?.toFixed(2)} />
      )) || <div className="text-[9px] text-muted-foreground/50">None</div>}

      <div className="border-t my-1.5" />
      <MetricCard label="Supply Zones" value={data.supply_zones?.length || 0} />
      <MetricCard label="Demand Zones" value={data.demand_zones?.length || 0} />
      <MetricCard label="Breakout State" value={data.breakout_state || "none"} />
      <MetricCard label="Zone Strength" value={data.zone_strength || "N/A"} />
    </div>
  )
}
