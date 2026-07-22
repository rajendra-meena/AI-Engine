"use client"

import { SettingsSection } from "./SettingsSection"
import { ToggleCard } from "./ToggleCard"
import type { ChartSettings as ChartType } from "@/store/useSettingsStore"

interface Props {
  settings: ChartType
  onUpdate: (p: Partial<ChartType>) => void
}

export function ChartSettingsPanel({ settings, onUpdate }: Props) {
  return (
    <SettingsSection title="Chart" description="Default chart behavior">
      <div className="grid grid-cols-2 gap-2">
        <div>
          <label className="text-[9px] text-muted-foreground block mb-0.5">Default Symbol</label>
          <input type="text" value={settings.defaultSymbol} onChange={(e) => onUpdate({ defaultSymbol: e.target.value })}
            className="w-full h-7 rounded border bg-muted/50 px-1.5 text-[10px] font-mono focus:outline-none" />
        </div>
        <div>
          <label className="text-[9px] text-muted-foreground block mb-0.5">Default Interval</label>
          <select value={settings.defaultInterval} onChange={(e) => onUpdate({ defaultInterval: e.target.value })}
            className="w-full h-7 rounded border bg-muted/50 px-1.5 text-[10px] focus:outline-none">
            {["1m","3m","5m","15m","30m","60m","4h","1d"].map((tf) => <option key={tf} value={tf}>{tf}</option>)}
          </select>
        </div>
        <div>
          <label className="text-[9px] text-muted-foreground block mb-0.5">Price Scale</label>
          <select value={settings.priceScale} onChange={(e) => onUpdate({ priceScale: e.target.value as "normal" | "log" })}
            className="w-full h-7 rounded border bg-muted/50 px-1.5 text-[10px] focus:outline-none">
            <option value="normal">Normal</option>
            <option value="log">Logarithmic</option>
          </select>
        </div>
        <div>
          <label className="text-[9px] text-muted-foreground block mb-0.5">Timezone</label>
          <select value={settings.timezone} onChange={(e) => onUpdate({ timezone: e.target.value })}
            className="w-full h-7 rounded border bg-muted/50 px-1.5 text-[10px] focus:outline-none">
            <option value="Asia/Kolkata">IST</option>
            <option value="UTC">UTC</option>
            <option value="America/New_York">EST</option>
          </select>
        </div>
      </div>
      <ToggleCard label="Crosshair" description="Show crosshair on hover" checked={settings.crosshair} onChange={(v) => onUpdate({ crosshair: v })} />
      <ToggleCard label="Grid" description="Show grid lines" checked={settings.grid} onChange={(v) => onUpdate({ grid: v })} />
      <ToggleCard label="Volume" description="Show volume bars" checked={settings.volume} onChange={(v) => onUpdate({ volume: v })} />
      <ToggleCard label="Auto Scale" description="Auto fit chart to data" checked={settings.autoScale} onChange={(v) => onUpdate({ autoScale: v })} />
      <ToggleCard label="Right Scale" description="Show right price scale" checked={settings.rightScale} onChange={(v) => onUpdate({ rightScale: v })} />
    </SettingsSection>
  )
}
