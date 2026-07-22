"use client"

interface ReplayStatisticsProps {
  processedCandles: number
  totalCandles: number
  elapsedSeconds: number
  speed: number
  progressPercent: number
  decisions: number
  trades: number
  winRate: number | null
}

function StatRow({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex items-center justify-between py-0.5">
      <span className="text-[9px] text-muted-foreground">{label}</span>
      <span className="text-[10px] font-mono font-medium">{value}</span>
    </div>
  )
}

function formatDuration(seconds: number): string {
  const h = Math.floor(seconds / 3600)
  const m = Math.floor((seconds % 3600) / 60)
  const s = Math.floor(seconds % 60)
  if (h > 0) return `${h}h ${m}m`
  if (m > 0) return `${m}m ${s}s`
  return `${s}s`
}

export function ReplayStatistics({
  processedCandles, totalCandles, elapsedSeconds, speed,
  progressPercent, decisions, trades, winRate,
}: ReplayStatisticsProps) {
  const remainingSeconds = speed > 0 && totalCandles > 0
    ? (totalCandles - processedCandles) / Math.max(1, processedCandles / Math.max(1, elapsedSeconds))
    : 0

  return (
    <div className="rounded-md border bg-card p-2 space-y-0.5">
      <div className="text-[9px] font-medium text-muted-foreground uppercase tracking-wider mb-1">Statistics</div>
      <StatRow label="Processed Candles" value={processedCandles.toLocaleString()} />
      <StatRow label="Total Candles" value={totalCandles.toLocaleString()} />
      <StatRow label="Elapsed" value={formatDuration(elapsedSeconds)} />
      <StatRow label="Remaining" value={formatDuration(remainingSeconds)} />
      <StatRow label="Speed" value={`${speed}x`} />
      <StatRow label="Progress" value={`${progressPercent.toFixed(1)}%`} />
      <StatRow label="AI Decisions" value={decisions.toLocaleString()} />
      <StatRow label="Trades" value={trades.toLocaleString()} />
      <StatRow label="Win Rate" value={winRate != null ? `${winRate.toFixed(1)}%` : "--"} />
    </div>
  )
}
