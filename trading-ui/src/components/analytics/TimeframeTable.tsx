"use client"

import { cn } from "@/lib/utils"
import type { TimeframeMetric } from "@/services/analyticsService"

interface TimeframeTableProps {
  data: TimeframeMetric[]
  className?: string
}

export function TimeframeTable({ data, className }: TimeframeTableProps) {
  if (!data.length) {
    return <div className="rounded-lg border bg-card p-3 text-[10px] text-muted-foreground text-center">No timeframe data</div>
  }

  return (
    <div className={cn("rounded-lg border bg-card overflow-hidden", className)}>
      <div className="text-[9px] font-medium text-muted-foreground uppercase tracking-wider px-3 pt-2 pb-1">Timeframe Performance</div>
      <div className="overflow-x-auto">
        <table className="w-full text-[10px]">
          <thead>
            <tr className="border-b text-muted-foreground">
              <th className="text-left font-medium px-3 py-1.5">Timeframe</th>
              <th className="text-right font-medium px-3 py-1.5">Predictions</th>
              <th className="text-right font-medium px-3 py-1.5">Accuracy</th>
              <th className="text-right font-medium px-3 py-1.5">Avg Score</th>
              <th className="text-right font-medium px-3 py-1.5">Avg Confidence</th>
            </tr>
          </thead>
          <tbody>
            {data.map((tf) => (
              <tr key={tf.timeframe} className="border-b last:border-0 hover:bg-muted/20 transition-colors">
                <td className="px-3 py-1.5 font-mono font-medium">{tf.timeframe}</td>
                <td className="px-3 py-1.5 text-right font-mono">{tf.predictionCount}</td>
                <td className={cn("px-3 py-1.5 text-right font-mono font-medium", tf.accuracy >= 60 ? "text-emerald-500" : tf.accuracy >= 40 ? "text-amber-500" : "text-red-500")}>
                  {tf.accuracy.toFixed(1)}%
                </td>
                <td className="px-3 py-1.5 text-right font-mono">{tf.avgScore.toFixed(0)}</td>
                <td className="px-3 py-1.5 text-right font-mono">{tf.avgConfidence.toFixed(0)}%</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}
