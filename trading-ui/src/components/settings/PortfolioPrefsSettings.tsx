"use client"

import { SettingsSection } from "./SettingsSection"
import { ToggleCard } from "./ToggleCard"
import type { PortfolioPrefs as PortfolioType } from "@/store/useSettingsStore"

interface Props {
  settings: PortfolioType
  onUpdate: (p: Partial<PortfolioType>) => void
}

export function PortfolioPrefsPanel({ settings, onUpdate }: Props) {
  return (
    <SettingsSection title="Portfolio" description="Portfolio and paper trading defaults">
      <div className="grid grid-cols-2 gap-2">
        <div>
          <label className="text-[9px] text-muted-foreground block mb-0.5">Paper Capital (₹)</label>
          <input type="number" value={settings.paperCapital} onChange={(e) => onUpdate({ paperCapital: Number(e.target.value) })}
            className="w-full h-7 rounded border bg-muted/50 px-1.5 text-[10px] font-mono focus:outline-none" />
        </div>
        <div>
          <label className="text-[9px] text-muted-foreground block mb-0.5">Default Currency</label>
          <select value={settings.defaultCurrency} onChange={(e) => onUpdate({ defaultCurrency: e.target.value })}
            className="w-full h-7 rounded border bg-muted/50 px-1.5 text-[10px] focus:outline-none">
            <option value="INR">INR (₹)</option>
            <option value="USD">USD ($)</option>
          </select>
        </div>
        <div>
          <label className="text-[9px] text-muted-foreground block mb-0.5">PnL Mode</label>
          <select value={settings.pnlMode} onChange={(e) => onUpdate({ pnlMode: e.target.value as "absolute" | "percent" })}
            className="w-full h-7 rounded border bg-muted/50 px-1.5 text-[10px] focus:outline-none">
            <option value="absolute">Absolute</option>
            <option value="percent">Percent</option>
          </select>
        </div>
      </div>
      <ToggleCard label="Auto Journal" description="Automatically record trade journal entries" checked={settings.autoJournal} onChange={(v) => onUpdate({ autoJournal: v })} />
      <ToggleCard label="Auto Screenshot" description="Capture chart screenshots on trade entry/exit" checked={settings.autoScreenshot} onChange={(v) => onUpdate({ autoScreenshot: v })} />
    </SettingsSection>
  )
}
