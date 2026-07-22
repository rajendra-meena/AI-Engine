"use client"

/* eslint-disable @typescript-eslint/no-explicit-any */

import { usePatterns } from "@/hooks/usePatterns"
import { cn } from "@/lib/utils"
import { Skeleton } from "@/components/ui/skeleton"
import { AlertCircle, RefreshCw, TrendingUp, TrendingDown, Minus } from "lucide-react"

function PatternIcon({ dir }: { dir: string }) {
  if (dir === "bullish") return <TrendingUp className="w-2.5 h-2.5 text-emerald-500" />
  if (dir === "bearish") return <TrendingDown className="w-2.5 h-2.5 text-red-500" />
  return <Minus className="w-2.5 h-2.5 text-muted-foreground" />
}

export function PatternPanel() {
  const { data, isLoading, error, refetch } = usePatterns()

  if (isLoading) return <div className="space-y-2 p-3"><Skeleton className="h-3 w-full" /><Skeleton className="h-3 w-5/6" /></div>
  if (error) return <div className="p-3 text-[10px] text-red-500 flex items-center gap-2"><AlertCircle className="w-3 h-3" /> Failed <button onClick={() => refetch()}><RefreshCw className="w-3 h-3" /></button></div>
  if (!data) return <div className="p-3 text-[10px] text-muted-foreground">No pattern data</div>

  const strongest = data.strongest_pattern
  const direction = data.pattern_direction
  const confidence = data.confidence

  return (
    <div className="space-y-1.5">
      <div className="flex items-center gap-2 mb-1">
        <span className={cn(
          "text-[10px] font-semibold",
          direction === "bullish" ? "text-emerald-500" : direction === "bearish" ? "text-red-500" : "text-muted-foreground"
        )}>
          {strongest || "No patterns"}
        </span>
        <span className="text-[9px] text-muted-foreground ml-auto">{data.total_count} total</span>
      </div>

      <div className="text-[9px] font-medium text-muted-foreground uppercase tracking-wider mb-1">Candlestick</div>
      {data.candlestick_patterns?.length > 0 ? data.candlestick_patterns.slice(0, 4).map((p: any, i: number) => (
        <div key={i} className="flex items-center gap-1.5">
          <PatternIcon dir={p.direction} />
          <span className="text-[10px] text-muted-foreground flex-1">{p.name}</span>
          <span className={cn("text-[8px] font-medium", p.strength === "strong" ? "text-emerald-500" : "text-muted-foreground")}>{p.strength}</span>
        </div>
      )) : <div className="text-[9px] text-muted-foreground/50">None detected</div>}

      <div className="text-[9px] font-medium text-muted-foreground uppercase tracking-wider mt-1">Breakouts</div>
      {data.breakout_patterns?.length > 0 ? data.breakout_patterns.slice(0, 4).map((p: any, i: number) => (
        <div key={i} className="flex items-center gap-1.5">
          <PatternIcon dir={p.direction} />
          <span className="text-[10px] text-muted-foreground flex-1">{p.name}</span>
          <span className="text-[8px] text-muted-foreground">{p.strength}</span>
        </div>
      )) : <div className="text-[9px] text-muted-foreground/50">None detected</div>}

      <div className="border-t my-1 pt-1 flex items-center gap-2">
        <span className="text-[9px] text-muted-foreground">Confidence:</span>
        <span className={cn("text-[10px] font-bold", confidence === "high" ? "text-emerald-500" : confidence === "medium" ? "text-amber-500" : "text-red-500")}>{confidence}</span>
      </div>
    </div>
  )
}
