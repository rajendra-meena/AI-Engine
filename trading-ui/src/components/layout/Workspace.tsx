"use client"

import { useState } from "react"
import { cn } from "@/lib/utils"
import { TradingViewChart } from "@/components/chart/TradingViewChart"

const CHART_TABS = [
  { id: "orders", label: "Orders" },
  { id: "positions", label: "Positions" },
  { id: "trades", label: "Trades" },
  { id: "logs", label: "Logs" },
  { id: "alerts", label: "Alerts" },
]

export function Workspace() {
  const [activeChartTab, setActiveChartTab] = useState("orders")

  return (
    <main className="flex flex-col flex-1 overflow-hidden" role="main">
      {/* Chart section */}
      <div className="flex-1 flex flex-col min-h-0">
        <TradingViewChart />
      </div>

      {/* Bottom tabs */}
      <div className="border-t bg-card shrink-0">
        <div className="flex items-center border-b">
          {CHART_TABS.map((tab) => (
            <button
              key={tab.id}
              onClick={() => setActiveChartTab(tab.id)}
              className={cn(
                "px-3 py-1.5 text-[11px] font-medium transition-colors border-r",
                activeChartTab === tab.id
                  ? "bg-muted/50 text-foreground"
                  : "text-muted-foreground hover:text-foreground hover:bg-accent/50"
              )}
            >
              {tab.label}
            </button>
          ))}
        </div>
        <div className="h-20 flex items-center justify-center text-[10px] text-muted-foreground/30">
          {activeChartTab.charAt(0).toUpperCase() + activeChartTab.slice(1)} data will appear here
        </div>
      </div>
    </main>
  )
}
