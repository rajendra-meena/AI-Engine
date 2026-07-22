"use client"

import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, LineChart, Line, AreaChart, Area, CartesianGrid } from "recharts"
import { cn } from "@/lib/utils"
import type { AccuracyPoint } from "@/services/analyticsService"
import type { ChartType } from "@/store/useAnalyticsStore"

interface AccuracyChartProps {
  data: AccuracyPoint[]
  chartType: ChartType
  className?: string
}

// eslint-disable-next-line @typescript-eslint/no-explicit-any
function CustomTooltip({ active, payload, label }: any) {
  if (!active || !payload?.length) return null
  const d = payload[0].payload
  return (
    <div className="rounded-lg border bg-background/95 px-3 py-2 text-xs shadow-lg">
      <div className="font-medium mb-1">{label}</div>
      <div className="text-muted-foreground">Accuracy: {d.accuracy.toFixed(1)}%</div>
      <div className="text-muted-foreground">Correct: {d.correct}/{d.total}</div>
    </div>
  )
}

export function AccuracyChart({ data, chartType, className }: AccuracyChartProps) {
  if (!data.length) {
    return <div className="flex items-center justify-center h-48 text-[10px] text-muted-foreground">No accuracy data</div>
  }

  const chartData = data.slice(-30) // Last 30 periods

  if (chartType === "line") {
    return (
      <div className={cn("rounded-lg border bg-card p-3", className)}>
        <ResponsiveContainer width="100%" height={200}>
          <LineChart data={chartData}>
            <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border))" />
            <XAxis dataKey="date" tick={{ fontSize: 9 }} tickFormatter={(v) => v.slice(5)} stroke="hsl(var(--muted-foreground))" />
            <YAxis domain={[0, 100]} tick={{ fontSize: 9 }} stroke="hsl(var(--muted-foreground))" />
            <Tooltip content={<CustomTooltip />} />
            <Line type="monotone" dataKey="accuracy" stroke="#6366f1" strokeWidth={2} dot={{ r: 2 }} />
          </LineChart>
        </ResponsiveContainer>
      </div>
    )
  }

  if (chartType === "area") {
    return (
      <div className={cn("rounded-lg border bg-card p-3", className)}>
        <ResponsiveContainer width="100%" height={200}>
          <AreaChart data={chartData}>
            <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border))" />
            <XAxis dataKey="date" tick={{ fontSize: 9 }} tickFormatter={(v) => v.slice(5)} stroke="hsl(var(--muted-foreground))" />
            <YAxis domain={[0, 100]} tick={{ fontSize: 9 }} stroke="hsl(var(--muted-foreground))" />
            <Tooltip content={<CustomTooltip />} />
            <defs>
              <linearGradient id="accuracyGrad" x1="0" y1="0" x2="0" y2="1">
                <stop offset="5%" stopColor="#6366f1" stopOpacity={0.3} />
                <stop offset="95%" stopColor="#6366f1" stopOpacity={0} />
              </linearGradient>
            </defs>
            <Area type="monotone" dataKey="accuracy" stroke="#6366f1" strokeWidth={2} fill="url(#accuracyGrad)" />
          </AreaChart>
        </ResponsiveContainer>
      </div>
    )
  }

  // Bar chart (default)
  return (
    <div className={cn("rounded-lg border bg-card p-3", className)}>
      <ResponsiveContainer width="100%" height={200}>
        <BarChart data={chartData}>
          <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border))" />
          <XAxis dataKey="date" tick={{ fontSize: 9 }} tickFormatter={(v) => v.slice(5)} stroke="hsl(var(--muted-foreground))" />
          <YAxis domain={[0, 100]} tick={{ fontSize: 9 }} stroke="hsl(var(--muted-foreground))" />
          <Tooltip content={<CustomTooltip />} />
          <Bar dataKey="accuracy" fill="#6366f1" radius={[2, 2, 0, 0]} />
        </BarChart>
      </ResponsiveContainer>
    </div>
  )
}
