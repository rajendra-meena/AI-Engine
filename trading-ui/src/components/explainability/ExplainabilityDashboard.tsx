"use client"

import { useExplainability } from "@/hooks/useExplainability"
import { DecisionBreakdown } from "./DecisionBreakdown"
import { ScoreBreakdown } from "./ScoreBreakdown"
import { ConfidenceBreakdown } from "./ConfidenceBreakdown"
import { RiskBreakdown } from "./RiskBreakdown"
import { MarketContextTree } from "./MarketContextTree"
import { IndicatorContributions } from "./IndicatorContribution"
import { PatternContributions } from "./PatternContribution"
import { StructureContributions } from "./StructureContribution"
import { SRContributions } from "./SRContribution"
import { MTFContributions } from "./MTFContribution"
import { ReasoningTimeline } from "./ReasoningTimeline"
import { DecisionFlow } from "./DecisionFlow"
import { WeightDistribution } from "./WeightDistribution"
import { ConfidenceGauge } from "./ConfidenceGauge"
import { ConflictAnalysis } from "./ConflictAnalysis"
import { WarningPanel } from "./WarningPanel"
import { DecisionMatrix } from "./DecisionMatrix"
import { Skeleton } from "@/components/ui/skeleton"
import { AlertCircle, RefreshCw, BrainCircuit, ChevronDown, ChevronRight } from "lucide-react"

export function ExplainabilityDashboard() {
  const explain = useExplainability()
  const { data, isLoading, error, view, toggleSection } = explain

  if (error && !data) {
    return (
      <div className="flex flex-col items-center justify-center h-64 gap-2">
        <AlertCircle className="w-8 h-8 text-red-500" />
        <div className="text-sm text-red-500">Failed to load explainability data</div>
        <button onClick={() => explain.refetch()} className="flex items-center gap-1 text-xs text-muted-foreground hover:text-foreground">
          <RefreshCw className="w-3 h-3" /> Retry
        </button>
      </div>
    )
  }

  return (
    <div className="space-y-3">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <BrainCircuit className="w-4 h-4 text-primary" />
          <h2 className="text-sm font-bold">AI Explainability Center</h2>
        </div>
        {data?.timestamp && (
          <span className="text-[8px] text-muted-foreground">{new Date(data.timestamp).toLocaleTimeString()}</span>
        )}
      </div>

      {isLoading && !data ? (
        <div className="space-y-2">
          {Array.from({ length: 6 }).map((_, i) => <Skeleton key={i} className="h-24 rounded-lg" />)}
        </div>
      ) : data ? (
        <>
          {/* Decision Flow */}
          {view.showDecisionFlow && (
            <DecisionFlow
              score={data.score}
              confidence={data.confidence}
              hasTradePlan={!!data.direction && data.direction !== "NONE"}
              decision={data.decision}
            />
          )}

          {/* Decision Summary */}
          <DecisionBreakdown
            decision={data.decision}
            score={data.score}
            confidence={data.confidence}
            riskLevel={data.riskLevel}
            institutionalBias={data.institutionalBias}
            marketCondition={data.marketCondition}
            tradingPermission={data.tradingPermission}
            direction={data.direction}
            timestamp={data.timestamp}
          />

          {/* Warnings */}
          <WarningPanel warnings={data.warnings} />

          {/* Two-column layout */}
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-3">
            <ScoreBreakdown items={data.scoreBreakdown} />
            <WeightDistribution items={data.scoreBreakdown} />
          </div>

          <div className="grid grid-cols-1 lg:grid-cols-2 gap-3">
            <ConfidenceBreakdown factors={data.confidenceFactors} confidence={data.confidence} />
            {view.showConfidenceGauge && (
              <div className="rounded-lg border bg-card p-3 flex items-center justify-center">
                <ConfidenceGauge confidence={data.confidence} />
              </div>
            )}
          </div>

          <div className="grid grid-cols-1 lg:grid-cols-2 gap-3">
            <RiskBreakdown factors={data.riskFactors} />
            <MarketContextTree nodes={data.marketContext} />
          </div>

          {/* Collapsible sections */}
          {[
            { key: "indicators", title: "Indicator Contributions", content: <IndicatorContributions indicators={data.indicators} /> },
            { key: "patterns", title: "Pattern Contributions", content: <PatternContributions patterns={data.patterns} /> },
            { key: "structure", title: "Structure Contributions", content: <StructureContributions items={data.structures} /> },
            { key: "sr", title: "Support & Resistance", content: <SRContributions items={data.srContributions} /> },
            { key: "mtf", title: "Multi-Timeframe", content: <MTFContributions items={data.mtfContributions} /> },
          ].map((section) => (
            <div key={section.key} className="rounded-lg border bg-card overflow-hidden">
              <button
                onClick={() => toggleSection(section.key)}
                className="flex items-center gap-2 w-full px-3 py-2 text-[9px] font-medium text-muted-foreground hover:text-foreground transition-colors"
              >
                {view.expandedSections[section.key] ? <ChevronDown className="w-3 h-3" /> : <ChevronRight className="w-3 h-3" />}
                {section.title}
              </button>
              {view.expandedSections[section.key] && <div className="px-3 pb-3">{section.content}</div>}
            </div>
          ))}

          {/* Non-collapsible */}
          <ConflictAnalysis conflicts={data.conflicts} />
          <ReasoningTimeline events={data.reasoning} />
          <DecisionMatrix rows={data.matrix} />
        </>
      ) : (
        <div className="flex items-center justify-center h-48 text-[10px] text-muted-foreground">No AI decision data available. Ensure the backend is running and generating decisions.</div>
      )}
    </div>
  )
}
