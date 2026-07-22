"use client"

import { SettingsSection } from "./SettingsSection"
import { SliderControl } from "./SliderControl"
import type { TradePlannerSettings as TradePlannerType } from "@/store/useSettingsStore"

interface Props {
  settings: TradePlannerType
  onUpdate: (p: Partial<TradePlannerType>) => void
}

export function TradePlannerSettingsPanel({ settings, onUpdate }: Props) {
  return (
    <SettingsSection title="Trade Planner" description="Default trade planning parameters">
      <div className="grid grid-cols-2 gap-2">
        <div>
          <label className="text-[9px] text-muted-foreground block mb-0.5">Default Capital (₹)</label>
          <input type="number" value={settings.defaultCapital} onChange={(e) => onUpdate({ defaultCapital: Number(e.target.value) })}
            className="w-full h-7 rounded border bg-muted/50 px-1.5 text-[10px] font-mono focus:outline-none" />
        </div>
        <div>
          <label className="text-[9px] text-muted-foreground block mb-0.5">Currency</label>
          <select value={settings.currency} onChange={(e) => onUpdate({ currency: e.target.value })}
            className="w-full h-7 rounded border bg-muted/50 px-1.5 text-[10px] focus:outline-none">
            <option value="INR">INR (₹)</option>
            <option value="USD">USD ($)</option>
            <option value="EUR">EUR (€)</option>
          </select>
        </div>
        <div>
          <label className="text-[9px] text-muted-foreground block mb-0.5">Position Sizing</label>
          <select value={settings.positionSizingMode} onChange={(e) => onUpdate({ positionSizingMode: e.target.value as "fixed" | "risk-based" | "kelly" })}
            className="w-full h-7 rounded border bg-muted/50 px-1.5 text-[10px] focus:outline-none">
            <option value="risk-based">Risk Based</option>
            <option value="fixed">Fixed</option>
            <option value="kelly">Kelly Criterion</option>
          </select>
        </div>
      </div>
      <SliderControl label="Risk %" value={settings.riskPercent} min={0.5} max={10} step={0.5} suffix="%" onChange={(v) => onUpdate({ riskPercent: v })} />
      <SliderControl label="Brokerage %" value={settings.brokerage} min={0} max={1} step={0.01} suffix="%" onChange={(v) => onUpdate({ brokerage: v })} />
      <SliderControl label="Slippage (pts)" value={settings.slippage} min={0} max={5} step={0.5} onChange={(v) => onUpdate({ slippage: v })} />
      <SliderControl label="Min RR Preference" value={settings.rrPreference} min={0.5} max={5} step={0.5} onChange={(v) => onUpdate({ rrPreference: v })} />
    </SettingsSection>
  )
}
