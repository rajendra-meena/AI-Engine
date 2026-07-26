"use client"

export function MetricCard({ label, value, sub, color }: {
  label: string
  value: string
  sub?: string
  color?: string
}) {
  return (
    <div className="rounded-lg border bg-card p-3">
      <div className="text-[9px] text-muted-foreground uppercase tracking-wider">{label}</div>
      <div className={`text-lg font-bold font-mono mt-0.5 ${color || ""}`}>{value}</div>
      {sub && <div className="text-[9px] text-muted-foreground mt-0.5">{sub}</div>}
    </div>
  )
}
