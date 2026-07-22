"use client"

import { X } from "lucide-react"
import type { StrategyCondition as SC, ConditionType, ComparisonOperator } from "@/store/useStrategyStore"

interface StrategyConditionProps {
  condition: SC
  index: number
  onChange: (index: number, update: Partial<SC>) => void
  onRemove: (index: number) => void
}

const CONDITION_OPTIONS: { value: ConditionType; label: string; group: string }[] = [
  { value: "ema_cross", label: "EMA Cross", group: "Moving Averages" },
  { value: "ema_above", label: "EMA Above", group: "Moving Averages" },
  { value: "ema_below", label: "EMA Below", group: "Moving Averages" },
  { value: "sma_cross", label: "SMA Cross", group: "Moving Averages" },
  { value: "vwap_above", label: "VWAP Above", group: "Volume" },
  { value: "vwap_below", label: "VWAP Below", group: "Volume" },
  { value: "rsi_above", label: "RSI Above", group: "Oscillators" },
  { value: "rsi_below", label: "RSI Below", group: "Oscillators" },
  { value: "rsi_overbought", label: "RSI Overbought", group: "Oscillators" },
  { value: "rsi_oversold", label: "RSI Oversold", group: "Oscillators" },
  { value: "macd_cross", label: "MACD Cross", group: "Oscillators" },
  { value: "adx_above", label: "ADX Above", group: "Trend" },
  { value: "supertrend_up", label: "SuperTrend Up", group: "Trend" },
  { value: "volume_spike", label: "Volume Spike", group: "Volume" },
  { value: "bos_bullish", label: "BOS Bullish", group: "Structure" },
  { value: "bos_bearish", label: "BOS Bearish", group: "Structure" },
  { value: "choch_bullish", label: "CHoCH Bullish", group: "Structure" },
  { value: "liquidity_sweep", label: "Liquidity Sweep", group: "Structure" },
  { value: "supply_zone", label: "Supply Zone", group: "S/R" },
  { value: "demand_zone", label: "Demand Zone", group: "S/R" },
  { value: "support", label: "Support", group: "S/R" },
  { value: "resistance", label: "Resistance", group: "S/R" },
  { value: "pattern_detected", label: "Pattern Detected", group: "Patterns" },
  { value: "bias_bullish", label: "Bullish Bias", group: "AI" },
  { value: "ai_score_above", label: "AI Score Above", group: "AI" },
  { value: "ai_confidence_above", label: "AI Conf Above", group: "AI" },
  { value: "trend_up", label: "Trend Up", group: "Market" },
  { value: "trend_down", label: "Trend Down", group: "Market" },
  { value: "volatility_high", label: "High Volatility", group: "Market" },
  { value: "gap_up", label: "Gap Up", group: "Price" },
  { value: "gap_down", label: "Gap Down", group: "Price" },
  { value: "session", label: "Session", group: "Time" },
]

const OPERATORS: ComparisonOperator[] = [">", ">=", "<", "<=", "==", "!="]

export function StrategyCondition({ condition, index, onChange, onRemove }: StrategyConditionProps) {
  return (
    <div className="flex items-center gap-1.5 py-0.5 group">
      {index === 0 && <span className="text-[8px] text-muted-foreground w-6">IF</span>}
      {index > 0 && (
        <select
          value={condition.operator}
          onChange={(e) => onChange(index, { operator: e.target.value as ComparisonOperator })}
          className="w-12 h-6 rounded border bg-muted/30 text-[8px] font-mono focus:outline-none"
        >
          <option value="AND">AND</option>
          <option value="OR">OR</option>
          <option value="NOT">NOT</option>
        </select>
      )}

      <select
        value={condition.type}
        onChange={(e) => onChange(index, { type: e.target.value as ConditionType })}
        className="h-6 rounded border bg-muted/50 px-1 text-[9px] font-mono focus:outline-none flex-1"
      >
        {CONDITION_OPTIONS.map((opt) => (
          <option key={opt.value} value={opt.value}>{opt.label}</option>
        ))}
      </select>

      <select
        value={condition.operator as string}
        onChange={(e) => onChange(index, { operator: e.target.value as ComparisonOperator })}
        className="h-6 w-12 rounded border bg-muted/30 text-[9px] font-mono focus:outline-none"
      >
        {OPERATORS.map((op) => <option key={op} value={op}>{op}</option>)}
      </select>

      <input
        type="number"
        value={condition.value as number}
        onChange={(e) => onChange(index, { value: Number(e.target.value) })}
        className="h-6 w-16 rounded border bg-muted/50 px-1 text-[9px] font-mono focus:outline-none"
      />

      <button onClick={() => onRemove(index)} className="p-0.5 opacity-0 group-hover:opacity-100 text-muted-foreground hover:text-red-500 transition-all">
        <X className="w-3 h-3" />
      </button>
    </div>
  )
}
