"use client"

import { cn } from "@/lib/utils"

interface SettingsSectionProps {
  title: string
  description?: string
  children: React.ReactNode
  className?: string
  onReset?: () => void
}

export function SettingsSection({ title, description, children, className, onReset }: SettingsSectionProps) {
  return (
    <div className={cn("space-y-3", className)}>
      <div className="flex items-center gap-2">
        <div className="flex-1">
          <h3 className="text-sm font-bold">{title}</h3>
          {description && <p className="text-[10px] text-muted-foreground">{description}</p>}
        </div>
        {onReset && (
          <button onClick={onReset} className="rounded px-2 py-1 text-[9px] text-muted-foreground hover:text-foreground hover:bg-accent transition-colors">
            Reset
          </button>
        )}
      </div>
      <div className={cn("rounded-lg border bg-card p-3 space-y-2", className)}>
        {children}
      </div>
    </div>
  )
}
