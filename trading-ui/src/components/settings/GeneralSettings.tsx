"use client"

import { SettingsSection } from "./SettingsSection"
import { ToggleCard } from "./ToggleCard"
import type { GeneralSettings as GeneralType } from "@/store/useSettingsStore"

interface Props {
  settings: GeneralType
  onUpdate: (p: Partial<GeneralType>) => void
}

export function GeneralSettingsPanel({ settings, onUpdate }: Props) {
  return (
    <SettingsSection title="General" description="Application preferences">
      <div className="grid grid-cols-2 gap-2">
        <div>
          <label className="text-[9px] text-muted-foreground block mb-0.5">Timezone</label>
          <select value={settings.timezone} onChange={(e) => onUpdate({ timezone: e.target.value })}
            className="w-full h-7 rounded border bg-muted/50 px-1.5 text-[10px] focus:outline-none">
            <option value="Asia/Kolkata">Asia/Kolkata (IST)</option>
            <option value="America/New_York">America/New_York (EST)</option>
            <option value="Europe/London">Europe/London (GMT)</option>
            <option value="UTC">UTC</option>
          </select>
        </div>
        <div>
          <label className="text-[9px] text-muted-foreground block mb-0.5">Date Format</label>
          <select value={settings.dateFormat} onChange={(e) => onUpdate({ dateFormat: e.target.value as "12h" | "24h" })}
            className="w-full h-7 rounded border bg-muted/50 px-1.5 text-[10px] focus:outline-none">
            <option value="12h">12-hour</option>
            <option value="24h">24-hour</option>
          </select>
        </div>
        <div>
          <label className="text-[9px] text-muted-foreground block mb-0.5">Number Format</label>
          <select value={settings.numberFormat} onChange={(e) => onUpdate({ numberFormat: e.target.value as "en-IN" | "en-US" })}
            className="w-full h-7 rounded border bg-muted/50 px-1.5 text-[10px] focus:outline-none">
            <option value="en-IN">Indian (IN)</option>
            <option value="en-US">US Format</option>
          </select>
        </div>
      </div>
      <ToggleCard label="Auto Save" description="Automatically save settings changes" checked={settings.autoSave} onChange={(v) => onUpdate({ autoSave: v })} />
      <ToggleCard label="Auto Update" description="Automatically check for updates" checked={settings.autoUpdate} onChange={(v) => onUpdate({ autoUpdate: v })} />
    </SettingsSection>
  )
}
