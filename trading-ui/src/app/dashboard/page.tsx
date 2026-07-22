"use client"

import { Header } from "@/components/layout/Header"
import { Sidebar } from "@/components/layout/Sidebar"
import { Workspace } from "@/components/layout/Workspace"
import { RightPanel } from "@/components/layout/RightPanel"
import { BottomPanel } from "@/components/layout/BottomPanel"
import { useRealtime } from "@/hooks/useRealtime"

export default function DashboardPage() {
  useRealtime()

  return (
    <div className="h-screen flex flex-col bg-background overflow-hidden">
      <Header />
      <div className="flex flex-1 overflow-hidden">
        <Sidebar />
        <Workspace />
        <RightPanel />
      </div>
      <BottomPanel />
    </div>
  )
}
