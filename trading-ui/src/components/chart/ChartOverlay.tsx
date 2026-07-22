"use client"

import { useChartStore } from "@/store/useChartStore"

export function ChartOverlay() {
  const { markers, horizontalLines } = useChartStore()

  if (markers.length === 0 && horizontalLines.length === 0) return null

  return (
    <div className="absolute bottom-2 left-2 z-20 space-y-1 max-w-[200px]">
      {markers.length > 0 && (
        <div className="rounded-md bg-background/90 border px-2 py-1 text-[9px] text-muted-foreground">
          <div className="font-medium mb-0.5">Markers</div>
          {markers.slice(-3).map((m, i) => (
            <div key={i} className="truncate">{m.text}</div>
          ))}
        </div>
      )}
    </div>
  )
}
