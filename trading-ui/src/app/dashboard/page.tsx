"use client"

import { AppLayout } from "@/components/layout/AppLayout"
import { Workspace } from "@/components/layout/Workspace"
import { RightPanel } from "@/components/layout/RightPanel"
import { BottomPanel } from "@/components/layout/BottomPanel"

export default function DashboardPage() {
  return (
    <AppLayout bottom={<BottomPanel />}>
      <div className="flex flex-1 overflow-hidden h-full">
        <Workspace />
        <RightPanel />
      </div>
    </AppLayout>
  )
}
