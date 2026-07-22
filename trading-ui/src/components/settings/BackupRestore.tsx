"use client"

import { useRef } from "react"
import { SettingsSection } from "./SettingsSection"
import { settingsService } from "@/services/settingsService"
import { useSettingsStore } from "@/store/useSettingsStore"

export function BackupRestorePanel() {
  const fileInputRef = useRef<HTMLInputElement>(null)
  const resetAll = useSettingsStore((s) => s.resetAll)

  const handleExport = () => {
    settingsService.downloadExport()
  }

  const handleImport = () => {
    fileInputRef.current?.click()
  }

  const handleFileChange = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (!file) return
    try {
      const text = await file.text()
      const data = JSON.parse(text)
      const result = settingsService.importAll(data)
      if (!result.success) {
        alert("Import errors: " + result.errors.join(", "))
      }
    } catch {
      alert("Invalid settings file")
    }
    e.target.value = ""
  }

  const handleResetAll = () => {
    if (window.confirm("Reset ALL settings to defaults? This cannot be undone.")) {
      resetAll()
    }
  }

  return (
    <SettingsSection title="Backup & Restore" description="Export or import your settings">
      <input ref={fileInputRef} type="file" accept=".json" onChange={handleFileChange} className="hidden" />

      <div className="grid grid-cols-2 gap-2">
        <button onClick={handleExport}
          className="h-8 rounded border bg-muted/30 text-[10px] font-medium hover:bg-accent transition-colors">
          Export Settings
        </button>
        <button onClick={handleImport}
          className="h-8 rounded border bg-muted/30 text-[10px] font-medium hover:bg-accent transition-colors">
          Import Settings
        </button>
      </div>

      <div className="border-t pt-2 mt-2">
        <button onClick={handleResetAll}
          className="w-full h-8 rounded border border-red-500/30 bg-red-500/10 text-[10px] font-medium text-red-500 hover:bg-red-500/20 transition-colors">
          Reset All to Defaults
        </button>
        <p className="text-[8px] text-muted-foreground mt-1 text-center">This action cannot be undone</p>
      </div>
    </SettingsSection>
  )
}
