"use client"

import { cn } from "@/lib/utils"
import type { ChartLayout } from "@/store/useWorkspaceStore"

interface LayoutSelectorProps {
  current: ChartLayout
  onSelect: (layout: ChartLayout) => void
}

const LAYOUTS: { id: ChartLayout; label: string; icon: string }[] = [
  { id: "single", label: "1", icon: "▢" },
  { id: "2h", label: "2H", icon: "▣▣" },
  { id: "2v", label: "2V", icon: "▣▣" },
  { id: "4", label: "4", icon: "⊞" },
  { id: "6", label: "6", icon: "⊞" },
  { id: "8", label: "8", icon: "⊞" },
]

export function LayoutSelector({ current, onSelect }: LayoutSelectorProps) {
  return (
    <div className="flex items-center gap-0.5">
      {LAYOUTS.map((l) => (
        <button
          key={l.id}
          onClick={() => onSelect(l.id)}
          className={cn(
            "w-6 h-6 rounded text-[8px] font-mono font-medium transition-colors flex items-center justify-center",
            current === l.id ? "bg-primary/20 text-primary" : "text-muted-foreground hover:bg-accent hover:text-foreground",
          )}
          title={l.label}
        >
          {l.id === "2h" ? "⫸" : l.id === "2v" ? "⫯" : l.id === "4" ? "⊞" : l.id === "6" ? "⊟" : l.id === "8" ? "⊠" : "⊡"}
        </button>
      ))}
    </div>
  )
}
