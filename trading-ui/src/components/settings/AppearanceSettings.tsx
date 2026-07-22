"use client"

import { SettingsSection } from "./SettingsSection"
import { ToggleCard } from "./ToggleCard"
import { ColorPicker } from "./ColorPicker"
import type { AppearanceSettings as AppearanceType } from "@/store/useSettingsStore"

interface Props {
  settings: AppearanceType
  onUpdate: (p: Partial<AppearanceType>) => void
}

export function AppearanceSettingsPanel({ settings, onUpdate }: Props) {
  return (
    <SettingsSection title="Appearance" description="Customize the look and feel">
      {/* Theme */}
      <div>
        <label className="text-[9px] text-muted-foreground block mb-0.5">Theme</label>
        <div className="flex gap-1">
          {["light", "dark", "system"].map((t) => (
            <button key={t} onClick={() => onUpdate({ theme: t as "light" | "dark" | "system" })}
              className={`flex-1 h-7 rounded text-[10px] font-medium transition-colors ${settings.theme === t ? "bg-primary/20 text-primary" : "bg-muted/30 text-muted-foreground hover:bg-accent"}`}>
              {t.charAt(0).toUpperCase() + t.slice(1)}
            </button>
          ))}
        </div>
      </div>

      <ColorPicker label="Accent Color" value={settings.accentColor} onChange={(c) => onUpdate({ accentColor: c })} />

      <div className="grid grid-cols-2 gap-2">
        <div>
          <label className="text-[9px] text-muted-foreground block mb-0.5">Font Size</label>
          <select value={settings.fontSize} onChange={(e) => onUpdate({ fontSize: Number(e.target.value) })}
            className="w-full h-7 rounded border bg-muted/50 px-1.5 text-[10px] focus:outline-none">
            <option value={10}>10px</option>
            <option value={11}>11px</option>
            <option value={12}>12px</option>
            <option value={13}>13px</option>
            <option value={14}>14px</option>
          </select>
        </div>
        <div>
          <label className="text-[9px] text-muted-foreground block mb-0.5">Density</label>
          <select value={settings.density} onChange={(e) => onUpdate({ density: e.target.value as "compact" | "normal" | "comfortable" })}
            className="w-full h-7 rounded border bg-muted/50 px-1.5 text-[10px] focus:outline-none">
            <option value="compact">Compact</option>
            <option value="normal">Normal</option>
            <option value="comfortable">Comfortable</option>
          </select>
        </div>
      </div>

      <ToggleCard label="Compact Mode" description="Reduce spacing throughout the app" checked={settings.compactMode} onChange={(v) => onUpdate({ compactMode: v })} />
      <ToggleCard label="Rounded Corners" description="Use rounded corners on panels" checked={settings.roundedCorners} onChange={(v) => onUpdate({ roundedCorners: v })} />
      <ToggleCard label="Animations" description="Enable UI animations and transitions" checked={settings.animations} onChange={(v) => onUpdate({ animations: v })} />
      <ToggleCard label="Panel Transparency" description="Use transparent panel backgrounds" checked={settings.panelTransparency} onChange={(v) => onUpdate({ panelTransparency: v })} />
    </SettingsSection>
  )
}
