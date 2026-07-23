"use client"

import { Navbar } from "@/components/navbar"
import { MultiChartWorkspace } from "@/components/workspace/MultiChartWorkspace"
import { useRealtime } from "@/hooks/useRealtime"

export default function WorkspaceRoute() {
  useRealtime()

  return (
    <div className="h-screen flex flex-col bg-background overflow-hidden">
      <Navbar />
      <div className="flex-1 overflow-hidden">
        <MultiChartWorkspace />
      </div>
    </div>
  )
}
