/**
 * settingsService.ts
 *
 * Settings export/import, backup/restore, and validation.
 *
 * Uses Zustand persist for storage — no backend API required for settings.
 */

// Dynamic property access for settings sections is inherently loosely typed
/* eslint-disable @typescript-eslint/no-explicit-any */

import { useSettingsStore } from "@/store/useSettingsStore"

export interface SettingsExport {
  version: string
  exportedAt: string
  settings: Record<string, unknown>
  appVersion: string
}

export const settingsService = {
  /**
   * Export all settings as a downloadable JSON object.
   */
  exportAll(): SettingsExport {
    const state = useSettingsStore.getState()
    return {
      version: "1.0",
      exportedAt: new Date().toISOString(),
      settings: {
        general: state.general,
        appearance: state.appearance,
        chart: state.chart,
        indicators: state.indicators,
        overlays: state.overlays,
        tradePlanner: state.tradePlanner,
        risk: state.risk,
        replay: state.replay,
        scanner: state.scanner,
        notifications: state.notifications,
        portfolio: state.portfolio,
        hotkeys: state.hotkeys,
        workspaces: state.workspaces,
      },
      appVersion: state.system.frontendVersion,
    }
  },

  /**
   * Import settings from a JSON object.
   * Only imports known sections to avoid injection.
   */
  importAll(data: SettingsExport): { success: boolean; errors: string[] } {
    const errors: string[] = []
    const store = useSettingsStore.getState()
    const settings = data.settings

    if (!settings || typeof settings !== "object") {
      return { success: false, errors: ["Invalid settings format"] }
    }

    const allowedSections = [
      "general", "appearance", "chart", "indicators", "overlays",
      "tradePlanner", "risk", "replay", "scanner", "notifications", "portfolio",
    ]

    const storeState = useSettingsStore.getState() as unknown as Record<string, unknown>

    for (const section of allowedSections) {
      const secData = (settings as Record<string, unknown>)[section]
      if (secData && typeof secData === "object") {
        try {
          const key = `update${section.charAt(0).toUpperCase() + section.slice(1)}`
          const updateFn = (storeState as any)[key]
          if (typeof updateFn === "function") {
            updateFn(secData)
          }
        } catch {
          errors.push(`Failed to import section: ${section}`)
        }
      }
    }

    if (Array.isArray(settings.hotkeys)) {
      store.resetHotkeys()
      for (const hk of settings.hotkeys as Array<{ id: string; keys: string }>) {
        if (hk.id && hk.keys) store.updateHotkey(hk.id, hk.keys)
      }
    }

    return { success: errors.length === 0, errors }
  },

  /**
   * Export settings as a downloadable file.
   */
  downloadExport(): void {
    const data = this.exportAll()
    const blob = new Blob([JSON.stringify(data, null, 2)], { type: "application/json" })
    const url = URL.createObjectURL(blob)
    const a = document.createElement("a")
    a.href = url
    a.download = `marketmind-settings-${new Date().toISOString().split("T")[0]}.json`
    a.click()
    URL.revokeObjectURL(url)
  },

  /**
   * Get system information.
   */
  getSystemInfo() {
    return useSettingsStore.getState().system
  },

  /**
   * Validate a hex color value.
   */
  isValidColor(color: string): boolean {
    return /^#[0-9a-fA-F]{6}$/.test(color)
  },

  /**
   * Detect conflicts in hotkeys.
   */
  detectConflicts(): Array<{ keys: string; conflicts: string[] }> {
    const hotkeys = useSettingsStore.getState().hotkeys
    const keyMap = new Map<string, string[]>()

    for (const hk of hotkeys) {
      if (!keyMap.has(hk.keys)) keyMap.set(hk.keys, [])
      keyMap.get(hk.keys)!.push(hk.label)
    }

    const conflicts: Array<{ keys: string; conflicts: string[] }> = []
    for (const [keys, labels] of keyMap) {
      if (labels.length > 1) conflicts.push({ keys, conflicts: labels })
    }
    return conflicts
  },
}
