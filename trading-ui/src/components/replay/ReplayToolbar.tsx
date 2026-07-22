"use client"

import { Play, Pause, Square, StepBack, StepForward, RotateCcw } from "lucide-react"
import { cn } from "@/lib/utils"

interface ReplayToolbarProps {
  isPlaying: boolean
  active: boolean
  currentIndex: number
  totalCandles: number
  onPlayPause: () => void
  onStop: () => void
  onStepBack: () => void
  onStepForward: () => void
  onRestart: () => void
}

export function ReplayToolbar({
  isPlaying, active, currentIndex, totalCandles,
  onPlayPause, onStop, onStepBack, onStepForward, onRestart,
}: ReplayToolbarProps) {
  return (
    <div className="flex items-center gap-1 rounded-md border bg-card px-2 py-1.5">
      {/* Restart */}
      <button
        onClick={onRestart}
        disabled={!active}
        className="rounded p-1 text-muted-foreground hover:text-foreground hover:bg-accent transition-colors disabled:opacity-30 disabled:pointer-events-none"
        title="Restart"
      >
        <RotateCcw className="w-3.5 h-3.5" />
      </button>

      {/* Step back */}
      <button
        onClick={onStepBack}
        disabled={!active || currentIndex <= 0}
        className="rounded p-1 text-muted-foreground hover:text-foreground hover:bg-accent transition-colors disabled:opacity-30 disabled:pointer-events-none"
        title="Previous Candle"
      >
        <StepBack className="w-3.5 h-3.5" />
      </button>

      {/* Play/Pause */}
      <button
        onClick={onPlayPause}
        disabled={!active && totalCandles === 0}
        className={cn(
          "rounded p-1.5 transition-colors",
          isPlaying
            ? "bg-amber-500/20 text-amber-500 hover:bg-amber-500/30"
            : "bg-emerald-500/20 text-emerald-500 hover:bg-emerald-500/30",
          !active && totalCandles === 0 && "opacity-30 pointer-events-none"
        )}
        title={isPlaying ? "Pause" : "Play"}
      >
        {isPlaying ? <Pause className="w-4 h-4" /> : <Play className="w-4 h-4" />}
      </button>

      {/* Step forward */}
      <button
        onClick={onStepForward}
        disabled={!active || currentIndex >= totalCandles}
        className="rounded p-1 text-muted-foreground hover:text-foreground hover:bg-accent transition-colors disabled:opacity-30 disabled:pointer-events-none"
        title="Next Candle"
      >
        <StepForward className="w-3.5 h-3.5" />
      </button>

      {/* Stop */}
      <button
        onClick={onStop}
        disabled={!active}
        className="rounded p-1 text-muted-foreground hover:text-foreground hover:bg-accent transition-colors disabled:opacity-30 disabled:pointer-events-none"
        title="Stop"
      >
        <Square className="w-3.5 h-3.5" />
      </button>

      <div className="w-px h-4 bg-border mx-1" />

      {/* Candle counter */}
      <span className="text-[10px] text-muted-foreground font-mono whitespace-nowrap">
        {currentIndex} / {totalCandles}
      </span>
    </div>
  )
}
