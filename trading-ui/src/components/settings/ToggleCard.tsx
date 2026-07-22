"use client"

import { cn } from "@/lib/utils"

interface ToggleCardProps {
  label: string
  description?: string
  checked: boolean
  onChange: (checked: boolean) => void
  className?: string
}

export function ToggleCard({ label, description, checked, onChange, className }: ToggleCardProps) {
  return (
    <label className={cn("flex items-center gap-3 py-1.5 cursor-pointer group", className)}>
      <div className="flex-1 min-w-0">
        <div className="text-[10px] font-medium">{label}</div>
        {description && <div className="text-[8px] text-muted-foreground">{description}</div>}
      </div>
      <input
        type="checkbox"
        checked={checked}
        onChange={(e) => onChange(e.target.checked)}
        className="rounded accent-primary"
      />
    </label>
  )
}
