"use client"

import { cn } from "@/lib/utils"

interface ReplaySpeedProps {
  speed: number
  onSpeedChange: (speed: number) => void
}

const SPEEDS = [0.25, 0.5, 1, 2, 5, 10, 20, 50, 100]

export function ReplaySpeed({ speed, onSpeedChange }: ReplaySpeedProps) {
  return (
    <div className="rounded-md border bg-card p-2 space-y-1.5">
      <div className="text-[9px] font-medium text-muted-foreground uppercase tracking-wider">Speed</div>
      <div className="flex flex-wrap gap-0.5">
        {SPEEDS.map((s) => (
          <button
            key={s}
            onClick={() => onSpeedChange(s)}
            className={cn(
              "px-1.5 py-0.5 rounded text-[9px] font-mono font-medium transition-colors",
              speed === s
                ? "bg-primary/20 text-primary"
                : "text-muted-foreground hover:bg-accent"
            )}
          >
            {s}x
          </button>
        ))}
      </div>
    </div>
  )
}
