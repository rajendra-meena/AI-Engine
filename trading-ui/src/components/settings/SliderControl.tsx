"use client"

import { cn } from "@/lib/utils"

interface SliderControlProps {
  label: string
  value: number
  min: number
  max: number
  step?: number
  suffix?: string
  onChange: (value: number) => void
  className?: string
}

export function SliderControl({ label, value, min, max, step = 1, suffix = "", onChange, className }: SliderControlProps) {
  return (
    <div className={cn("space-y-1", className)}>
      <div className="flex items-center justify-between">
        <span className="text-[10px] font-medium">{label}</span>
        <span className="text-[10px] font-mono text-muted-foreground">{value}{suffix}</span>
      </div>
      <input
        type="range"
        value={value}
        min={min}
        max={max}
        step={step}
        onChange={(e) => onChange(Number(e.target.value))}
        className="w-full h-1.5 rounded-full appearance-none bg-muted accent-primary cursor-pointer"
      />
    </div>
  )
}
