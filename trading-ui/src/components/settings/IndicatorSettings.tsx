"use client"

import { SettingsSection } from "./SettingsSection"
import { ToggleCard } from "./ToggleCard"
import { SliderControl } from "./SliderControl"
import type { IndicatorSettings as IndicatorType } from "@/store/useSettingsStore"

interface Props {
  settings: IndicatorType
  onUpdate: (p: Partial<IndicatorType>) => void
}

export function IndicatorSettingsPanel({ settings, onUpdate }: Props) {
  const INDICATORS = [
    { key: "ema", label: "EMA" }, { key: "sma", label: "SMA" }, { key: "rsi", label: "RSI" },
    { key: "macd", label: "MACD" }, { key: "atr", label: "ATR" }, { key: "adx", label: "ADX" },
    { key: "vwap", label: "VWAP" }, { key: "supertrend", label: "SuperTrend" },
  ] as const

  return (
    <SettingsSection title="Indicators" description="Enable/disable indicators and configure defaults">
      <div className="grid grid-cols-2 gap-1">
        {INDICATORS.map(({ key, label }) => (
          <ToggleCard key={key} label={label} checked={settings[key] as boolean} onChange={(v) => onUpdate({ [key]: v } as Partial<IndicatorType>)} />
        ))}
      </div>
      <SliderControl label="Line Width" value={settings.lineWidth} min={1} max={5} onChange={(v) => onUpdate({ lineWidth: v })} />
      <SliderControl label="Opacity" value={settings.opacity} min={10} max={100} step={10} suffix="%" onChange={(v) => onUpdate({ opacity: v })} />
      <ToggleCard label="Default Visibility" description="Show indicators by default on new charts" checked={settings.defaultVisible} onChange={(v) => onUpdate({ defaultVisible: v })} />
    </SettingsSection>
  )
}
