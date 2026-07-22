"use client"

import { SettingsSection } from "./SettingsSection"
import { ToggleCard } from "./ToggleCard"
import { SliderControl } from "./SliderControl"
import type { OverlaySettings as OverlayType } from "@/store/useSettingsStore"

interface Props {
  settings: OverlayType
  onUpdate: (p: Partial<OverlayType>) => void
}

export function OverlaySettingsPanel({ settings, onUpdate }: Props) {
  const TOGGLES = [
    { key: "supportResistance", label: "Support & Resistance" },
    { key: "supplyDemand", label: "Supply & Demand" },
    { key: "swingHighLow", label: "Swing High/Low" },
    { key: "trendlines", label: "Trendlines" },
    { key: "liquidity", label: "Liquidity" },
    { key: "bos", label: "BOS" },
    { key: "choch", label: "CHoCH" },
    { key: "aiLabels", label: "AI Labels" },
    { key: "entryZone", label: "Entry Zone" },
    { key: "targetLines", label: "Target Lines" },
    { key: "stoploss", label: "Stoploss" },
  ] as const

  return (
    <SettingsSection title="Chart Overlays" description="Configure overlay visibility and appearance">
      <div className="grid grid-cols-2 gap-1">
        {TOGGLES.map(({ key, label }) => (
          <ToggleCard key={key} label={label} checked={settings[key] as boolean} onChange={(v) => onUpdate({ [key]: v } as Partial<OverlayType>)} />
        ))}
      </div>
      <SliderControl label="Overlay Opacity" value={settings.opacity} min={10} max={100} step={10} suffix="%" onChange={(v) => onUpdate({ opacity: v })} />
      <div>
        <label className="text-[9px] text-muted-foreground block mb-0.5">Label Size</label>
        <select value={settings.labelSize} onChange={(e) => onUpdate({ labelSize: e.target.value as "sm" | "md" | "lg" })}
          className="w-full h-7 rounded border bg-muted/50 px-1.5 text-[10px] focus:outline-none">
          <option value="sm">Small</option>
          <option value="md">Medium</option>
          <option value="lg">Large</option>
        </select>
      </div>
    </SettingsSection>
  )
}
