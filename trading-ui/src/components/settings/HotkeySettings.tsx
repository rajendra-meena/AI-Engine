"use client"

import { SettingsSection } from "./SettingsSection"
import { ShortcutEditor } from "./ShortcutEditor"
import { useMemo } from "react"
import { settingsService } from "@/services/settingsService"
import type { HotkeyEntry } from "@/store/useSettingsStore"

interface Props {
  hotkeys: HotkeyEntry[]
  onUpdate: (id: string, keys: string) => void
  onReset: () => void
}

export function HotkeySettingsPanel({ hotkeys, onUpdate, onReset }: Props) {
  const conflicts = useMemo(() => settingsService.detectConflicts(), [])

  const grouped = useMemo(() => {
    const groups: Record<string, HotkeyEntry[]> = {}
    for (const hk of hotkeys) {
      if (!groups[hk.category]) groups[hk.category] = []
      groups[hk.category].push(hk)
    }
    return groups
  }, [hotkeys])

  return (
    <SettingsSection title="Keyboard Shortcuts" description="Customize keyboard shortcuts" onReset={onReset}>
      {Object.entries(grouped).map(([category, items]) => (
        <div key={category}>
          <div className="text-[9px] font-medium text-muted-foreground uppercase tracking-wider mb-1 mt-2 first:mt-0">{category}</div>
          {items.map((hk) => (
            <ShortcutEditor
              key={hk.id}
              id={hk.id}
              label={hk.label}
              keys={hk.keys}
              category={hk.category}
              onChange={onUpdate}
              conflicts={conflicts.find((c) => c.keys === hk.keys)?.conflicts}
            />
          ))}
        </div>
      ))}
    </SettingsSection>
  )
}
