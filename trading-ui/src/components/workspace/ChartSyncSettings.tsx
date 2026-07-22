"use client"

import { cn } from "@/lib/utils"
import type { SyncMode } from "@/store/useWorkspaceStore"

interface ChartSyncSettingsProps {
  enabled: SyncMode[]
  syncedGroup: string | null
  onToggle: (mode: SyncMode, enable: boolean) => void
  className?: string
}

const MODES: { id: SyncMode; label: string }[] = [
  { id: "crosshair", label: "Crosshair" },
  { id: "zoom", label: "Zoom" },
  { id: "scroll", label: "Scroll" },
  { id: "timeframe", label: "TF" },
  { id: "symbol", label: "Symbol" },
  { id: "drawing", label: "Drawings" },
  { id: "replay", label: "Replay" },
  { id: "indicator", label: "Indicators" },
  { id: "overlay", label: "Overlays" },
  { id: "ai", label: "AI" },
]

export function ChartSyncSettings({ enabled, syncedGroup, onToggle, className }: ChartSyncSettingsProps) {
  return (
    <div className={cn("rounded-lg border bg-card p-2 min-w-[180px]", className)}>
      <div className="text-[9px] font-medium text-muted-foreground uppercase tracking-wider mb-1">Sync Settings</div>
      <div className="space-y-0.5">
        {MODES.map((mode) => (
          <label key={mode.id} className="flex items-center gap-1.5 cursor-pointer">
            <input
              type="checkbox"
              checked={enabled.includes(mode.id)}
              onChange={(e) => onToggle(mode.id, e.target.checked)}
              className="rounded"
            />
            <span className="text-[9px]">{mode.label}</span>
          </label>
        ))}
      </div>
      <div className="text-[8px] text-muted-foreground mt-1">
        {syncedGroup ? `Group: ${syncedGroup}` : "Not synced"}
      </div>
    </div>
  )
}
