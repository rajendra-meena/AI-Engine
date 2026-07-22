"use client"

import { cn } from "@/lib/utils"
import type { PatternMetric } from "@/services/analyticsService"

interface PatternTableProps {
  data: PatternMetric[]
  className?: string
}

export function PatternTable({ data, className }: PatternTableProps) {
  if (!data.length) {
    return <div className="rounded-lg border bg-card p-3 text-[10px] text-muted-foreground text-center">Pattern analytics available with prediction data</div>
  }

  return (
    <div className={cn("rounded-lg border bg-card overflow-hidden", className)}>
      <div className="text-[9px] font-medium text-muted-foreground uppercase tracking-wider px-3 pt-2 pb-1">Pattern Performance</div>
      <div className="overflow-x-auto">
        <table className="w-full text-[10px]">
          <thead>
            <tr className="border-b text-muted-foreground">
              <th className="text-left font-medium px-3 py-1.5">Pattern</th>
              <th className="text-left font-medium px-3 py-1.5">Type</th>
              <th className="text-right font-medium px-3 py-1.5">Occurrences</th>
              <th className="text-right font-medium px-3 py-1.5">Wins</th>
              <th className="text-right font-medium px-3 py-1.5">Losses</th>
              <th className="text-right font-medium px-3 py-1.5">Accuracy</th>
              <th className="text-right font-medium px-3 py-1.5">Avg RR</th>
            </tr>
          </thead>
          <tbody>
            {data.map((p, i) => (
              <tr key={i} className="border-b last:border-0 hover:bg-muted/20 transition-colors">
                <td className="px-3 py-1.5 font-medium">{p.name}</td>
                <td className="px-3 py-1.5 text-muted-foreground">{p.type}</td>
                <td className="px-3 py-1.5 text-right font-mono">{p.occurrences}</td>
                <td className="px-3 py-1.5 text-right font-mono text-emerald-500">{p.wins}</td>
                <td className="px-3 py-1.5 text-right font-mono text-red-500">{p.losses}</td>
                <td className={cn("px-3 py-1.5 text-right font-mono font-medium", p.accuracy >= 60 ? "text-emerald-500" : "text-amber-500")}>
                  {p.accuracy.toFixed(1)}%
                </td>
                <td className="px-3 py-1.5 text-right font-mono">{p.avgRR.toFixed(1)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}
