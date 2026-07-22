"use client"

import { useSettingsStore } from "@/store/useSettingsStore"
import { SettingsSidebar } from "./SettingsSidebar"
import { GeneralSettingsPanel } from "./GeneralSettings"
import { AppearanceSettingsPanel } from "./AppearanceSettings"
import { ChartSettingsPanel } from "./ChartSettings"
import { IndicatorSettingsPanel } from "./IndicatorSettings"
import { OverlaySettingsPanel } from "./OverlaySettings"
import { TradePlannerSettingsPanel } from "./TradePlannerSettings"
import { RiskSettingsPanel } from "./RiskSettings"
import { ReplaySettingsPanel } from "./ReplaySettings"
import { ScannerSettingsPanel } from "./ScannerSettings"
import { NotificationPrefsPanel } from "./NotificationPrefsSettings"
import { PortfolioPrefsPanel } from "./PortfolioPrefsSettings"
import { HotkeySettingsPanel } from "./HotkeySettings"
import { BackupRestorePanel } from "./BackupRestore"
import { AboutSystemPanel } from "./AboutSystem"
import { Settings } from "lucide-react"

export function SettingsPage() {
  const store = useSettingsStore()

  const renderSection = () => {
    switch (store.activeSection) {
      case "general": return <GeneralSettingsPanel settings={store.general} onUpdate={store.updateGeneral} />
      case "appearance": return <AppearanceSettingsPanel settings={store.appearance} onUpdate={store.updateAppearance} />
      case "chart": return <ChartSettingsPanel settings={store.chart} onUpdate={store.updateChart} />
      case "indicators": return <IndicatorSettingsPanel settings={store.indicators} onUpdate={store.updateIndicators} />
      case "overlays": return <OverlaySettingsPanel settings={store.overlays} onUpdate={store.updateOverlays} />
      case "tradePlanner": return <TradePlannerSettingsPanel settings={store.tradePlanner} onUpdate={store.updateTradePlanner} />
      case "risk": return <RiskSettingsPanel settings={store.risk} onUpdate={store.updateRisk} />
      case "replay": return <ReplaySettingsPanel settings={store.replay} onUpdate={store.updateReplay} />
      case "scanner": return <ScannerSettingsPanel settings={store.scanner} onUpdate={store.updateScanner} />
      case "notifications": return <NotificationPrefsPanel settings={store.notifications} onUpdate={store.updateNotificationPrefs} />
      case "portfolio": return <PortfolioPrefsPanel settings={store.portfolio} onUpdate={store.updatePortfolioPrefs} />
      case "hotkeys": return <HotkeySettingsPanel hotkeys={store.hotkeys} onUpdate={store.updateHotkey} onReset={store.resetHotkeys} />
      case "backup": return <BackupRestorePanel />
      case "about": return <AboutSystemPanel />
      default: return <GeneralSettingsPanel settings={store.general} onUpdate={store.updateGeneral} />
    }
  }

  return (
    <div className="flex h-full rounded-lg border bg-card overflow-hidden">
      <SettingsSidebar
        activeSection={store.activeSection}
        searchQuery={store.searchQuery}
        onSectionChange={store.setActiveSection}
        onSearchChange={store.setSearchQuery}
      />

      <div className="flex-1 overflow-y-auto p-4 space-y-4">
        <div className="flex items-center gap-2">
          <Settings className="w-4 h-4 text-primary" />
          <h2 className="text-sm font-bold">Settings</h2>
          {store.dirty && <span className="text-[8px] text-amber-500 ml-auto">Unsaved changes</span>}
        </div>
        {renderSection()}
      </div>
    </div>
  )
}
