"use client"

import { AppLayout } from "@/components/layout/AppLayout"
import { ReplayStudio } from "@/components/replay/ReplayStudio"
import { ChartContainer } from "@/components/chart/ChartContainer"
import { ChartToolbar } from "@/components/chart/ChartToolbar"
import { useState, useCallback } from "react"
import { cn } from "@/lib/utils"

export default function BacktestPage() {
  const [replayMode, setReplayMode] = useState(false)

  const handleToggleReplay = useCallback(() => {
    setReplayMode((prev) => !prev)
  }, [])

  return (
    <AppLayout className="flex flex-col">
      <div className="flex items-center justify-between px-4 py-2 border-b shrink-0">
        <h1 className="text-lg font-bold">Backtest & Replay Studio</h1>
        <button
          onClick={handleToggleReplay}
          className={cn(
            "px-3 py-1 text-xs rounded transition-colors font-medium",
            replayMode ? "bg-amber-500/20 text-amber-500" : "bg-muted text-muted-foreground hover:bg-accent"
          )}
        >
          {replayMode ? "Chart View" : "Replay Studio"}
        </button>
      </div>

      <div className="flex-1 flex flex-col min-h-0">
        {replayMode ? (
          <ReplayStudio className="flex-1" />
        ) : (
          <>
            <ChartToolbar onToggleReplay={handleToggleReplay} replayMode={false} />
            <div className="flex-1 relative">
              <ChartContainer />
            </div>
          </>
        )}
      </div>
    </AppLayout>
  )
}
