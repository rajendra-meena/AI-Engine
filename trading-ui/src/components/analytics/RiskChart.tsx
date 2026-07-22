"use client"

import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid } from "recharts"
import { cn } from "@/lib/utils"
import type { RiskBin } from "@/services/analyticsService"

interface RiskChartProps {
  data: RiskBin[]
  className?: string
}

const RISK_COLORS: Record<string, string> = {
  LOW: "#22c55e",
  MEDIUM: "#f59e0b",
  HIGH: "#ef4444",
  EXTREME: "#dc2626",
}

export function RiskChart({ data, className }: RiskChartProps) {
  if (!data.length) {
    return <div className="flex items-center justify-center h-48 text-[10px] text-muted-foreground">No risk data</div>
  }

  const chartData = data
    .filter((d) => d.count > 0)
    .map((d) => ({
      ...d,
      name: d.level,
      winRate: d.count > 0 ? (d.wins / d.count) * 100 : 0,
      fill: RISK_COLORS[d.level] || "#888",
    }))

  return (
    <div className={cn("rounded-lg border bg-card p-3", className)}>
      <ResponsiveContainer width="100%" height={180}>
        <BarChart data={chartData}>
          <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border))" />
          <XAxis dataKey="name" tick={{ fontSize: 9 }} stroke="hsl(var(--muted-foreground))" />
          <YAxis domain={[0, 100]} tick={{ fontSize: 9 }} stroke="hsl(var(--muted-foreground))" />
          {/* eslint-disable-next-line @typescript-eslint/no-explicit-any */}
          <Tooltip content={({ active, payload }: any) => {
            if (!active || !payload?.length) return null
            const d = payload[0].payload
            return (
              <div className="rounded-lg border bg-background/95 px-3 py-2 text-xs shadow-lg">
                <div className="font-medium mb-1">{d.level} Risk</div>
                <div className="text-muted-foreground">Count: {d.count}</div>
                <div className="text-muted-foreground">Wins: {d.wins} / Losses: {d.losses}</div>
                <div className="text-muted-foreground">Win Rate: {d.winRate.toFixed(1)}%</div>
                <div className="text-muted-foreground">Avg Gain: {d.avgGain.toFixed(0)}</div>
                <div className="text-muted-foreground">Avg Loss: {d.avgLoss.toFixed(0)}</div>
              </div>
            )
          }} />
          <Bar dataKey="winRate" radius={[2, 2, 0, 0]} fill="var(--bar-fill, #6366f1)" />
        </BarChart>
      </ResponsiveContainer>

      {/* Detail grid */}
      <div className="grid grid-cols-4 gap-1 mt-2">
        {data.filter((d) => d.count > 0).map((bin, i) => (
          <div key={i} className="text-center p-1 rounded bg-muted/20">
            <div className="text-[8px] font-medium uppercase" style={{ color: RISK_COLORS[bin.level] }}>{bin.level}</div>
            <div className="text-[10px] font-mono font-bold">{bin.count}</div>
            <div className="text-[7px] text-muted-foreground">
              W: {bin.wins} L: {bin.losses}
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}
