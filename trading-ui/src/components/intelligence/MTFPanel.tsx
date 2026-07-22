"use client"

import { useMTF } from "@/hooks/useMTF"
import { TrendBadge } from "./TrendBadge"
import { RiskBadge } from "./RiskBadge"
import { Skeleton } from "@/components/ui/skeleton"
import { AlertCircle, RefreshCw } from "lucide-react"
import { cn } from "@/lib/utils"

const TF_ORDER = ["60m", "30m", "15m", "10m", "5m", "3m", "2m", "1m"]

export function MTFPanel() {
  const { data, isLoading, error, refetch } = useMTF()

  if (isLoading) return <div className="space-y-2 p-3"><Skeleton className="h-3 w-full" /><Skeleton className="h-3 w-5/6" /></div>
  if (error) return <div className="p-3 text-[10px] text-red-500 flex items-center gap-2"><AlertCircle className="w-3 h-3" /> Failed <button onClick={() => refetch()}><RefreshCw className="w-3 h-3" /></button></div>
  if (!data) return <div className="p-3 text-[10px] text-muted-foreground">No MTF data</div>

  return (
    <div className="space-y-1.5">
      {/* Summary */}
      <div className="flex items-center gap-2 mb-1">
        <span className="text-[10px] font-semibold">{data.alignment_level}</span>
        <span className="text-[10px] font-mono text-muted-foreground">Score: {data.alignment_score}</span>
      </div>
      <TrendBadge value={data.institutional_bias} />
      <div className="flex items-center gap-2 mt-1">
        <RiskBadge level={data.trading_permission === "ALLOW_LONG" ? "LOW" : data.trading_permission === "ALLOW_SHORT" ? "MEDIUM" : data.trading_permission === "NO_TRADE" ? "HIGH" : undefined} />
        <span className="text-[9px] text-muted-foreground">{data.trading_permission}</span>
      </div>

      <div className="border-t my-1.5" />
      <MetricCard label="Market Condition" value={data.market_condition} />

      {/* Timeframe Table */}
      <div className="text-[9px] font-medium text-muted-foreground uppercase tracking-wider mb-1">Timeframes</div>
      <div className="space-y-0.5">
        {TF_ORDER.map((tf) => {
          const ctx = data.timeframes?.[tf]
          if (!ctx) return null
          return (
            <div key={tf} className="flex items-center gap-2 text-[10px]">
              <span className="w-6 font-mono font-medium text-muted-foreground">{tf}</span>
              <span className={cn("flex-1", ctx.bias === "BULLISH" ? "text-emerald-500" : ctx.bias === "BEARISH" ? "text-red-500" : "text-muted-foreground")}>
                {ctx.bias}
              </span>
              <span className="text-muted-foreground/50 w-6 text-right">{ctx.confidence}%</span>
            </div>
          )
        })}
      </div>

      {data.warnings?.length > 0 && (
        <div className="border-t my-1.5 pt-1">
          <div className="text-[9px] font-medium text-muted-foreground uppercase tracking-wider mb-1">Warnings</div>
          {data.warnings.map((w: string, i: number) => (
            <div key={i} className="text-[9px] text-amber-500 flex items-start gap-1">
              <span className="mt-0.5">*</span> {w}
            </div>
          ))}
        </div>
      )}
    </div>
  )
}

function MetricCard({ label, value }: { label: string; value?: string | number | null }) {
  return (
    <div className="flex items-center justify-between">
      <span className="text-[10px] text-muted-foreground">{label}</span>
      <span className="text-[11px] font-mono font-medium">{value ?? "--"}</span>
    </div>
  )
}
