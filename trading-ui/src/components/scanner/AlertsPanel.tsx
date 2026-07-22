"use client"

import { cn } from "@/lib/utils"
import { Volume2, Monitor, Zap } from "lucide-react"
import type { AlertConfig } from "@/store/useScannerStore"

interface AlertsPanelProps {
  alerts: AlertConfig[]
  onToggle: (id: string) => void
  onUpdate: (id: string, config: Partial<AlertConfig>) => void
  className?: string
}

export function AlertsPanel({ alerts, onToggle, onUpdate, className }: AlertsPanelProps) {
  return (
    <div className={cn("rounded-lg border bg-card p-2", className)}>
      <div className="text-[9px] font-medium text-muted-foreground uppercase tracking-wider mb-1">Alerts</div>
      <div className="space-y-1">
        {alerts.map((alert) => (
          <div key={alert.id} className="flex items-center gap-1.5">
            <label className="flex items-center gap-1.5 flex-1 cursor-pointer">
              <input
                type="checkbox"
                checked={alert.enabled}
                onChange={() => onToggle(alert.id)}
                className="rounded"
              />
              <span className={cn("text-[9px]", alert.enabled ? "text-foreground" : "text-muted-foreground/50")}>
                {alert.label}
              </span>
            </label>
            {alert.enabled && (
              <div className="flex items-center gap-0.5">
                <button
                  onClick={() => onUpdate(alert.id, { flash: !alert.flash })}
                  className={cn("rounded p-0.5", alert.flash ? "text-primary" : "text-muted-foreground/30")}
                  title="Flash row"
                >
                  <Zap className="w-2.5 h-2.5" />
                </button>
                <button
                  onClick={() => onUpdate(alert.id, { sound: !alert.sound })}
                  className={cn("rounded p-0.5", alert.sound ? "text-primary" : "text-muted-foreground/30")}
                  title="Play sound"
                >
                  <Volume2 className="w-2.5 h-2.5" />
                </button>
                <button
                  onClick={() => onUpdate(alert.id, { desktop: !alert.desktop })}
                  className={cn("rounded p-0.5", alert.desktop ? "text-primary" : "text-muted-foreground/30")}
                  title="Desktop notification"
                >
                  <Monitor className="w-2.5 h-2.5" />
                </button>
              </div>
            )}
          </div>
        ))}
      </div>
    </div>
  )
}
