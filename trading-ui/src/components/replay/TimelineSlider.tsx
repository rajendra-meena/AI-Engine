"use client"

import { useCallback, useRef } from "react"
import { cn } from "@/lib/utils"

interface TimelineSliderProps {
  currentIndex: number
  totalCandles: number
  progressPercent: number
  onSeek: (position: number) => void
}

export function TimelineSlider({ totalCandles, progressPercent, onSeek }: TimelineSliderProps) {
  const trackRef = useRef<HTMLDivElement>(null)

  const handleClick = useCallback((e: React.MouseEvent<HTMLDivElement>) => {
    if (!trackRef.current || totalCandles === 0) return
    const rect = trackRef.current.getBoundingClientRect()
    const x = (e.clientX - rect.left) / rect.width
    const target = Math.round(x * totalCandles)
    onSeek(Math.max(0, Math.min(target, totalCandles)))
  }, [totalCandles, onSeek])

  const handleDrag = useCallback((e: React.MouseEvent<HTMLDivElement>) => {
    if (e.buttons !== 1) return
    handleClick(e)
  }, [handleClick])

  return (
    <div className="space-y-1">
      <div
        ref={trackRef}
        className="relative h-6 rounded-md bg-muted/50 cursor-pointer overflow-hidden border"
        onClick={handleClick}
        onMouseMove={handleDrag}
      >
        {/* Progress fill */}
        <div
          className="absolute inset-y-0 left-0 bg-primary/20 transition-all duration-200"
          style={{ width: `${Math.min(progressPercent, 100)}%` }}
        />

        {/* Cursor */}
        <div
          className="absolute top-1/2 -translate-y-1/2 w-2.5 h-5 rounded-sm bg-primary shadow-lg transition-all duration-200"
          style={{ left: `calc(${Math.min(progressPercent, 100)}% - 5px)` }}
        />

        {/* Tick marks */}
        {totalCandles > 0 && (
          <div className="absolute inset-x-0 bottom-0 flex justify-between px-1">
            {Array.from({ length: 11 }, (_, i) => (
              <div
                key={i}
                className={cn(
                  "w-px h-1 transition-colors",
                  i * 10 <= progressPercent ? "bg-primary/30" : "bg-border"
                )}
              />
            ))}
          </div>
        )}
      </div>

      {/* Labels */}
      <div className="flex justify-between text-[8px] text-muted-foreground">
        <span>0</span>
        <span>{progressPercent.toFixed(1)}%</span>
        <span>{totalCandles}</span>
      </div>
    </div>
  )
}
