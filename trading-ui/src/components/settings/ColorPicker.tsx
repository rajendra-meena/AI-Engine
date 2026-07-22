"use client"

import { cn } from "@/lib/utils"

interface ColorPickerProps {
  label: string
  value: string
  onChange: (color: string) => void
  className?: string
}

const PRESETS = ["#6366f1", "#22c55e", "#f59e0b", "#ef4444", "#ec4899", "#06b6d4", "#a855f7", "#f97316"]

export function ColorPicker({ label, value, onChange, className }: ColorPickerProps) {
  return (
    <div className={cn("space-y-1", className)}>
      <div className="text-[10px] font-medium">{label}</div>
      <div className="flex items-center gap-2">
        <div className="flex gap-0.5">
          {PRESETS.map((color) => (
            <button
              key={color}
              onClick={() => onChange(color)}
              className={cn(
                "w-5 h-5 rounded-full border-2 transition-all",
                value === color ? "border-foreground scale-110" : "border-transparent",
              )}
              style={{ backgroundColor: color }}
            />
          ))}
        </div>
        <input
          type="color"
          value={value}
          onChange={(e) => onChange(e.target.value)}
          className="w-7 h-7 rounded cursor-pointer border-0 p-0 bg-transparent"
        />
        <span className="text-[9px] font-mono text-muted-foreground">{value}</span>
      </div>
    </div>
  )
}
