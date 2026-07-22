"use client"

import { useState, useMemo } from "react"
import { useQuery } from "@tanstack/react-query"
import { marketIntelligenceService } from "@/services/marketIntelligenceService"
import { BrainCircuit, Calendar, Newspaper, TrendingUp, LineChart, Grid, MessageSquare, FileText, Star, BarChart3 } from "lucide-react"
import { cn } from "@/lib/utils"

const TABS = [
  { id: "overview", label: "Market Overview", icon: <BarChart3 className="w-3.5 h-3.5" /> },
  { id: "economy", label: "Economic Calendar", icon: <Calendar className="w-3.5 h-3.5" /> },
  { id: "news", label: "News Intelligence", icon: <Newspaper className="w-3.5 h-3.5" /> },
  { id: "flow", label: "Institutional Flow", icon: <TrendingUp className="w-3.5 h-3.5" /> },
  { id: "options", label: "Options Intel", icon: <LineChart className="w-3.5 h-3.5" /> },
  { id: "sectors", label: "Sectors", icon: <Grid className="w-3.5 h-3.5" /> },
  { id: "copilot", label: "AI Copilot", icon: <MessageSquare className="w-3.5 h-3.5" /> },
  { id: "briefing", label: "Briefing", icon: <FileText className="w-3.5 h-3.5" /> },
  { id: "watchlist", label: "Watchlist Intel", icon: <Star className="w-3.5 h-3.5" /> },
]

export function MarketIntelligenceDashboard() {
  const [activeTab, setActiveTab] = useState("overview")

  const { data: regime } = useQuery({ queryKey: ["intel-regime"], queryFn: () => marketIntelligenceService.getMarketRegime(), refetchInterval: 60_000, staleTime: 30_000 })
  const { data: events } = useQuery({ queryKey: ["intel-events"], queryFn: () => marketIntelligenceService.getEconomicCalendar("IN"), refetchInterval: 120_000, staleTime: 60_000 })
  const { data: news } = useQuery({ queryKey: ["intel-news"], queryFn: () => marketIntelligenceService.getNews("NIFTY 50"), refetchInterval: 60_000, staleTime: 30_000 })
  const { data: flow } = useQuery({ queryKey: ["intel-flow"], queryFn: () => marketIntelligenceService.getInstitutionalFlow("NIFTY 50"), refetchInterval: 60_000, staleTime: 30_000 })
  const { data: sectors } = useQuery({ queryKey: ["intel-sectors"], queryFn: () => marketIntelligenceService.getSectorData(), refetchInterval: 60_000, staleTime: 30_000 })

  const overviewContent = useMemo(() => (
    <div className="space-y-3">
      {/* Market Regime */}
      {regime && (
        <div className="rounded-lg border bg-card p-3">
          <div className="text-[9px] font-medium text-muted-foreground uppercase tracking-wider mb-2">Market Regime</div>
          <div className="grid grid-cols-2 sm:grid-cols-5 gap-2">
            <div className="text-center">
              <div className="text-[8px] text-muted-foreground">Regime</div>
              <div className={cn("text-xs font-bold mt-0.5", regime.riskOn ? "text-emerald-500" : "text-red-500")}>{regime.regime}</div>
            </div>
            <div className="text-center">
              <div className="text-[8px] text-muted-foreground">Volatility</div>
              <div className="text-xs font-bold mt-0.5">{regime.volatility}</div>
            </div>
            <div className="text-center">
              <div className="text-[8px] text-muted-foreground">Breadth</div>
              <div className="text-xs font-bold mt-0.5">{regime.breadth.toFixed(1)}%</div>
            </div>
            <div className="text-center">
              <div className="text-[8px] text-muted-foreground">Correlation</div>
              <div className="text-xs font-bold mt-0.5">{regime.correlation.toFixed(2)}</div>
            </div>
            <div className="text-center">
              <div className="text-[8px] text-muted-foreground">Risk</div>
              <div className={cn("text-xs font-bold mt-0.5", regime.riskOn ? "text-emerald-500" : "text-red-500")}>{regime.riskOn ? "Risk On" : "Risk Off"}</div>
            </div>
          </div>
        </div>
      )}

      {/* Sectors */}
      {sectors && sectors.length > 0 && (
        <div className="rounded-lg border bg-card p-3">
          <div className="text-[9px] font-medium text-muted-foreground uppercase tracking-wider mb-2">Sector Performance</div>
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-1.5">
            {sectors.slice(0, 8).map((s) => (
              <div key={s.name} className="flex items-center justify-between rounded bg-muted/20 px-2 py-1">
                <span className="text-[9px]">{s.name}</span>
                <span className={cn("text-[9px] font-mono font-medium", s.change >= 0 ? "text-emerald-500" : "text-red-500")}>
                  {s.change >= 0 ? "+" : ""}{s.change.toFixed(2)}%
                </span>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Economic Events */}
      {events && events.length > 0 && (
        <div className="rounded-lg border bg-card p-3">
          <div className="text-[9px] font-medium text-muted-foreground uppercase tracking-wider mb-2">Upcoming Economic Events</div>
          <div className="space-y-1">
            {events.slice(0, 5).map((ev) => (
              <div key={ev.id} className="flex items-center gap-2 text-[9px]">
                <span className={cn("w-1.5 h-1.5 rounded-full", ev.impact === "high" ? "bg-red-500" : ev.impact === "medium" ? "bg-amber-500" : "bg-blue-500")} />
                <span className="font-medium w-20">{ev.country}</span>
                <span className="flex-1">{ev.title}</span>
                <span className="text-muted-foreground">{ev.date ? new Date(ev.date).toLocaleDateString() : ""}</span>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Institutional Flow */}
      {flow && (
        <div className="rounded-lg border bg-card p-3">
          <div className="text-[9px] font-medium text-muted-foreground uppercase tracking-wider mb-2">Institutional Flow</div>
          <div className="grid grid-cols-3 gap-2 text-center">
            <div>
              <div className="text-[8px] text-muted-foreground">FII Net</div>
              <div className={cn("text-xs font-mono font-bold mt-0.5", flow.fiiNet >= 0 ? "text-emerald-500" : "text-red-500")}>
                {flow.fiiNet >= 0 ? "+" : ""}{flow.fiiNet.toFixed(0)}
              </div>
            </div>
            <div>
              <div className="text-[8px] text-muted-foreground">DII Net</div>
              <div className={cn("text-xs font-mono font-bold mt-0.5", flow.diiNet >= 0 ? "text-emerald-500" : "text-red-500")}>
                {flow.diiNet >= 0 ? "+" : ""}{flow.diiNet.toFixed(0)}
              </div>
            </div>
            <div>
              <div className="text-[8px] text-muted-foreground">Delivery %</div>
              <div className="text-xs font-mono font-bold mt-0.5">{flow.deliveryPercent.toFixed(1)}%</div>
            </div>
          </div>
        </div>
      )}

      {/* AI Summary */}
      <div className="rounded-lg border bg-card p-3">
        <div className="flex items-center gap-1 text-[9px] font-medium text-muted-foreground uppercase tracking-wider mb-1">
          <BrainCircuit className="w-3 h-3" /> AI Summary
        </div>
        <p className="text-[10px] leading-relaxed">
          Market regime is {regime?.regime?.toLowerCase() ?? "unknown"} with {regime?.volatility?.toLowerCase() ?? "normal"} volatility.
          Institutional flows show {flow ? (flow.fiiNet > 0 ? "FII buying" : "FII selling") : "mixed"} activity.
          {sectors && sectors.length > 0 ? ` Leading sectors: ${sectors.filter((s) => s.change > 0).slice(0, 3).map((s) => s.name).join(", ")}.` : ""}
        </p>
      </div>
    </div>
  ), [regime, events, news, flow, sectors])

  const newsContent = useMemo(() => (
    <div className="space-y-1">
      {(!news || news.length === 0) ? (
        <div className="rounded-lg border bg-card p-6 text-center text-[10px] text-muted-foreground">No news data available</div>
      ) : (
        news.slice(0, 10).map((item) => (
          <div key={item.id} className="rounded-lg border bg-card p-2 space-y-1">
            <div className="flex items-center justify-between">
              <span className="text-[10px] font-medium">{item.title}</span>
              <span className={cn("text-[8px] px-1 py-0.5 rounded font-medium", item.sentiment === "positive" ? "bg-emerald-500/10 text-emerald-500" : item.sentiment === "negative" ? "bg-red-500/10 text-red-500" : "bg-muted/30 text-muted-foreground")}>
                {item.sentimentScore.toFixed(2)}
              </span>
            </div>
            <div className="text-[8px] text-muted-foreground">{item.summary}</div>
            <div className="flex items-center gap-2 text-[8px] text-muted-foreground">
              <span>{item.source}</span>
              <span>{item.expectedImpact}</span>
              <span>{new Date(item.publishedAt).toLocaleString()}</span>
            </div>
          </div>
        ))
      )}
    </div>
  ), [news])

  return (
    <div className="space-y-3">
      <div className="flex items-center gap-2">
        <BrainCircuit className="w-4 h-4 text-primary" />
        <h2 className="text-sm font-bold">Market Intelligence</h2>
      </div>

      <div className="flex items-center gap-1 border-b overflow-x-auto">
        {TABS.map((tab) => (
          <button key={tab.id} onClick={() => setActiveTab(tab.id)}
            className={cn("flex items-center gap-1 px-3 py-1.5 text-[9px] font-medium transition-colors border-b-2 -mb-px whitespace-nowrap", activeTab === tab.id ? "text-primary border-primary" : "text-muted-foreground hover:text-foreground border-transparent")}>
            {tab.icon} {tab.label}
          </button>
        ))}
      </div>

      {activeTab === "overview" && overviewContent}
      {activeTab === "news" && newsContent}
      {activeTab === "economy" && (
        <div className="rounded-lg border bg-card p-3">
          <div className="text-[9px] font-medium text-muted-foreground uppercase tracking-wider mb-2">Economic Calendar</div>
          {(!events || events.length === 0) ? (
            <div className="text-center py-6 text-[10px] text-muted-foreground">No upcoming events</div>
          ) : (
            <div className="space-y-1">
              {events.map((ev) => (
                <div key={ev.id} className="flex items-center gap-2 text-[9px] py-1 border-b last:border-0">
                  <span className={cn("w-1.5 h-1.5 rounded-full shrink-0", ev.impact === "high" ? "bg-red-500" : ev.impact === "medium" ? "bg-amber-500" : "bg-blue-500")} />
                  <span className="w-6 text-[8px] text-muted-foreground">{ev.country}</span>
                  <span className="flex-1 font-medium">{ev.title}</span>
                  <span className="text-muted-foreground w-16 text-right">{ev.previous ?? "—"}</span>
                  <span className="w-16 text-right">{ev.forecast ?? "—"}</span>
                  <span className={cn("text-[8px] px-1 py-0.5 rounded", ev.impact === "high" ? "bg-red-500/10 text-red-500" : ev.impact === "medium" ? "bg-amber-500/10 text-amber-500" : "bg-blue-500/10 text-blue-500")}>
                    {ev.impact}
                  </span>
                </div>
              ))}
            </div>
          )}
        </div>
      )}
      {activeTab === "copilot" && (
        <div className="rounded-lg border bg-card p-6 text-center">
          <MessageSquare className="w-8 h-8 text-muted-foreground/30 mx-auto mb-2" />
          <div className="text-[10px] text-muted-foreground">AI Trading Copilot ready. Ask questions about any trade or market condition.</div>
        </div>
      )}
      {(activeTab !== "overview" && activeTab !== "news" && activeTab !== "economy" && activeTab !== "copilot") && (
        <div className="rounded-lg border bg-card p-6 text-center text-[10px] text-muted-foreground">{TABS.find((t) => t.id === activeTab)?.label} coming soon.</div>
      )}
    </div>
  )
}
