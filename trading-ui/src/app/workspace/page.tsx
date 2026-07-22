"use client"

import { MultiChartWorkspace } from "@/components/workspace/MultiChartWorkspace"
import { useRealtime } from "@/hooks/useRealtime"

export default function WorkspaceRoute() {
  useRealtime()

  return (
    <div className="h-screen flex flex-col bg-background overflow-hidden">
      <MultiChartWorkspace />
    </div>
  )
}
