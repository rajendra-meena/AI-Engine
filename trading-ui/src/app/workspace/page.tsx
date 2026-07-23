"use client"

import { AppLayout } from "@/components/layout/AppLayout"
import { MultiChartWorkspace } from "@/components/workspace/MultiChartWorkspace"

export default function WorkspaceRoute() {
  return (
    <AppLayout>
      <MultiChartWorkspace />
    </AppLayout>
  )
}
