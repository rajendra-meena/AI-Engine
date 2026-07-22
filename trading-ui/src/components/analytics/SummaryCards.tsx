"use client"

import { MetricCard } from "./MetricCard"
import { PerformanceBadge } from "./PerformanceBadge"
import { Target, TrendingUp, TrendingDown, BarChart3, Percent, Award, DollarSign, Activity, ShieldAlert } from "lucide-react"
import type { SummaryMetrics } from "@/services/analyticsService"

interface SummaryCardsProps {
  metrics: SummaryMetrics
}

export function SummaryCards({ metrics }: SummaryCardsProps) {
  return (
    <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 gap-2">
      <MetricCard label="Total Predictions" value={metrics.totalPredictions} icon={<Target className="w-3.5 h-3.5" />} />
      <MetricCard label="Win Rate" value={metrics.winRate.toFixed(1)} suffix="%" color={metrics.winRate >= 50 ? "bullish" : "bearish"} icon={<Percent className="w-3.5 h-3.5" />} />
      <MetricCard label="Correct" value={metrics.correct} color="bullish" icon={<TrendingUp className="w-3.5 h-3.5" />} />
      <MetricCard label="Wrong" value={metrics.wrong} color="bearish" icon={<TrendingDown className="w-3.5 h-3.5" />} />

      <MetricCard label="Avg Score" value={metrics.avgScore.toFixed(0)} icon={<BarChart3 className="w-3.5 h-3.5" />} />
      <MetricCard label="Avg Confidence" value={metrics.avgConfidence.toFixed(0)} suffix="%" color={metrics.avgConfidence >= 60 ? "bullish" : "warning"} icon={<Award className="w-3.5 h-3.5" />} />
      <MetricCard label="Avg RR" value={metrics.avgRR.toFixed(1)} icon={<Activity className="w-3.5 h-3.5" />} />
      <MetricCard label="Profit Factor" value={metrics.profitFactor.toFixed(2)} color={metrics.profitFactor >= 1 ? "bullish" : "bearish"} icon={<DollarSign className="w-3.5 h-3.5" />} />

      <MetricCard label="Expectancy" value={metrics.expectancy.toFixed(0)} color={metrics.expectancy >= 0 ? "bullish" : "bearish"} icon={<Activity className="w-3.5 h-3.5" />} />
      <MetricCard label="Max Drawdown" value={metrics.maxDrawdown.toFixed(1)} suffix="%" color="warning" icon={<ShieldAlert className="w-3.5 h-3.5" />} />
      <MetricCard label="Current Accuracy" value={metrics.currentAccuracy.toFixed(1)} suffix="%" color={metrics.currentAccuracy >= 50 ? "bullish" : "bearish"} icon={<Activity className="w-3.5 h-3.5" />} />
      <MetricCard label="Checked" value={metrics.totalChecked} icon={<BarChart3 className="w-3.5 h-3.5" />} />

      {metrics.largestWin > 0 && (
        <div className="col-span-2 flex items-center gap-2">
          <PerformanceBadge value={metrics.largestWin} label="Largest Win" />
          <PerformanceBadge value={metrics.largestLoss} label="Largest Loss" invert />
        </div>
      )}
    </div>
  )
}
