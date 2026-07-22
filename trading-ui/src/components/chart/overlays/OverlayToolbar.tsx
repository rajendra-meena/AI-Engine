"use client"

import { useOverlayStore } from "@/store/useOverlayStore"
import { cn } from "@/lib/utils"

const OVERLAY_BUTTONS = [
  { key: "ema" as const, label: "EMA" },
  { key: "sma" as const, label: "SMA" },
  { key: "vwap" as const, label: "VWAP" },
  { key: "supertrend" as const, label: "SuperT" },
  { key: "patterns" as const, label: "Patterns" },
  { key: "structure" as const, label: "Struct" },
  { key: "bos" as const, label: "BOS" },
  { key: "choch" as const, label: "CHoCH" },
  { key: "sr" as const, label: "S/R" },
  { key: "supplyDemand" as const, label: "S/D" },
  { key: "liquidity" as const, label: "Liq" },
  { key: "ai" as const, label: "AI" },
  { key: "labels" as const, label: "Labels" },
  { key: "targets" as const, label: "Targets" },
]

export function OverlayToolbar() {
  const overlayState = useOverlayStore()

  return (
    <div className="flex items-center gap-1 px-2 py-1 border-b bg-card shrink-0 overflow-x-auto">
      <span className="text-[9px] font-medium text-muted-foreground uppercase tracking-wider mr-1 shrink-0">Overlays</span>
      {OVERLAY_BUTTONS.map((btn) => {
        const active = overlayState[btn.key] as boolean
        return (
          <button
            key={btn.key}
            onClick={() => overlayState.toggle(btn.key)}
            className={cn(
              "px-1.5 py-0.5 text-[10px] rounded transition-colors font-medium shrink-0",
              active
                ? "bg-primary/20 text-primary"
                : "text-muted-foreground hover:bg-accent hover:text-accent-foreground"
            )}
          >
            {btn.label}
          </button>
        )
      })}
      <div className="flex-1" />
      <button
        onClick={() => overlayState.setAll(true)}
        className="px-1.5 py-0.5 text-[9px] text-muted-foreground hover:text-foreground transition-colors shrink-0"
      >
        All
      </button>
      <button
        onClick={() => overlayState.setAll(false)}
        className="px-1.5 py-0.5 text-[9px] text-muted-foreground hover:text-foreground transition-colors shrink-0"
      >
        None
      </button>
    </div>
  )
}
