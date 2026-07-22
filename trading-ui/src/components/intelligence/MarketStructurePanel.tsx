"use client"

import { useStructure } from "@/hooks/useStructure"
import { MetricCard } from "./MetricCard"
import { TrendBadge, StrengthBadge } from "./TrendBadge"
import { Skeleton } from "@/components/ui/skeleton"
import { AlertCircle, RefreshCw } from "lucide-react"

export function MarketStructurePanel() {
  const { data, isLoading, error, refetch } = useStructure()

  if (isLoading) return <div className="space-y-2 p-3"><Skeleton className="h-3 w-full" /><Skeleton className="h-3 w-5/6" /></div>
  if (error) return <div className="p-3 text-[10px] text-red-500 flex items-center gap-2"><AlertCircle className="w-3 h-3" /> Failed <button onClick={() => refetch()}><RefreshCw className="w-3 h-3" /></button></div>
  if (!data) return <div className="p-3 text-[10px] text-muted-foreground">No structure data</div>

  return (
    <div className="space-y-1.5">
      <div className="flex items-center gap-2 mb-1">
        <TrendBadge value={data.trend} />
        <StrengthBadge value={data.trend_strength} />
        <span className="text-[9px] text-muted-foreground ml-auto">{data.trend_age} bars</span>
      </div>

      <div className="text-[9px] font-medium text-muted-foreground uppercase tracking-wider mb-1">HH / HL / LH / LL</div>
      <MetricCard label="Last HH" value={data.last_hh?.toFixed(2)} />
      <MetricCard label="Last HL" value={data.last_hl?.toFixed(2)} />
      <MetricCard label="Last LH" value={data.last_lh?.toFixed(2)} />
      <MetricCard label="Last LL" value={data.last_ll?.toFixed(2)} />

      <div className="border-t my-1.5" />
      <MetricCard label="Swing High" value={data.current_swing_high?.toFixed(2)} />
      <MetricCard label="Swing Low" value={data.current_swing_low?.toFixed(2)} />
      <MetricCard label="Market Phase" value={data.market_phase} />
      <MetricCard label="BOS Count" value={data.bos_count} />
      <MetricCard label="CHoCH Count" value={data.choch_count} />

      <div className="border-t my-1.5" />
      <MetricCard label="Impulse" value={data.impulse_active ? "Active" : "No"} trend={data.impulse_active ? "up" : undefined} />
      <MetricCard label="Pullback" value={data.pullback_active ? "Active" : "No"} trend={data.pullback_active ? "down" : undefined} />
      <MetricCard label="Consolidation" value={`${data.consolidation_bars} bars`} />
      <MetricCard label="Liquidity Sweeps" value={data.liquidity_sweeps} />
      <MetricCard label="Valid Structure" value={data.valid_structure ? "Yes" : "No"} trend={data.valid_structure ? "up" : "down"} />
    </div>
  )
}
