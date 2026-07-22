"use client"

import { useMemo } from "react"
import { cn } from "@/lib/utils"
import { ScannerRanking } from "./ScannerRanking"
import { Star, TrendingUp, TrendingDown, Minus } from "lucide-react"
import { motion, AnimatePresence } from "framer-motion"
import type { ScannerRow, ScannerSort } from "@/store/useScannerStore"

interface ScannerTableProps {
  rows: ScannerRow[]
  sort: ScannerSort
  watchlist: { symbol: string; pinned: boolean }[]
  flashSymbols: string[]
  selectedSymbol: string | null
  onSelectSymbol: (symbol: string | null) => void
  onToggleWatchlist: (symbol: string) => void
  onTogglePin: (symbol: string) => void
  onSortChange: (sort: ScannerSort) => void
  className?: string
}

const RISK_COLORS: Record<string, string> = {
  LOW: "text-emerald-500", MEDIUM: "text-amber-500", HIGH: "text-red-500", EXTREME: "text-red-600",
}

const BIAS_COLORS: Record<string, string> = {
  BULLISH: "text-emerald-500", BEARISH: "text-red-500", NEUTRAL: "text-muted-foreground",
}

const TREND_ICONS: Record<string, React.ReactNode> = {
  UPTREND: <TrendingUp className="w-3 h-3 text-emerald-500" />,
  DOWNTREND: <TrendingDown className="w-3 h-3 text-red-500" />,
}

function TrendCell({ trend }: { trend: string }) {
  return (
    <span className="flex items-center gap-1">
      {TREND_ICONS[trend] || <Minus className="w-3 h-3 text-muted-foreground" />}
      <span className="text-[9px]">{trend === "UPTREND" ? "UP" : trend === "DOWNTREND" ? "DOWN" : "RNG"}</span>
    </span>
  )
}

function ChangeCell({ change }: { change: number }) {
  return (
    <span className={cn("font-mono text-[10px]", change > 0 ? "text-emerald-500" : change < 0 ? "text-red-500" : "text-muted-foreground")}>
      {change > 0 ? "+" : ""}{change.toFixed(2)}%
    </span>
  )
}

function ScoreCell({ score }: { score: number }) {
  return (
    <span className={cn("font-mono font-bold text-[11px]", score >= 80 ? "text-emerald-500" : score >= 60 ? "text-blue-500" : score >= 40 ? "text-amber-500" : "text-red-500")}>
      {score}
    </span>
  )
}

function RiskCell({ risk }: { risk: string }) {
  return <span className={cn("text-[9px] font-medium", RISK_COLORS[risk] || "")}>{risk}</span>
}

function RRCell({ rr }: { rr: number }) {
  return (
    <span className={cn("font-mono text-[10px] font-medium", rr >= 2 ? "text-emerald-500" : rr >= 1 ? "text-amber-500" : "text-muted-foreground")}>
      {rr.toFixed(1)}:1
    </span>
  )
}

export function ScannerTable({
  rows, sort, watchlist, flashSymbols, selectedSymbol,
  onSelectSymbol, onToggleWatchlist, onTogglePin, onSortChange, className,
}: ScannerTableProps) {
  const wlSymbols = useMemo(() => new Set(watchlist.map((w) => w.symbol)), [watchlist])
  const pinnedSymbols = useMemo(() => new Set(watchlist.filter((w) => w.pinned).map((w) => w.symbol)), [watchlist])

  const sortedRows = useMemo(() => {
    const pinned = rows.filter((r) => pinnedSymbols.has(r.symbol))
    const unpinned = rows.filter((r) => !pinnedSymbols.has(r.symbol))
    return [...pinned, ...unpinned]
  }, [rows, pinnedSymbols])

  const renderSortArrow = (field: string) => {
    if (sort.field !== field) return null
    return <span className="ml-0.5 text-[8px]">{sort.direction === "desc" ? "▼" : "▲"}</span>
  }

  const handleSort = (field: string) => {
    onSortChange({ field: field as "score" | "confidence" | "rr" | "change" | "volume" | "price" | "symbol", direction: sort.field === field && sort.direction === "desc" ? "asc" : "desc" })
  }

  if (!rows.length) {
    return (
      <div className="rounded-lg border bg-card p-8 text-center">
        <div className="text-[10px] text-muted-foreground">No scanner data available. Start a scan to see results.</div>
      </div>
    )
  }

  return (
    <div className={cn("rounded-lg border bg-card overflow-hidden", className)}>
      <div className="overflow-x-auto">
        <table className="w-full text-[10px]">
          <thead>
            <tr className="border-b text-muted-foreground">
              <th className="w-6 px-1" />
              <th className="w-4 px-1" />
              <th className="text-left font-medium px-2 py-1.5 cursor-pointer hover:text-foreground" onClick={() => handleSort("symbol")}>
                Symbol {renderSortArrow("symbol")}
              </th>
              <th className="text-right font-medium px-2 py-1.5 cursor-pointer hover:text-foreground" onClick={() => handleSort("price")}>
                Price {renderSortArrow("price")}
              </th>
              <th className="text-right font-medium px-2 py-1.5 cursor-pointer hover:text-foreground" onClick={() => handleSort("change")}>
                Change {renderSortArrow("change")}
              </th>
              <th className="text-right font-medium px-2 py-1.5 cursor-pointer hover:text-foreground" onClick={() => handleSort("volume")}>
                Vol {renderSortArrow("volume")}
              </th>
              <th className="text-center font-medium px-2 py-1.5">Trend</th>
              <th className="text-right font-medium px-2 py-1.5 cursor-pointer hover:text-foreground" onClick={() => handleSort("score")}>
                Score {renderSortArrow("score")}
              </th>
              <th className="text-right font-medium px-2 py-1.5 cursor-pointer hover:text-foreground" onClick={() => handleSort("confidence")}>
                Conf {renderSortArrow("confidence")}
              </th>
              <th className="text-center font-medium px-2 py-1.5">Risk</th>
              <th className="text-right font-medium px-2 py-1.5 cursor-pointer hover:text-foreground" onClick={() => handleSort("rr")}>
                RR {renderSortArrow("rr")}
              </th>
              <th className="text-center font-medium px-2 py-1.5">Bias</th>
              <th className="text-center font-medium px-2 py-1.5">Align</th>
              <th className="text-right font-medium px-2 py-1.5">S Dist</th>
              <th className="text-right font-medium px-2 py-1.5">R Dist</th>
              <th className="text-left font-medium px-2 py-1.5">Pattern</th>
              <th className="text-center font-medium px-2 py-1.5">Rank</th>
            </tr>
          </thead>
          <tbody>
            <AnimatePresence mode="popLayout">
              {sortedRows.map((row) => (
                <motion.tr
                  key={row.symbol}
                  layout
                  initial={{ opacity: 0 }}
                  animate={{
                    opacity: 1,
                    backgroundColor: flashSymbols.includes(row.symbol) ? "rgba(245, 158, 11, 0.15)" : undefined,
                  }}
                  exit={{ opacity: 0 }}
                  transition={{ duration: 0.2 }}
                  onClick={() => onSelectSymbol(selectedSymbol === row.symbol ? null : row.symbol)}
                  className={cn(
                    "border-b last:border-0 cursor-pointer transition-colors hover:bg-muted/20",
                    selectedSymbol === row.symbol && "bg-muted/30",
                  )}
                >
                  {/* Watchlist star */}
                  <td className="px-1 py-1">
                    <button onClick={(e) => { e.stopPropagation(); onToggleWatchlist(row.symbol) }} className="p-0.5">
                      <Star className={cn("w-2.5 h-2.5", wlSymbols.has(row.symbol) ? "text-amber-500 fill-amber-500" : "text-muted-foreground/30")} />
                    </button>
                  </td>
                  {/* Pin */}
                  <td className="px-1 py-1">
                    {wlSymbols.has(row.symbol) && (
                      <button onClick={(e) => { e.stopPropagation(); onTogglePin(row.symbol) }} className="p-0.5 text-[8px]">
                        {pinnedSymbols.has(row.symbol) ? "📌" : "📍"}
                      </button>
                    )}
                  </td>
                  <td className="px-2 py-1.5 font-medium">{row.symbol}</td>
                  <td className="px-2 py-1.5 text-right font-mono">{row.price.toFixed(2)}</td>
                  <td className="px-2 py-1.5 text-right"><ChangeCell change={row.change} /></td>
                  <td className="px-2 py-1.5 text-right font-mono text-[9px]">{row.volume.toLocaleString()}</td>
                  <td className="px-2 py-1.5 text-center"><TrendCell trend={row.trend} /></td>
                  <td className="px-2 py-1.5 text-right"><ScoreCell score={row.score} /></td>
                  <td className="px-2 py-1.5 text-right font-mono text-[10px]">{row.confidence}%</td>
                  <td className="px-2 py-1.5 text-center"><RiskCell risk={row.risk} /></td>
                  <td className="px-2 py-1.5 text-right"><RRCell rr={row.rr} /></td>
                  <td className={cn("px-2 py-1.5 text-center text-[9px] font-medium", BIAS_COLORS[row.institutionalBias] || "")}>{row.institutionalBias}</td>
                  <td className="px-2 py-1.5 text-center text-[8px]">{row.mtfAlignment}</td>
                  <td className="px-2 py-1.5 text-right font-mono text-[9px]">{row.supportDistance != null ? `${row.supportDistance.toFixed(1)}%` : "--"}</td>
                  <td className="px-2 py-1.5 text-right font-mono text-[9px]">{row.resistanceDistance != null ? `${row.resistanceDistance.toFixed(1)}%` : "--"}</td>
                  <td className="px-2 py-1.5 text-[9px]">{row.pattern || "--"}</td>
                  <td className="px-2 py-1.5"><ScannerRanking rank={row.rank} /></td>
                </motion.tr>
              ))}
            </AnimatePresence>
          </tbody>
        </table>
      </div>

      <div className="flex items-center justify-between px-3 py-1.5 border-t text-[9px] text-muted-foreground">
        <span>{rows.length} symbols</span>
        <span>Updated {new Date().toLocaleTimeString()}</span>
      </div>
    </div>
  )
}
