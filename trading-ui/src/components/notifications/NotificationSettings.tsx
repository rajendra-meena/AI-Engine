"use client"

import { cn } from "@/lib/utils"
import { Volume2, Monitor, Bell, Trash2, Clock } from "lucide-react"
import type { NotificationCategory, NotificationPriority, NotificationSettings as Settings } from "@/store/useNotificationStore"

interface NotificationSettingsPanelProps {
  settings: Settings
  onUpdate: (partial: Partial<Settings>) => void
  onToggleCategory: (cat: NotificationCategory) => void
  onTogglePriority: (pri: NotificationPriority) => void
  className?: string
}

const CATEGORY_LABELS: Record<NotificationCategory, string> = {
  ai: "AI Decisions", indicators: "Indicators", structure: "Market Structure",
  patterns: "Patterns", sr: "Support & Resistance", portfolio: "Portfolio",
  replay: "Replay", scanner: "Scanner", orders: "Orders",
  warnings: "Warnings", errors: "Errors", system: "System",
}

const PRIORITY_LABELS: Record<NotificationPriority, string> = {
  INFO: "Info", SUCCESS: "Success", WARNING: "Warning", CRITICAL: "Critical",
}

export function NotificationSettingsPanel({ settings, onUpdate, onToggleCategory, onTogglePriority, className }: NotificationSettingsPanelProps) {
  return (
    <div className={cn("space-y-2", className)}>
      {/* Global toggle */}
      <label className="flex items-center gap-2 cursor-pointer">
        <Bell className="w-3 h-3 text-muted-foreground" />
        <span className="text-[10px] font-medium flex-1">Enable Notifications</span>
        <input type="checkbox" checked={settings.enabled} onChange={(e) => onUpdate({ enabled: e.target.checked })} className="rounded" />
      </label>

      {/* Sound */}
      <label className="flex items-center gap-2 cursor-pointer pl-5" hidden={!settings.enabled}>
        <Volume2 className="w-2.5 h-2.5 text-muted-foreground" />
        <span className="text-[9px] flex-1">Sound</span>
        <input type="checkbox" checked={settings.sound} onChange={(e) => onUpdate({ sound: e.target.checked })} className="rounded" />
      </label>

      {/* Desktop */}
      <label className="flex items-center gap-2 cursor-pointer pl-5" hidden={!settings.enabled}>
        <Monitor className="w-2.5 h-2.5 text-muted-foreground" />
        <span className="text-[9px] flex-1">Desktop Notifications</span>
        <input type="checkbox" checked={settings.desktop} onChange={(e) => onUpdate({ desktop: e.target.checked })} className="rounded" />
      </label>

      {/* Auto dismiss */}
      <label className="flex items-center gap-2 cursor-pointer pl-5" hidden={!settings.enabled}>
        <Clock className="w-2.5 h-2.5 text-muted-foreground" />
        <span className="text-[9px] flex-1">Auto dismiss ({settings.autoDismissSeconds}s)</span>
        <input type="checkbox" checked={settings.autoDismiss} onChange={(e) => onUpdate({ autoDismiss: e.target.checked })} className="rounded" />
      </label>

      {/* Categories */}
      <div className="pt-1 border-t">
        <div className="text-[8px] text-muted-foreground uppercase tracking-wider mb-1">Categories</div>
        <div className="grid grid-cols-2 gap-0.5">
          {(Object.keys(CATEGORY_LABELS) as NotificationCategory[]).map((cat) => (
            <label key={cat} className="flex items-center gap-1 cursor-pointer">
              <input type="checkbox" checked={settings.categories[cat]} onChange={() => onToggleCategory(cat)} className="rounded" />
              <span className="text-[8px]">{CATEGORY_LABELS[cat]}</span>
            </label>
          ))}
        </div>
      </div>

      {/* Priorities */}
      <div className="pt-1 border-t">
        <div className="text-[8px] text-muted-foreground uppercase tracking-wider mb-1">Priorities</div>
        <div className="flex gap-1">
          {(Object.keys(PRIORITY_LABELS) as NotificationPriority[]).map((pri) => (
            <label key={pri} className="flex items-center gap-1 cursor-pointer">
              <input type="checkbox" checked={settings.priorities[pri]} onChange={() => onTogglePriority(pri)} className="rounded" />
              <span className={cn("text-[8px]", pri === "CRITICAL" ? "text-red-500" : pri === "WARNING" ? "text-amber-500" : pri === "SUCCESS" ? "text-emerald-500" : "")}>
                {PRIORITY_LABELS[pri]}
              </span>
            </label>
          ))}
        </div>
      </div>

      {/* Max history */}
      <div className="pt-1 border-t flex items-center gap-2">
        <Trash2 className="w-2.5 h-2.5 text-muted-foreground" />
        <span className="text-[8px] text-muted-foreground">Max history: {settings.maxHistory}</span>
      </div>
    </div>
  )
}
