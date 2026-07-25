"use client"

import { TradingViewChart } from "@/components/chart/TradingViewChart"

export function Workspace() {
  return (
    <main className="flex flex-col flex-1 overflow-hidden" role="main">
      <div className="flex-1 flex flex-col min-h-0">
        <TradingViewChart />
      </div>
    </main>
  )
}
