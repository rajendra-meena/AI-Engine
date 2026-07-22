"use client"

import { useMemo } from "react"
import { cn } from "@/lib/utils"
import type { DecisionHistoryItem } from "@/services/analyticsService"

interface DecisionHistoryProps {
  data: DecisionHistoryItem[]
  page: number
  pageSize: number
  total: number
  onPageChange: (page: number) => void
  onSort: (field: string) => void
  className?: string
}

const RESULT_COLORS: Record<string, string> = {
  Win: "text-emerald-500 bg-emerald-500/10",
  Loss: "text-red-500 bg-red-500/10",
  SL: "text-amber-500 bg-amber-500/10",
}

export function DecisionHistory({ data, page, pageSize, total, onPageChange, onSort, className }: DecisionHistoryProps) {
  const totalPages = Math.max(1, Math.ceil(total / pageSize))

  const paginated = useMemo(() => {
    const start = (page - 1) * pageSize
    return data.slice(start, start + pageSize)
  }, [data, page, pageSize])

  if (!data.length) {
    return <div className="rounded-lg border bg-card p-6 text-center text-[10px] text-muted-foreground">No decision history</div>
  }

  return (
    <div className={cn("rounded-lg border bg-card overflow-hidden", className)}>
      <div className="text-[9px] font-medium text-muted-foreground uppercase tracking-wider px-3 pt-2 pb-1">Decision History</div>

      <div className="overflow-x-auto max-h-[400px] overflow-y-auto">
        <table className="w-full text-[10px]">
          <thead className="sticky top-0 bg-card">
            <tr className="border-b text-muted-foreground">
              {["Time", "Symbol", "Direction", "Score", "Conf", "Risk", "Decision", "Entry", "Result", "Reason"].map((col) => (
                <th
                  key={col}
                  onClick={() => onSort(col.toLowerCase())}
                  className="text-left font-medium px-2 py-1.5 cursor-pointer hover:text-foreground transition-colors whitespace-nowrap"
                >
                  {col}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {paginated.map((row) => (
              <tr key={row.id} className="border-b last:border-0 hover:bg-muted/20 transition-colors">
                <td className="px-2 py-1.5 font-mono text-muted-foreground whitespace-nowrap">
                  {new Date(row.time).toLocaleDateString("en-IN", { day: "2-digit", month: "short" })}
                </td>
                <td className="px-2 py-1.5 font-medium">{row.symbol}</td>
                <td className={cn("px-2 py-1.5 font-mono font-medium", row.direction === "LONG" || row.direction === "BULLISH" ? "text-emerald-500" : row.direction === "SHORT" || row.direction === "BEARISH" ? "text-red-500" : "")}>
                  {row.direction}
                </td>
                <td className="px-2 py-1.5 font-mono">{row.score ?? "--"}</td>
                <td className="px-2 py-1.5 font-mono">{row.confidence != null ? `${row.confidence}%` : "--"}</td>
                <td className="px-2 py-1.5">
                  <span className={cn("px-1 py-0.5 rounded text-[8px] font-medium", row.risk === "LOW" ? "text-emerald-500 bg-emerald-500/10" : row.risk === "HIGH" ? "text-red-500 bg-red-500/10" : "text-muted-foreground bg-muted/30")}>
                    {row.risk || "--"}
                  </span>
                </td>
                <td className={cn("px-2 py-1.5 font-mono font-medium", row.decision === "hit" ? "text-emerald-500" : row.decision === "miss" ? "text-red-500" : "")}>
                  {row.decision}
                </td>
                <td className="px-2 py-1.5 font-mono">{row.entry ?? "--"}</td>
                <td className="px-2 py-1.5">
                  {row.result && (
                    <span className={cn("px-1 py-0.5 rounded text-[8px] font-medium", RESULT_COLORS[row.result] || "")}>
                      {row.result}
                    </span>
                  )}
                </td>
                <td className="px-2 py-1.5 text-muted-foreground max-w-[120px] truncate">{row.reason || "--"}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* Pagination */}
      {totalPages > 1 && (
        <div className="flex items-center justify-between px-3 py-2 border-t">
          <span className="text-[9px] text-muted-foreground">{(page - 1) * pageSize + 1}-{Math.min(page * pageSize, total)} of {total}</span>
          <div className="flex items-center gap-1">
            <button
              onClick={() => onPageChange(page - 1)}
              disabled={page <= 1}
              className="rounded px-1.5 py-0.5 text-[9px] text-muted-foreground hover:bg-accent disabled:opacity-30 transition-colors"
            >
              Prev
            </button>
            {Array.from({ length: Math.min(totalPages, 5) }, (_, i) => {
              const start = Math.max(1, page - 2)
              const p = start + i
              if (p > totalPages) return null
              return (
                <button
                  key={p}
                  onClick={() => onPageChange(p)}
                  className={cn("rounded px-1.5 py-0.5 text-[9px] transition-colors", p === page ? "bg-primary/20 text-primary" : "text-muted-foreground hover:bg-accent")}
                >
                  {p}
                </button>
              )
            })}
            <button
              onClick={() => onPageChange(page + 1)}
              disabled={page >= totalPages}
              className="rounded px-1.5 py-0.5 text-[9px] text-muted-foreground hover:bg-accent disabled:opacity-30 transition-colors"
            >
              Next
            </button>
          </div>
        </div>
      )}
    </div>
  )
}
