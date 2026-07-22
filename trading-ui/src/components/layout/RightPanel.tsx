"use client"

import { useLayoutStore } from "@/store/useLayoutStore"
import { PanelSection } from "./PanelSection"
import { AIDecisionPanel } from "@/components/intelligence/AIDecisionPanel"
import { TradePlannerPanel } from "@/components/trade/TradePlannerPanel"
import { IndicatorsPanel } from "@/components/intelligence/IndicatorsPanel"
import { MarketStructurePanel } from "@/components/intelligence/MarketStructurePanel"
import { PatternPanel } from "@/components/intelligence/PatternPanel"
import { SupportResistancePanel } from "@/components/intelligence/SupportResistancePanel"
import { MTFPanel } from "@/components/intelligence/MTFPanel"
import {
  Brain, Gauge, LayoutDashboard, Shield, PanelRight, SplitSquareHorizontal, ChevronLeft, ChevronRight, ClipboardList,
} from "lucide-react"

const SECTIONS = [
  { id: "ai", title: "AI Decision", icon: <Brain className="w-3.5 h-3.5" />, color: "text-violet-500", panel: <AIDecisionPanel /> },
  { id: "trade", title: "Trade Planner", icon: <ClipboardList className="w-3.5 h-3.5" />, color: "text-emerald-500", panel: <TradePlannerPanel /> },
  { id: "indicators", title: "Indicators", icon: <Gauge className="w-3.5 h-3.5" />, color: "text-blue-500", panel: <IndicatorsPanel /> },
  { id: "structure", title: "Market Structure", icon: <LayoutDashboard className="w-3.5 h-3.5" />, color: "text-amber-500", panel: <MarketStructurePanel /> },
  { id: "patterns", title: "Patterns", icon: <SplitSquareHorizontal className="w-3.5 h-3.5" />, color: "text-cyan-500", panel: <PatternPanel /> },
  { id: "sr", title: "Support & Resistance", icon: <Shield className="w-3.5 h-3.5" />, color: "text-red-500", panel: <SupportResistancePanel /> },
  { id: "mtf", title: "Multi Timeframe", icon: <PanelRight className="w-3.5 h-3.5" />, color: "text-purple-500", panel: <MTFPanel /> },
]

export function RightPanel() {
  const { rightPanelOpen, toggleRightPanel } = useLayoutStore()

  if (!rightPanelOpen) {
    return (
      <button
        onClick={toggleRightPanel}
        className="flex items-center border-l bg-card px-1 hover:bg-accent transition-colors"
        aria-label="Expand right panel"
      >
        <ChevronLeft className="w-4 h-4 text-muted-foreground" />
      </button>
    )
  }

  return (
    <aside className="w-[380px] border-l bg-card flex flex-col shrink-0 overflow-hidden" role="complementary" aria-label="Analysis panels">
      <div className="flex items-center justify-between px-3 py-2 border-b shrink-0">
        <span className="text-xs font-semibold text-muted-foreground">Analysis</span>
        <button
          onClick={toggleRightPanel}
          className="rounded-md p-1 text-muted-foreground hover:bg-accent hover:text-accent-foreground transition-colors"
          aria-label="Collapse right panel"
        >
          <ChevronRight className="w-4 h-4" />
        </button>
      </div>

      <div className="flex-1 overflow-y-auto p-2 space-y-2">
        {SECTIONS.map((section) => (
          <PanelSection
            key={section.id}
            icon={<span className={section.color}>{section.icon}</span>}
            title={section.title}
            defaultOpen={section.id === "ai"}
          >
            {section.panel}
          </PanelSection>
        ))}
      </div>
    </aside>
  )
}
