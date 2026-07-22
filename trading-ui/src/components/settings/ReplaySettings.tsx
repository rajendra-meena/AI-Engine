"use client"

import { SettingsSection } from "./SettingsSection"
import { ToggleCard } from "./ToggleCard"
import { SliderControl } from "./SliderControl"
import type { ReplaySettings as ReplayType } from "@/store/useSettingsStore"

interface Props {
  settings: ReplayType
  onUpdate: (p: Partial<ReplayType>) => void
}

export function ReplaySettingsPanel({ settings, onUpdate }: Props) {
  return (
    <SettingsSection title="Replay" description="Historical replay defaults">
      <SliderControl label="Default Speed" value={settings.defaultSpeed} min={1} max={100} step={1} suffix="x" onChange={(v) => onUpdate({ defaultSpeed: v })} />
      <SliderControl label="Default Days" value={settings.defaultDays} min={1} max={365} step={5} suffix="d" onChange={(v) => onUpdate({ defaultDays: v })} />
      <div>
        <label className="text-[9px] text-muted-foreground block mb-0.5">Default Interval</label>
        <select value={settings.defaultInterval} onChange={(e) => onUpdate({ defaultInterval: e.target.value })}
          className="w-full h-7 rounded border bg-muted/50 px-1.5 text-[10px] focus:outline-none">
          {["1m","3m","5m","15m","30m","60m"].map((tf) => <option key={tf} value={tf}>{tf}</option>)}
        </select>
      </div>
      <ToggleCard label="Auto Pause" description="Pause replay after each candle" checked={settings.autoPause} onChange={(v) => onUpdate({ autoPause: v })} />
      <ToggleCard label="Show Timeline" description="Display timeline during replay" checked={settings.showTimeline} onChange={(v) => onUpdate({ showTimeline: v })} />
      <ToggleCard label="Show Journal" description="Display AI decision journal" checked={settings.showJournal} onChange={(v) => onUpdate({ showJournal: v })} />
    </SettingsSection>
  )
}
