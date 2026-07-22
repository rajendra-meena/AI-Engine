"use client"

import { useReplay } from "@/hooks/useReplay"
import { ReplayToolbar } from "./ReplayToolbar"
import { TimelineSlider } from "./TimelineSlider"
import { ReplayCalendar } from "./ReplayCalendar"
import { ReplaySpeed } from "./ReplaySpeed"
import { ReplayStatistics } from "./ReplayStatistics"
import { ReplayJournal } from "./ReplayJournal"
import { ReplayMiniMap } from "./ReplayMiniMap"
import { ReplayControls } from "./ReplayControls"
import { useState, useEffect } from "react"
import { cn } from "@/lib/utils"
import { BarChart3, BookOpen, Map, CalendarDays } from "lucide-react"

interface ReplayStudioProps {
  className?: string
}

/**
 * ReplayStudio — Professional Replay & Backtesting Studio.
 *
 * Architecture:
 *   ReplayToolbar   — Play/Pause/Stop/Step controls
 *   TimelineSlider  — Seekable progress timeline
 *   ReplayCalendar  — Date/week/month/session picker
 *   ReplaySpeed     — 0.25x to 100x speed buttons
 *   ReplayStatistics — Candles/time/progress/decisions/trades/win rate
 *   ReplayJournal   — Per-candle AI decision log
 *   ReplayMiniMap   — Session overview with event markers
 *   ReplayControls  — Keyboard shortcuts (Space, arrows, Ctrl)
 *
 * All data from the backend Replay Engine via REST + WebSocket.
 * No mock data.
 */
export function ReplayStudio({ className }: ReplayStudioProps) {
  const replay = useReplay()
  const [elapsedSeconds, setElapsedSeconds] = useState(0)

  useEffect(() => {
    if (!replay.startTime || !replay.isPlaying) return
    const interval = setInterval(() => {
      setElapsedSeconds((Date.now() - replay.startTime!) / 1000)
    }, 1000)
    return () => clearInterval(interval)
  }, [replay.startTime, replay.isPlaying])

  if (!replay.active && replay.totalCandles === 0) {
    return (
      <div className={cn("flex flex-col h-full", className)}>
        <div className="flex-1 flex items-center justify-center">
          <div className="text-center space-y-3">
            <div className="text-sm text-muted-foreground">No active replay session</div>
            <button
              onClick={() => replay.start()}
              className="rounded-md bg-primary/20 text-primary hover:bg-primary/30 px-4 py-2 text-xs font-medium transition-colors"
            >
              Start Replay (NIFTY 50 · 15m · 30d)
            </button>
          </div>
        </div>
        <ReplayControls
          onPlayPause={replay.togglePlay}
          onStepBack={replay.stepBack}
          onStepForward={replay.stepForward}
          onStop={replay.stop}
        />
      </div>
    )
  }

  const progressPercent = replay.totalCandles > 0
    ? (replay.currentIndex / replay.totalCandles) * 100
    : 0

  return (
    <div className={cn("flex flex-col h-full overflow-hidden", className)}>
      <ReplayControls
        onPlayPause={replay.togglePlay}
        onStepBack={replay.stepBack}
        onStepForward={replay.stepForward}
        onStop={replay.stop}
      />

      {/* Toolbar */}
      <div className="flex items-center gap-2 p-2 border-b bg-card shrink-0">
        <ReplayToolbar
          isPlaying={replay.isPlaying}
          active={replay.active}
          currentIndex={replay.currentIndex}
          totalCandles={replay.totalCandles}
          onPlayPause={replay.togglePlay}
          onStop={replay.stop}
          onStepBack={replay.stepBack}
          onStepForward={replay.stepForward}
          onRestart={() => replay.start()}
        />

        <div className="w-px h-5 bg-border mx-1" />

        {/* Toggle buttons */}
        <button
          onClick={replay.toggleStatistics}
          className={cn("rounded p-1 transition-colors", replay.showStatistics ? "text-primary" : "text-muted-foreground hover:text-foreground")}
          title="Statistics"
        >
          <BarChart3 className="w-3.5 h-3.5" />
        </button>
        <button
          onClick={replay.toggleJournal}
          className={cn("rounded p-1 transition-colors", replay.showJournal ? "text-primary" : "text-muted-foreground hover:text-foreground")}
          title="Journal"
        >
          <BookOpen className="w-3.5 h-3.5" />
        </button>
        <button
          onClick={replay.toggleMiniMap}
          className={cn("rounded p-1 transition-colors", replay.showMiniMap ? "text-primary" : "text-muted-foreground hover:text-foreground")}
          title="Mini Map"
        >
          <Map className="w-3.5 h-3.5" />
        </button>
        <button
          onClick={replay.toggleCalendar}
          className={cn("rounded p-1 transition-colors", replay.showCalendar ? "text-primary" : "text-muted-foreground hover:text-foreground")}
          title="Calendar"
        >
          <CalendarDays className="w-3.5 h-3.5" />
        </button>
      </div>

      {/* Main panel */}
      <div className="flex-1 overflow-y-auto p-2 space-y-2">
        {/* Timeline */}
        <TimelineSlider
          currentIndex={replay.currentIndex}
          totalCandles={replay.totalCandles}
          progressPercent={progressPercent}
          onSeek={replay.seek}
        />

        <div className="grid grid-cols-2 gap-2">
          {/* Calendar */}
          {replay.showCalendar && (
            <ReplayCalendar
              mode={replay.view === "studio" ? "date" : "date"}
              selectedDate={null}
              onModeChange={() => {}}
              onDateChange={() => {}}
            />
          )}

          {/* Speed */}
          <ReplaySpeed
            speed={replay.speed}
            onSpeedChange={replay.setSpeed}
          />
        </div>

        <div className="grid grid-cols-2 gap-2">
          {/* Statistics */}
          {replay.showStatistics && (
            <ReplayStatistics
              processedCandles={replay.currentIndex}
              totalCandles={replay.totalCandles}
              elapsedSeconds={elapsedSeconds}
              speed={replay.speed}
              progressPercent={progressPercent}
              decisions={replay.processedDecisions}
              trades={replay.processedTrades}
              winRate={null}
            />
          )}

          {/* Mini Map */}
          {replay.showMiniMap && (
            <ReplayMiniMap
              currentIndex={replay.currentIndex}
              totalCandles={replay.totalCandles}
              events={replay.journal.map((j) => ({
                index: j.index,
                type: "decision" as const,
                color: j.decision === "HIGH_CONVICTION" ? "#22c55e" : j.decision === "NO_TRADE" ? "#ef4444" : "#f59e0b",
              }))}
            />
          )}
        </div>

        {/* Journal */}
        {replay.showJournal && (
          <ReplayJournal entries={replay.journal} />
        )}
      </div>
    </div>
  )
}
