"use client"

import { SettingsSection } from "./SettingsSection"
import { ToggleCard } from "./ToggleCard"
import { SliderControl } from "./SliderControl"
import type { RiskSettings as RiskType } from "@/store/useSettingsStore"

interface Props {
  settings: RiskType
  onUpdate: (p: Partial<RiskType>) => void
}

export function RiskSettingsPanel({ settings, onUpdate }: Props) {
  return (
    <SettingsSection title="Risk Management" description="Global risk parameters">
      <SliderControl label="Max Daily Loss (₹)" value={settings.maxDailyLoss} min={1000} max={100000} step={1000} onChange={(v) => onUpdate({ maxDailyLoss: v })} />
      <SliderControl label="Max Weekly Loss (₹)" value={settings.maxWeeklyLoss} min={5000} max={500000} step={5000} onChange={(v) => onUpdate({ maxWeeklyLoss: v })} />
      <SliderControl label="Max Open Positions" value={settings.maxOpenPositions} min={1} max={20} onChange={(v) => onUpdate({ maxOpenPositions: v })} />
      <SliderControl label="Max Exposure %" value={settings.maxExposure} min={10} max={100} step={5} suffix="%" onChange={(v) => onUpdate({ maxExposure: v })} />
      <SliderControl label="Max Drawdown %" value={settings.maxDrawdown} min={5} max={50} suffix="%" onChange={(v) => onUpdate({ maxDrawdown: v })} />
      <SliderControl label="Trade Cooldown (s)" value={settings.tradeCooldown} min={0} max={3600} step={30} suffix="s" onChange={(v) => onUpdate({ tradeCooldown: v })} />
      <ToggleCard label="Stop Trading on Max Loss" description="Automatically stop trading when limits are hit" checked={settings.stopTrading} onChange={(v) => onUpdate({ stopTrading: v })} />
    </SettingsSection>
  )
}
