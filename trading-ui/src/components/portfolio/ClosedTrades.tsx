"use client"

import { cn } from "@/lib/utils"
import type { ClosedTrade } from "@/store/usePortfolioStore"

interface ClosedTradesProps {
  trades: ClosedTrade[]
}

export function ClosedTrades({ trades }: ClosedTradesProps) {
  if (!trades.length) {
    return <div className="rounded-lg border bg-card p-6 text-center text-[10px] text-muted-foreground">No closed trades</div>
  }

  return (
    <div className="rounded-lg border bg-card overflow-hidden">
      <div className="text-[9px] font-medium text-muted-foreground uppercase tracking-wider px-3 pt-2 pb-1">Closed Trades ({trades.length})</div>
      <div className="overflow-x-auto max-h-[400px] overflow-y-auto">
        <table className="w-full text-[10px]">
          <thead className="sticky top-0 bg-card">
            <tr className="border-b text-muted-foreground">
              <th className="text-left font-medium px-2 py-1.5">Symbol</th>
              <th className="text-center font-medium px-2 py-1.5">Dir</th>
              <th className="text-right font-medium px-2 py-1.5">Entry</th>
              <th className="text-right font-medium px-2 py-1.5">Exit</th>
              <th className="text-right font-medium px-2 py-1.5">PnL</th>
              <th className="text-right font-medium px-2 py-1.5">RR</th>
              <th className="text-right font-medium px-2 py-1.5">Duration</th>
              <th className="text-left font-medium px-2 py-1.5">Reason</th>
              <th className="text-left font-medium px-2 py-1.5">Result</th>
            </tr>
          </thead>
          <tbody>
            {[...trades].reverse().map((trade) => (
              <tr key={trade.id} className="border-b last:border-0 hover:bg-muted/20 transition-colors">
                <td className="px-2 py-1.5 font-medium">{trade.symbol}</td>
                <td className={cn("px-2 py-1.5 text-center font-mono", trade.direction === "LONG" ? "text-emerald-500" : "text-red-500")}>{trade.direction}</td>
                <td className="px-2 py-1.5 text-right font-mono">{trade.entry.toFixed(2)}</td>
                <td className="px-2 py-1.5 text-right font-mono">{trade.exit.toFixed(2)}</td>
                <td className={cn("px-2 py-1.5 text-right font-mono font-medium", (trade.pnl ?? 0) >= 0 ? "text-emerald-500" : "text-red-500")}>
                  {(trade.pnl ?? 0) >= 0 ? "+" : ""}{trade.pnl?.toFixed(2) ?? "--"}
                </td>
                <td className={cn("px-2 py-1.5 text-right font-mono", (trade.rr ?? 0) >= 1 ? "text-emerald-500" : "text-amber-500")}>
                  {trade.rr?.toFixed(1) ?? "--"}
                </td>
                <td className="px-2 py-1.5 text-right font-mono">{trade.duration}h</td>
                <td className="px-2 py-1.5">{trade.exitReason}</td>
                <td className="px-2 py-1.5">
                  <span className={cn("px-1 py-0.5 rounded text-[8px] font-medium", (trade.pnl ?? 0) >= 0 ? "bg-emerald-500/10 text-emerald-500" : "bg-red-500/10 text-red-500")}>
                    {(trade.pnl ?? 0) >= 0 ? "Win" : "Loss"}
                  </span>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}
