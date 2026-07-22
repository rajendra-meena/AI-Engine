"use client"

import { usePortfolio } from "@/hooks/usePortfolio"
import { PortfolioDashboard } from "./PortfolioDashboard"
import { OpenPositions } from "./OpenPositions"
import { ClosedTrades } from "./ClosedTrades"
import { OrderEntry } from "./OrderEntry"
import { TradeJournal } from "./TradeJournal"
import { WatchlistManager } from "./WatchlistManager"
import { Briefcase, ListOrdered, History, BookOpen, Star } from "lucide-react"
import { cn } from "@/lib/utils"

const TABS = [
  { id: "overview", label: "Overview", icon: <Briefcase className="w-3.5 h-3.5" /> },
  { id: "positions", label: "Positions", icon: <ListOrdered className="w-3.5 h-3.5" /> },
  { id: "trades", label: "Trades", icon: <History className="w-3.5 h-3.5" /> },
  { id: "journal", label: "Journal", icon: <BookOpen className="w-3.5 h-3.5" /> },
  { id: "watchlist", label: "Watchlist", icon: <Star className="w-3.5 h-3.5" /> },
]

export function PortfolioPage() {
  const portfolio = usePortfolio()

  return (
    <div className="space-y-3">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Briefcase className="w-4 h-4 text-primary" />
          <h2 className="text-sm font-bold">Portfolio & Paper Trading</h2>
        </div>
      </div>

      {/* Tabs */}
      <div className="flex items-center gap-1 border-b">
        {TABS.map((tab) => (
          <button
            key={tab.id}
            onClick={() => portfolio.setActiveTab(tab.id)}
            className={cn(
              "flex items-center gap-1 px-3 py-1.5 text-[9px] font-medium transition-colors border-b-2 -mb-px",
              portfolio.activeTab === tab.id
                ? "text-primary border-primary"
                : "text-muted-foreground hover:text-foreground border-transparent",
            )}
          >
            {tab.icon} {tab.label}
          </button>
        ))}
      </div>

      {/* Content */}
      <div className="flex gap-3">
        {/* Main */}
        <div className="flex-1 min-w-0">
          {portfolio.activeTab === "overview" && (
            <PortfolioDashboard summary={portfolio.summary} onTabChange={portfolio.setActiveTab} />
          )}

          {portfolio.activeTab === "positions" && (
            <OpenPositions
              positions={portfolio.positions}
              onClose={(pos) => portfolio.closePosition(pos)}
              onModifySL={(id) => portfolio.modifySL(id, 0)}
              onBreakEven={portfolio.moveToBreakEven}
            />
          )}

          {portfolio.activeTab === "trades" && (
            <ClosedTrades trades={portfolio.closedTrades} />
          )}

          {portfolio.activeTab === "journal" && (
            <TradeJournal entries={portfolio.journal} />
          )}

          {portfolio.activeTab === "watchlist" && (
            <WatchlistManager
              watchlists={portfolio.watchlists}
              selectedId={null}
              onSelect={() => {}}
              onAdd={portfolio.addWatchlist}
              onRemove={portfolio.removeWatchlist}
              onAddSymbol={portfolio.addToWatchlist}
              onRemoveSymbol={portfolio.removeFromWatchlist}
            />
          )}
        </div>

        {/* Order Entry Sidebar */}
        <div className="w-64 shrink-0 hidden lg:block">
          <OrderEntry onPlaceOrder={(req) => { portfolio.placeOrder(req) }} />
        </div>
      </div>
    </div>
  )
}
