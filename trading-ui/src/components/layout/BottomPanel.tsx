"use client"

import { useState, useRef, useCallback } from "react"
import { useLayoutStore } from "@/store/useLayoutStore"
import { cn } from "@/lib/utils"

const TABS = [
  { id: "logs", label: "Logs" },
  { id: "orders", label: "Orders" },
  { id: "trades", label: "Trades" },
  { id: "replay", label: "Replay" },
  { id: "api", label: "API" },
  { id: "websocket", label: "WebSocket" },
]

export function BottomPanel() {
  const { bottomPanelOpen, bottomPanelHeight, toggleBottomPanel, setBottomPanelHeight } = useLayoutStore()
  const [activeTab, setActiveTab] = useState("logs")
  const resizeRef = useRef<HTMLDivElement>(null)

  const handleMouseDown = useCallback(
    (e: React.MouseEvent) => {
      e.preventDefault()
      const startY = e.clientY
      const startH = bottomPanelHeight
      const onMouseMove = (ev: MouseEvent) => setBottomPanelHeight(startH - (ev.clientY - startY))
      const onMouseUp = () => {
        document.removeEventListener("mousemove", onMouseMove)
        document.removeEventListener("mouseup", onMouseUp)
      }
      document.addEventListener("mousemove", onMouseMove)
      document.addEventListener("mouseup", onMouseUp)
    },
    [bottomPanelHeight, setBottomPanelHeight]
  )

  return (
    <div
      className="flex flex-col border-t bg-card shrink-0"
      style={{ height: bottomPanelOpen ? bottomPanelHeight : 28 }}
      role="region"
      aria-label="Bottom panel"
    >
      <div
        ref={resizeRef}
        onMouseDown={handleMouseDown}
        className="h-1 cursor-row-resize hover:bg-primary/50 transition-colors shrink-0"
        role="separator"
        aria-orientation="horizontal"
      />

      <div className="flex items-center border-b shrink-0">
        {TABS.map((tab) => (
          <button
            key={tab.id}
            onClick={() => setActiveTab(tab.id)}
            className={cn(
              "px-3 py-1.5 text-[11px] font-medium transition-colors border-r",
              activeTab === tab.id
                ? "bg-muted/50 text-foreground"
                : "text-muted-foreground hover:text-foreground hover:bg-accent/50"
            )}
          >
            {tab.label}
          </button>
        ))}
        <div className="flex-1" />
        <button
          onClick={toggleBottomPanel}
          className="px-2 py-1 text-[10px] text-muted-foreground hover:text-foreground"
          aria-label={bottomPanelOpen ? "Minimize panel" : "Expand panel"}
        >
          {bottomPanelOpen ? "-" : "+"}
        </button>
      </div>

      <div className="flex-1 overflow-y-auto p-3 text-xs text-muted-foreground">
        {bottomPanelOpen ? (
          <div className="space-y-1 font-mono text-[11px]">
            <span className="text-green-500">[INFO]</span> System initialized<br />
            <span className="text-green-500">[INFO]</span> EventBus started<br />
            <span className="text-green-500">[INFO]</span> WebSocket gateway connected<br />
            <span className="text-yellow-500">[WARN]</span> Waiting for market data...<br />
          </div>
        ) : (
          <div className="text-[10px] text-muted-foreground/50">{activeTab} panel minimized</div>
        )}
      </div>
    </div>
  )
}
