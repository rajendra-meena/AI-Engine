"use client"

import { cn } from "@/lib/utils"
import { CheckCircle2, MinusCircle, XCircle } from "lucide-react"
import type { DecisionMatrixRow } from "@/services/explainabilityService"

interface DecisionMatrixProps {
  rows: DecisionMatrixRow[]
}

export function DecisionMatrix({ rows }: DecisionMatrixProps) {
  return (
    <div className="rounded-lg border bg-card p-3 space-y-2">
      <div className="text-[9px] font-medium text-muted-foreground uppercase tracking-wider">Decision Matrix</div>
      <div className="overflow-x-auto">
        <table className="w-full text-[10px]">
          <thead>
            <tr className="border-b text-muted-foreground">
              <th className="text-left font-medium px-2 py-1">Factor</th>
              <th className="text-center font-medium px-2 py-1">Positive</th>
              <th className="text-center font-medium px-2 py-1">Neutral</th>
              <th className="text-center font-medium px-2 py-1">Negative</th>
              <th className="text-right font-medium px-2 py-1 w-20">Value</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((row) => (
              <tr key={row.label} className="border-b last:border-0 hover:bg-muted/20">
                <td className="px-2 py-1.5 font-medium">{row.label}</td>
                <td className="px-2 py-1.5 text-center">{row.positive ? <CheckCircle2 className="w-3.5 h-3.5 text-emerald-500 mx-auto" /> : <span className="text-muted-foreground/30">—</span>}</td>
                <td className="px-2 py-1.5 text-center">{row.neutral ? <MinusCircle className="w-3.5 h-3.5 text-amber-500 mx-auto" /> : <span className="text-muted-foreground/30">—</span>}</td>
                <td className="px-2 py-1.5 text-center">{row.negative ? <XCircle className="w-3.5 h-3.5 text-red-500 mx-auto" /> : <span className="text-muted-foreground/30">—</span>}</td>
                <td className={cn("px-2 py-1.5 text-right font-mono font-medium", row.value >= 60 ? "text-emerald-500" : row.value >= 40 ? "text-amber-500" : "text-red-500")}>{row.value}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}
