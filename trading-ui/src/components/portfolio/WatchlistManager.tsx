"use client"

import { useState } from "react"
import { cn } from "@/lib/utils"
import { Plus, X } from "lucide-react"
import type { WatchlistGroup } from "@/store/usePortfolioStore"

interface WatchlistManagerProps {
  watchlists: WatchlistGroup[]
  selectedId: string | null
  onSelect: (id: string | null) => void
  onAdd: (group: WatchlistGroup) => void
  onRemove: (id: string) => void
  onAddSymbol: (groupId: string, symbol: string) => void
  onRemoveSymbol: (groupId: string, symbol: string) => void
  className?: string
}

const COLORS = ["#6366f1", "#22c55e", "#f59e0b", "#ef4444", "#ec4899", "#06b6d4"]

export function WatchlistManager({ watchlists, selectedId, onSelect, onAdd, onRemove, onAddSymbol, onRemoveSymbol, className }: WatchlistManagerProps) {
  const [newName, setNewName] = useState("")
  const [newSymbol, setNewSymbol] = useState("")
  const [addingTo, setAddingTo] = useState<string | null>(null)

  const handleAddList = () => {
    if (!newName.trim()) return
    onAdd({ id: `wl_${Date.now()}`, name: newName.trim(), symbols: [], color: COLORS[watchlists.length % COLORS.length] })
    setNewName("")
  }

  return (
    <div className={cn("rounded-lg border bg-card p-2", className)}>
      <div className="text-[9px] font-medium text-muted-foreground uppercase tracking-wider mb-1">Watchlists</div>

      <div className="space-y-0.5">
        {watchlists.map((wl) => (
          <div key={wl.id}>
            <div className={cn("flex items-center gap-1 px-1.5 py-1 rounded text-[10px] cursor-pointer transition-colors", selectedId === wl.id ? "bg-muted/30" : "hover:bg-muted/20")}>
              <div className="w-2 h-2 rounded-full shrink-0" style={{ backgroundColor: wl.color || "#888" }} />
              <span onClick={() => onSelect(selectedId === wl.id ? null : wl.id)} className="flex-1 font-medium">{wl.name}</span>
              <span className="text-[8px] text-muted-foreground">{wl.symbols.length}</span>
              <button onClick={() => setAddingTo(addingTo === wl.id ? null : wl.id)} className="p-0.5 text-muted-foreground hover:text-foreground">
                <Plus className="w-2.5 h-2.5" />
              </button>
              <button onClick={() => onRemove(wl.id)} className="p-0.5 text-muted-foreground hover:text-red-500">
                <X className="w-2.5 h-2.5" />
              </button>
            </div>

            {/* Symbols */}
            {selectedId === wl.id && (
              <div className="ml-4 space-y-0.5 mt-0.5">
                {wl.symbols.map((sym) => (
                  <div key={sym} className="flex items-center gap-1 text-[9px] text-muted-foreground px-1.5 py-0.5">
                    <span className="flex-1">{sym}</span>
                    <button onClick={() => onRemoveSymbol(wl.id, sym)} className="p-0.5 hover:text-red-500">
                      <X className="w-2 h-2" />
                    </button>
                  </div>
                ))}
                {addingTo === wl.id && (
                  <div className="flex items-center gap-1">
                    <input
                      type="text"
                      value={newSymbol}
                      onChange={(e) => setNewSymbol(e.target.value.toUpperCase())}
                      placeholder="Symbol"
                      className="h-5 w-20 rounded border bg-muted/50 px-1 text-[8px] focus:outline-none"
                      onKeyDown={(e) => {
                        if (e.key === "Enter" && newSymbol) {
                          onAddSymbol(wl.id, newSymbol); setNewSymbol("")
                        }
                      }}
                    />
                    <button
                      onClick={() => { if (newSymbol) { onAddSymbol(wl.id, newSymbol); setNewSymbol("") } }}
                      className="px-1 py-0.5 rounded text-[8px] bg-primary/20 text-primary"
                    >Add</button>
                  </div>
                )}
              </div>
            )}
          </div>
        ))}
      </div>

      {/* New watchlist */}
      <div className="flex items-center gap-1 mt-1 pt-1 border-t">
        <input
          type="text"
          value={newName}
          onChange={(e) => setNewName(e.target.value)}
          placeholder="New list..."
          className="h-6 flex-1 rounded border bg-muted/50 px-1.5 text-[9px] focus:outline-none"
          onKeyDown={(e) => e.key === "Enter" && handleAddList()}
        />
        <button onClick={handleAddList} className="rounded p-1 text-muted-foreground hover:text-foreground hover:bg-accent transition-colors">
          <Plus className="w-3 h-3" />
        </button>
      </div>
    </div>
  )
}
