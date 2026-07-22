"use client"

import { SettingsSection } from "./SettingsSection"
import { ToggleCard } from "./ToggleCard"
import { SliderControl } from "./SliderControl"
import type { ScannerSettings as ScannerType } from "@/store/useSettingsStore"

interface Props {
  settings: ScannerType
  onUpdate: (p: Partial<ScannerType>) => void
}

export function ScannerSettingsPanel({ settings, onUpdate }: Props) {
  return (
    <SettingsSection title="Scanner" description="Market scanner defaults">
      <SliderControl label="Refresh Interval (s)" value={settings.refreshInterval} min={10} max={300} step={5} suffix="s" onChange={(v) => onUpdate({ refreshInterval: v })} />
      <SliderControl label="Min Score" value={settings.minScore} min={0} max={100} onChange={(v) => onUpdate({ minScore: v })} />
      <SliderControl label="Min Confidence %" value={settings.minConfidence} min={0} max={100} suffix="%" onChange={(v) => onUpdate({ minConfidence: v })} />
      <SliderControl label="Min RR" value={settings.minRR} min={0} max={5} step={0.5} onChange={(v) => onUpdate({ minRR: v })} />
      <div>
        <label className="text-[9px] text-muted-foreground block mb-0.5">Default Sort</label>
        <select value={settings.defaultSort} onChange={(e) => onUpdate({ defaultSort: e.target.value })}
          className="w-full h-7 rounded border bg-muted/50 px-1.5 text-[10px] focus:outline-none">
          <option value="score">Score</option>
          <option value="confidence">Confidence</option>
          <option value="rr">RR</option>
          <option value="volume">Volume</option>
        </select>
      </div>
      <ToggleCard label="Alert Rules" description="Enable scanner alert rules" checked={settings.alertRules} onChange={(v) => onUpdate({ alertRules: v })} />
    </SettingsSection>
  )
}
