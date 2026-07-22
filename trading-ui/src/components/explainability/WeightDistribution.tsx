"use client"

import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid } from "recharts"
import type { ScoreContribution } from "@/services/explainabilityService"

interface WeightDistributionProps {
  items: ScoreContribution[]
}

export function WeightDistribution({ items }: WeightDistributionProps) {
  const data = items.map((i) => ({ name: i.label, weight: i.weight, value: i.value, fill: i.color }))

  return (
    <div className="rounded-lg border bg-card p-3 space-y-2">
      <div className="text-[9px] font-medium text-muted-foreground uppercase tracking-wider">Weight Distribution</div>
      <ResponsiveContainer width="100%" height={180}>
        <BarChart data={data}>
          <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border))" />
          <XAxis dataKey="name" tick={{ fontSize: 8 }} stroke="hsl(var(--muted-foreground))" />
          <YAxis tick={{ fontSize: 8 }} stroke="hsl(var(--muted-foreground))" />
          {/* eslint-disable-next-line @typescript-eslint/no-explicit-any */}
          <Tooltip content={({ active, payload }: any) => {
            if (!active || !payload?.length) return null
            const d = payload[0].payload
            return <div className="rounded border bg-background/95 px-2 py-1 text-[10px] shadow-lg"><b>{d.name}</b>: {d.weight}% weight · {d.value} value</div>
          }} />
          <Bar dataKey="weight" radius={[2, 2, 0, 0]} fill="#6366f1" />
        </BarChart>
      </ResponsiveContainer>
    </div>
  )
}
