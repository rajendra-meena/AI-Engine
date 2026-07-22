"use client"

import { useState, useCallback } from "react"
import { ChartContainer } from "./ChartContainer"
import { ChartToolbar } from "./ChartToolbar"
import { ChartOverlay } from "./ChartOverlay"
import { ReplayOverlay } from "./ReplayOverlay"
import { OverlayToolbar } from "./overlays/OverlayToolbar"
import { IndicatorOverlay } from "./overlays/IndicatorOverlay"
import { StructureOverlay } from "./overlays/StructureOverlay"
import { PatternOverlay } from "./overlays/PatternOverlay"
import { SupportResistanceOverlay } from "./overlays/SupportResistanceOverlay"
import { LiquidityOverlay } from "./overlays/LiquidityOverlay"
import { AIOverlay } from "./overlays/AIOverlay"
import { useChartData } from "@/hooks/useChartData"
import { useChartStore } from "@/store/useChartStore"
import { chartService } from "@/services/chartService"
import { cn } from "@/lib/utils"

interface TradingViewChartProps {
  className?: string
  showToolbar?: boolean
  showReplay?: boolean
}

export function TradingViewChart({ className, showToolbar = true, showReplay = true }: TradingViewChartProps) {
  const { isLoading, refetch } = useChartData()
  const { replayMode, setReplayMode, setCandles, setReplayIndex, symbol, interval } = useChartStore()
  const [isPlaying, setIsPlaying] = useState(false)
  const [speed, setSpeed] = useState(1)
  const [replayTimer, setReplayTimer] = useState<NodeJS.Timeout | null>(null)

  const handleToggleReplay = useCallback(async () => {
    if (replayMode) {
      setReplayMode(false)
      setIsPlaying(false)
      if (replayTimer) clearInterval(replayTimer)
      refetch()
    } else {
      setReplayMode(true)
      setReplayIndex(0)
      const data = await chartService.fetchCandles(symbol, interval, 30)
      setCandles(data.candles || [])
    }
  }, [replayMode, replayTimer, refetch, setReplayMode, setReplayIndex, setCandles, symbol, interval])

  const handlePlay = useCallback(() => {
    setIsPlaying(true)
    const timer = setInterval(() => {
      useChartStore.setState((s) => {
        const next = s.replayIndex + 1
        if (next >= s.candles.length) { clearInterval(timer); return { replayIndex: s.candles.length - 1 } }
        return { replayIndex: next, candles: s.candles.slice(0, next + 1) }
      })
    }, 3000 / speed)
    setReplayTimer(timer)
  }, [speed])

  const handlePause = useCallback(() => {
    setIsPlaying(false)
    if (replayTimer) clearInterval(replayTimer)
  }, [replayTimer])

  const handleStop = useCallback(() => {
    setIsPlaying(false)
    if (replayTimer) clearInterval(replayTimer)
    setReplayMode(false)
    refetch()
  }, [replayTimer, refetch, setReplayMode])

  const handleStepBack = useCallback(() => {
    setReplayIndex(Math.max(0, useChartStore.getState().replayIndex - 1))
  }, [setReplayIndex])

  const handleStepForward = useCallback(() => {
    const state = useChartStore.getState()
    setReplayIndex(Math.min(state.candles.length - 1, state.replayIndex + 1))
  }, [setReplayIndex])

  return (
    <div className={cn("relative flex flex-col h-full", className)}>
      {showToolbar && (
        <ChartToolbar onToggleReplay={showReplay ? handleToggleReplay : undefined} replayMode={replayMode} />
      )}

      {/* Overlay toolbar */}
      <OverlayToolbar />

      <div className="flex-1 relative">
        {isLoading && (
          <div className="absolute inset-0 z-10 flex items-center justify-center bg-background/60">
            <div className="w-6 h-6 border-2 border-primary border-t-transparent rounded-full animate-spin" />
          </div>
        )}
        <ChartContainer />
        <ChartOverlay />

        {/* Intelligence overlays — render null, update chart store via hooks */}
        <IndicatorOverlay />
        <StructureOverlay />
        <PatternOverlay />
        <SupportResistanceOverlay />
        <LiquidityOverlay />
        <AIOverlay />

        {replayMode && (
          <ReplayOverlay
            isPlaying={isPlaying}
            onPlay={handlePlay}
            onPause={handlePause}
            onStop={handleStop}
            onStepBack={handleStepBack}
            onStepForward={handleStepForward}
            speed={speed}
            onSpeedChange={setSpeed}
          />
        )}
      </div>
    </div>
  )
}
