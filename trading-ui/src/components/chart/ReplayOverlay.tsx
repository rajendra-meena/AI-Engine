"use client"

import { useChartStore } from "@/store/useChartStore"
import { Play, Pause, SkipBack, SkipForward, RotateCcw } from "lucide-react"

interface ReplayOverlayProps {
  isPlaying: boolean
  onPlay: () => void
  onPause: () => void
  onStop: () => void
  onStepBack: () => void
  onStepForward: () => void
  speed: number
  onSpeedChange: (speed: number) => void
}

const SPEEDS = [1, 2, 5, 10, 30, 60, 100]

export function ReplayOverlay({ isPlaying, onPlay, onPause, onStop, onStepBack, onStepForward, speed, onSpeedChange }: ReplayOverlayProps) {
  const { replayIndex, candles } = useChartStore()
  const progress = candles.length > 0 ? Math.round((replayIndex / candles.length) * 100) : 0

  return (
    <div className="absolute bottom-0 left-0 right-0 z-30 bg-background/95 border-t px-4 py-2">
      <div className="flex items-center gap-3">
        {/* Controls */}
        <div className="flex items-center gap-1">
          <button onClick={onStepBack} className="rounded p-1 text-muted-foreground hover:text-foreground hover:bg-accent transition-colors" aria-label="Step back">
            <SkipBack className="w-4 h-4" />
          </button>
          {isPlaying ? (
            <button onClick={onPause} className="rounded p-1.5 bg-amber-500/20 text-amber-500 hover:bg-amber-500/30 transition-colors" aria-label="Pause">
              <Pause className="w-4 h-4" />
            </button>
          ) : (
            <button onClick={onPlay} className="rounded p-1.5 bg-emerald-500/20 text-emerald-500 hover:bg-emerald-500/30 transition-colors" aria-label="Play">
              <Play className="w-4 h-4" />
            </button>
          )}
          <button onClick={onStepForward} className="rounded p-1 text-muted-foreground hover:text-foreground hover:bg-accent transition-colors" aria-label="Step forward">
            <SkipForward className="w-4 h-4" />
          </button>
          <button onClick={onStop} className="rounded p-1 text-muted-foreground hover:text-foreground hover:bg-accent transition-colors" aria-label="Stop">
            <RotateCcw className="w-4 h-4" />
          </button>
        </div>

        {/* Progress */}
        <div className="flex-1 flex items-center gap-2">
          <div className="h-1 flex-1 rounded-full bg-muted overflow-hidden">
            <div className="h-full bg-primary transition-all duration-200" style={{ width: `${progress}%` }} />
          </div>
          <span className="text-[10px] text-muted-foreground w-8 text-right">{progress}%</span>
        </div>

        {/* Speed */}
        <select
          value={speed}
          onChange={(e) => onSpeedChange(Number(e.target.value))}
          className="h-6 rounded border bg-muted/50 px-1.5 text-[10px] font-medium text-muted-foreground focus:outline-none"
        >
          {SPEEDS.map((s) => (
            <option key={s} value={s}>{s}x</option>
          ))}
        </select>

        {/* Info */}
        <div className="text-[10px] text-muted-foreground whitespace-nowrap">
          {replayIndex}/{candles.length}
        </div>
      </div>
    </div>
  )
}
