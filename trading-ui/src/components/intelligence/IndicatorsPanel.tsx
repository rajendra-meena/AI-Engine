"use client"

import { useIndicators } from "@/hooks/useIndicators"
import { MetricCard } from "./MetricCard"
import { Skeleton } from "@/components/ui/skeleton"
import { AlertCircle, RefreshCw } from "lucide-react"

export function IndicatorsPanel() {
  const { data, isLoading, error, refetch } = useIndicators()

  if (isLoading) return <div className="space-y-2 p-3"><Skeleton className="h-3 w-full" /><Skeleton className="h-3 w-5/6" /><Skeleton className="h-3 w-4/6" /></div>
  if (error) return <div className="p-3 text-[10px] text-red-500 flex items-center gap-2"><AlertCircle className="w-3 h-3" /> Failed <button onClick={() => refetch()}><RefreshCw className="w-3 h-3" /></button></div>
  if (!data) return <div className="p-3 text-[10px] text-muted-foreground">No indicator data</div>

  const rsi = data.rsi_14
  const macdHist = data.macd_histogram

  return (
    <div className="space-y-1.5">
      <div className="text-[9px] font-medium text-muted-foreground uppercase tracking-wider mb-1">Moving Averages</div>
      <MetricCard label="EMA 9" value={data.ema_9?.toFixed(2)} trend={data.ema_9 && data.candle_close ? (data.candle_close > data.ema_9 ? "up" : "down") : undefined} />
      <MetricCard label="EMA 20" value={data.ema_20?.toFixed(2)} trend={data.ema_20 && data.candle_close ? (data.candle_close > data.ema_20 ? "up" : "down") : undefined} />
      <MetricCard label="EMA 50" value={data.ema_50?.toFixed(2)} trend={data.ema_20 && data.ema_50 ? (data.ema_20 > data.ema_50 ? "up" : "down") : undefined} />
      <MetricCard label="EMA 200" value={data.ema_200?.toFixed(2)} />
      <MetricCard label="SMA 20" value={data.sma_20?.toFixed(2)} />
      <MetricCard label="SMA 50" value={data.sma_50?.toFixed(2)} />
      <div className="border-t my-1.5" />
      <div className="text-[9px] font-medium text-muted-foreground uppercase tracking-wider mb-1">Oscillators</div>
      <MetricCard label="RSI (14)" value={data.rsi_14?.toFixed(1)} trend={rsi != null ? (rsi > 50 ? "up" : "down") : undefined} valueClass={rsi != null ? (rsi > 70 ? "text-red-500" : rsi > 60 ? "text-emerald-500" : rsi < 30 ? "text-emerald-500" : "") : undefined} />
      <MetricCard label="MACD" value={data.macd?.toFixed(2)} trend={macdHist != null ? (macdHist > 0 ? "up" : "down") : undefined} />
      <MetricCard label="Signal" value={data.macd_signal?.toFixed(2)} />
      <MetricCard label="Histogram" value={data.macd_histogram?.toFixed(2)} trend={macdHist != null ? (macdHist > 0 ? "up" : "down") : undefined} valueClass={macdHist != null ? (macdHist > 0 ? "text-emerald-500" : "text-red-500") : undefined} />
      <MetricCard label="ADX (14)" value={data.adx_14?.toFixed(1)} trend={data.adx_14 != null ? (data.adx_14 > 25 ? "up" : "down") : undefined} valueClass={data.adx_14 != null ? (data.adx_14 > 25 ? "text-emerald-500" : "text-amber-500") : undefined} />
      <div className="border-t my-1.5" />
      <div className="text-[9px] font-medium text-muted-foreground uppercase tracking-wider mb-1">Volatility</div>
      <MetricCard label="ATR (14)" value={data.atr_14?.toFixed(2)} />
      <MetricCard label="VWAP" value={data.vwap?.toFixed(2)} trend={data.vwap && data.candle_close ? (data.candle_close > data.vwap ? "up" : "down") : undefined} />
      <MetricCard label="SuperTrend" value={data.supertrend_trend || "N/A"} />
    </div>
  )
}
