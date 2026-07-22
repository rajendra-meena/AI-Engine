"use client"

import { SettingsSection } from "./SettingsSection"
import { useSettingsStore } from "@/store/useSettingsStore"

export function AboutSystemPanel() {
  const system = useSettingsStore((s) => s.system)

  const rows = [
    { label: "Frontend Version", value: system.frontendVersion },
    { label: "Environment", value: system.environment },
    { label: "Build Date", value: system.buildDate ? new Date(system.buildDate).toLocaleString() : "N/A" },
    { label: "API URL", value: system.apiUrl },
    { label: "WebSocket URL", value: system.wsUrl },
    { label: "Platform", value: system.platform },
    { label: "Browser", value: system.browser.slice(0, 80) + "..." },
  ]

  return (
    <SettingsSection title="About" description="System information">
      <div className="space-y-1">
        {rows.map((row) => (
          <div key={row.label} className="flex items-center justify-between py-0.5">
            <span className="text-[9px] text-muted-foreground">{row.label}</span>
            <span className="text-[9px] font-mono text-right max-w-[60%] truncate">{row.value}</span>
          </div>
        ))}
      </div>
    </SettingsSection>
  )
}
