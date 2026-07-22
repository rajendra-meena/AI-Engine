"use client"

import { useAnalytics } from "@/hooks/useAnalytics"
import { SummaryCards } from "./SummaryCards"
import { AccuracyChart } from "./AccuracyChart"
import { ConfidenceChart } from "./ConfidenceChart"
import { RiskChart } from "./RiskChart"
import { PatternTable } from "./PatternTable"
import { IndicatorTable } from "./IndicatorTable"
import { TimeframeTable } from "./TimeframeTable"
import { DecisionHistory } from "./DecisionHistory"
import { FilterPanel } from "./FilterPanel"
import { ExportPanel } from "./ExportPanel"
import { Skeleton } from "@/components/ui/skeleton"
import { cn } from "@/lib/utils"
import { AlertCircle, RefreshCw, BarChart3, Activity, Shield, TrendingUp, Grid, Table } from "lucide-react"

export function AnalyticsDashboard() {
  const analytics = useAnalytics()

  const {
    summary, dailyAccuracy, weeklyAccuracy, monthlyAccuracy,
    confidenceDistribution, riskDistribution, timeframeMetrics, decisionHistory,
    loading, error, filters, pagination, view, autoRefresh,
    setFilters, resetFilters, setSort, setPage, setView, setAutoRefresh,
    refresh,
  } = analytics

  if (error && !loading) {
    return (
      <div className="flex flex-col items-center justify-center h-64 gap-2">
        <AlertCircle className="w-8 h-8 text-red-500" />
        <div className="text-sm text-red-500">Failed to load analytics</div>
        <button onClick={refresh} className="flex items-center gap-1 text-xs text-muted-foreground hover:text-foreground">
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
          <BarChart3 className="w-4 h-4 text-primary" />
          <h2 className="text-sm font-bold">AI Prediction Analytics</h2>
        </div>
        <div className="flex items-center gap-2">
          {/* Chart type toggle */}
          <div className="flex items-center rounded-md border overflow-hidden">
            {(["bar", "line", "area"] as const).map((type) => (
              <button
                key={type}
                onClick={() => setView({ accuracyChartType: type })}
                className={cn("px-2 py-1 text-[9px] font-medium transition-colors", view.accuracyChartType === type ? "bg-primary/20 text-primary" : "text-muted-foreground hover:bg-accent")}
              >
                {type.charAt(0).toUpperCase() + type.slice(1)}
              </button>
            ))}
          </div>
          <ExportPanel onExport={(format) => {
            analytics.exportAll().then((data) => {
              const blob = new Blob([JSON.stringify(data, null, 2)], { type: "application/json" })
              const url = URL.createObjectURL(blob)
              const a = document.createElement("a")
              a.href = url; a.download = `ai-analytics-${new Date().toISOString().split("T")[0]}.${format}`
              a.click(); URL.revokeObjectURL(url)
            })
          }} />
        </div>
      </div>

      {/* Filters */}
      <FilterPanel
        filters={filters}
        onFilterChange={setFilters}
        onReset={resetFilters}
        onRefresh={refresh}
        autoRefresh={autoRefresh}
        onAutoRefreshChange={setAutoRefresh}
      />

      {/* Summary Cards */}
      {loading ? (
        <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 gap-2">
          {Array.from({ length: 8 }).map((_, i) => <Skeleton key={i} className="h-20 rounded-lg" />)}
        </div>
      ) : (
        <SummaryCards metrics={summary} />
      )}

      {/* View tabs */}
      <div className="flex items-center gap-1 border-b">
        {[
          { id: "accuracy" as const, label: "Accuracy", icon: <TrendingUp className="w-3 h-3" /> },
          { id: "confidence" as const, label: "Confidence", icon: <Activity className="w-3 h-3" /> },
          { id: "risk" as const, label: "Risk", icon: <Shield className="w-3 h-3" /> },
          { id: "timeframes" as const, label: "Timeframes", icon: <Grid className="w-3 h-3" /> },
          { id: "patterns" as const, label: "Patterns", icon: <Table className="w-3 h-3" /> },
          { id: "indicators" as const, label: "Indicators", icon: <BarChart3 className="w-3 h-3" /> },
        ].map((tab) => (
          <button
            key={tab.id}
            onClick={() => setView({ [tab.id === "accuracy" ? "accuracyChart" : tab.id === "confidence" ? "showConfidence" : tab.id === "risk" ? "showRisk" : tab.id === "timeframes" ? "showTimeframes" : tab.id === "patterns" ? "showPatterns" : "showIndicators"]: true } as Record<string, unknown>)}
            className={cn(
              "flex items-center gap-1 px-3 py-1.5 text-[9px] font-medium transition-colors border-b-2 -mb-px",
              "text-muted-foreground hover:text-foreground border-transparent"
            )}
          >
            {tab.icon} {tab.label}
          </button>
        ))}
        <div className="flex-1" />
        {/* Timeframe toggle for accuracy chart */}
        <div className="flex items-center gap-0.5">
          {(["daily", "weekly", "monthly"] as const).map((period) => (
            <button
              key={period}
              onClick={() => setView({ accuracyChart: period })}
              className={cn("px-2 py-1 text-[8px] font-medium rounded transition-colors", view.accuracyChart === period ? "bg-muted text-foreground" : "text-muted-foreground hover:text-foreground")}
            >
              {period.charAt(0).toUpperCase() + period.slice(1)}
            </button>
          ))}
        </div>
      </div>

      {/* Charts grid */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-3">
        {/* Accuracy Chart */}
        <div className="space-y-1">
          <div className="text-[10px] font-medium text-muted-foreground uppercase tracking-wider px-1">
            {view.accuracyChart.charAt(0).toUpperCase() + view.accuracyChart.slice(1)} Accuracy
          </div>
          {loading ? (
            <Skeleton className="h-48 rounded-lg" />
          ) : (
            <AccuracyChart
              data={view.accuracyChart === "daily" ? dailyAccuracy : view.accuracyChart === "weekly" ? weeklyAccuracy : monthlyAccuracy}
              chartType={view.accuracyChartType}
            />
          )}
        </div>

        {/* Confidence Chart */}
        {loading ? (
          <Skeleton className="h-48 rounded-lg" />
        ) : (
          <ConfidenceChart data={confidenceDistribution} />
        )}
      </div>

      {/* Risk + Timeframes */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-3">
        {loading ? <Skeleton className="h-48 rounded-lg" /> : <RiskChart data={riskDistribution} />}
        {loading ? <Skeleton className="h-48 rounded-lg" /> : <TimeframeTable data={timeframeMetrics} />}
      </div>

      {/* Patterns + Indicators */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-3">
        <PatternTable data={[]} />
        <IndicatorTable data={[]} />
      </div>

      {/* Decision History */}
      <DecisionHistory
        data={decisionHistory}
        page={pagination.page}
        pageSize={pagination.pageSize}
        total={decisionHistory.length}
        onPageChange={setPage}
        onSort={(field) => setSort({ field: field as "time" | "score" | "confidence" | "direction" | "risk" | "decision" | "result" | "pnl", direction: "desc" })}
      />
    </div>
  )
}
