"use client"

import { cn } from "@/lib/utils"
import type { Position } from "@/store/usePortfolioStore"

interface OpenPositionsProps {
  positions: Position[]
  onClose: (position: Position) => void
  onModifySL: (id: string) => void
  onBreakEven: (id: string) => void
}

export function OpenPositions({ positions, onClose, onModifySL, onBreakEven }: OpenPositionsProps) {
  if (!positions.length) {
    return <div className="rounded-lg border bg-card p-6 text-center text-[10px] text-muted-foreground">No open positions</div>
  }

  return (
    <div className="rounded-lg border bg-card overflow-hidden">
      <div className="text-[9px] font-medium text-muted-foreground uppercase tracking-wider px-3 pt-2 pb-1">Open Positions ({positions.length})</div>
      <div className="overflow-x-auto">
        <table className="w-full text-[10px]">
          <thead>
            <tr className="border-b text-muted-foreground">
              <th className="text-left font-medium px-2 py-1.5">Symbol</th>
              <th className="text-center font-medium px-2 py-1.5">Dir</th>
              <th className="text-right font-medium px-2 py-1.5">Entry</th>
              <th className="text-right font-medium px-2 py-1.5">Current</th>
              <th className="text-right font-medium px-2 py-1.5">PnL</th>
              <th className="text-right font-medium px-2 py-1.5">RR</th>
              <th className="text-right font-medium px-2 py-1.5">Score</th>
              <th className="text-center font-medium px-2 py-1.5">Risk</th>
              <th className="text-center font-medium px-2 py-1.5">SL</th>
              <th className="text-center font-medium px-2 py-1.5">Actions</th>
            </tr>
          </thead>
          <tbody>
            {positions.map((pos) => (
              <tr key={pos.id} className="border-b last:border-0 hover:bg-muted/20 transition-colors">
                <td className="px-2 py-1.5 font-medium">{pos.symbol}</td>
                <td className={cn("px-2 py-1.5 text-center font-mono font-medium", pos.direction === "LONG" ? "text-emerald-500" : "text-red-500")}>{pos.direction}</td>
                <td className="px-2 py-1.5 text-right font-mono">{pos.entry.toFixed(2)}</td>
                <td className="px-2 py-1.5 text-right font-mono">{pos.currentPrice.toFixed(2)}</td>
                <td className={cn("px-2 py-1.5 text-right font-mono font-medium", pos.pnl >= 0 ? "text-emerald-500" : "text-red-500")}>
                  {pos.pnl >= 0 ? "+" : ""}{pos.pnl.toFixed(2)} ({(pos.pnlPercent >= 0 ? "+" : "")}{pos.pnlPercent.toFixed(2)}%)
                </td>
                <td className={cn("px-2 py-1.5 text-right font-mono", pos.rr >= 1 ? "text-emerald-500" : "text-amber-500")}>{pos.rr.toFixed(1)}</td>
                <td className="px-2 py-1.5 text-right font-mono">{pos.aiScore ?? "--"}</td>
                <td className="px-2 py-1.5 text-center">
                  <span className={cn("px-1 py-0.5 rounded text-[8px]", pos.risk === "LOW" ? "bg-emerald-500/10 text-emerald-500" : pos.risk === "HIGH" ? "bg-red-500/10 text-red-500" : "bg-amber-500/10 text-amber-500")}>
                    {pos.risk || "--"}
                  </span>
                </td>
                <td className="px-2 py-1.5 text-center font-mono">{pos.trailingStop ? pos.trailingStop.toFixed(2) : "--"}</td>
                <td className="px-2 py-1.5">
                  <div className="flex items-center gap-1">
                    <button onClick={() => onModifySL(pos.id)} className="px-1 py-0.5 rounded text-[8px] bg-muted/30 hover:bg-accent transition-colors">SL</button>
                    <button onClick={() => onBreakEven(pos.id)} className="px-1 py-0.5 rounded text-[8px] bg-muted/30 hover:bg-accent transition-colors">BE</button>
                    <button onClick={() => onClose(pos)} className="px-1.5 py-0.5 rounded text-[8px] bg-red-500/10 text-red-500 hover:bg-red-500/20 transition-colors">Close</button>
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}
