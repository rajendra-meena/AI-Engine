"use client"

import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid } from "recharts"
import { cn } from "@/lib/utils"
import type { ConfidenceBin } from "@/services/analyticsService"

interface ConfidenceChartProps {
  data: ConfidenceBin[]
  className?: string
}

export function ConfidenceChart({ data, className }: ConfidenceChartProps) {
  if (!data.length) {
    return <div className="flex items-center justify-center h-48 text-[10px] text-muted-foreground">No confidence data</div>
  }

  const chartData = data.map((d) => ({
    ...d,
    name: d.label,
    fill: d.accuracy >= 60 ? "#22c55e" : d.accuracy >= 40 ? "#f59e0b" : "#ef4444",
  }))

  return (
    <div className={cn("rounded-lg border bg-card p-3", className)}>
      <ResponsiveContainer width="100%" height={200}>
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
                <div className="font-medium mb-1">Confidence {d.label}</div>
                <div className="text-muted-foreground">Accuracy: {d.accuracy.toFixed(1)}%</div>
                <div className="text-muted-foreground">Predictions: {d.predictions}</div>
                <div className="text-muted-foreground">Correct: {d.correct}</div>
              </div>
            )
          }} />
          <Bar dataKey="accuracy" radius={[2, 2, 0, 0]} fill="var(--bar-fill, #6366f1)">
            {chartData.map((entry, i) => (
              <rect key={i} fill={entry.fill} />
            ))}
          </Bar>
        </BarChart>
      </ResponsiveContainer>

      {/* Summary grid */}
      <div className="grid grid-cols-5 gap-1 mt-2">
        {data.map((bin, i) => (
          <div key={i} className="text-center p-1 rounded bg-muted/20">
            <div className="text-[8px] text-muted-foreground">{bin.label}</div>
            <div className={cn("text-[10px] font-mono font-bold", bin.accuracy >= 60 ? "text-emerald-500" : bin.accuracy >= 40 ? "text-amber-500" : "text-red-500")}>
              {bin.accuracy.toFixed(0)}%
            </div>
            <div className="text-[7px] text-muted-foreground">{bin.predictions} pred</div>
          </div>
        ))}
      </div>
    </div>
  )
}
