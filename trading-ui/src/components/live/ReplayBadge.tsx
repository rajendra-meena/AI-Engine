"use client"

import { useRealtimeStore } from "@/store/useRealtimeStore"

export function ReplayBadge() {
  const replayActive = useRealtimeStore((s) => s.replayActive)
  const replayProgress = useRealtimeStore((s) => s.replayProgress)

  if (!replayActive) return null

  return (
    <div className="flex items-center gap-1.5 rounded-md bg-amber-500/10 border border-amber-500/20 px-2 py-0.5">
      <span className="w-1.5 h-1.5 rounded-full bg-amber-500 animate-pulse" />
      <span className="text-[10px] font-medium text-amber-500">Replay</span>
      <span className="text-[9px] text-amber-500/70">{replayProgress}%</span>
    </div>
  )
}
