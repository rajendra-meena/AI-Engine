import { create } from "zustand"
import { persist } from "zustand/middleware"

/* ─── Types ─── */

export type ThemeMode = "light" | "dark" | "system"
export type DateTimeFormat = "12h" | "24h"
export type NumberFormat = "en-IN" | "en-US"
export type PositionSizingMode = "fixed" | "risk-based" | "kelly"
export type PnLMode = "absolute" | "percent"
export type DensityMode = "compact" | "normal" | "comfortable"

export interface GeneralSettings {
  appName: string
  language: string
  timezone: string
  dateFormat: DateTimeFormat
  numberFormat: NumberFormat
  autoSave: boolean
  autoUpdate: boolean
}

export interface AppearanceSettings {
  theme: ThemeMode
  accentColor: string
  fontSize: number
  compactMode: boolean
  roundedCorners: boolean
  panelTransparency: boolean
  animations: boolean
  density: DensityMode
}

export interface ChartSettings {
  defaultSymbol: string
  defaultInterval: string
  crosshair: boolean
  grid: boolean
  watermark: boolean
  priceScale: "normal" | "log"
  volume: boolean
  autoScale: boolean
  rightScale: boolean
  leftScale: boolean
  timezone: string
  sessionBreak: boolean
}

export interface IndicatorSettings {
  ema: boolean
  sma: boolean
  rsi: boolean
  macd: boolean
  atr: boolean
  adx: boolean
  vwap: boolean
  supertrend: boolean
  lineWidth: number
  opacity: number
  defaultVisible: boolean
}

export interface OverlaySettings {
  supportResistance: boolean
  supplyDemand: boolean
  swingHighLow: boolean
  trendlines: boolean
  liquidity: boolean
  bos: boolean
  choch: boolean
  aiLabels: boolean
  entryZone: boolean
  targetLines: boolean
  stoploss: boolean
  opacity: number
  labelSize: "sm" | "md" | "lg"
}

export interface TradePlannerSettings {
  defaultCapital: number
  riskPercent: number
  brokerage: number
  slippage: number
  taxes: number
  lotSize: number
  commission: number
  currency: string
  rrPreference: number
  positionSizingMode: PositionSizingMode
}

export interface RiskSettings {
  maxDailyLoss: number
  maxWeeklyLoss: number
  maxOpenPositions: number
  maxExposure: number
  maxDrawdown: number
  stopTrading: boolean
  tradeCooldown: number
}

export interface ReplaySettings {
  defaultSpeed: number
  defaultDays: number
  defaultInterval: string
  autoPause: boolean
  showTimeline: boolean
  showJournal: boolean
  theme: string
}

export interface ScannerSettings {
  refreshInterval: number
  defaultSort: string
  minScore: number
  minConfidence: number
  minRR: number
  watchlist: string[]
  alertRules: boolean
}

export interface NotificationPrefs {
  desktop: boolean
  sound: boolean
  popup: boolean
  grouping: boolean
  autoDelete: boolean
  historyLimit: number
}

export interface PortfolioPrefs {
  paperCapital: number
  defaultAccount: string
  defaultCurrency: string
  autoJournal: boolean
  autoScreenshot: boolean
  pnlMode: PnLMode
}

export interface HotkeyEntry {
  id: string
  label: string
  keys: string
  category: string
}

export interface WorkspaceLayout {
  id: string
  name: string
  sidebarOpen: boolean
  rightPanelOpen: boolean
  bottomPanelOpen: boolean
  activeTab: string
}

export interface BackupState {
  version: string
  exportedAt: string
  settings: Record<string, unknown>
}

export interface SystemInfo {
  frontendVersion: string
  apiUrl: string
  wsUrl: string
  environment: string
  buildDate: string
  browser: string
  platform: string
}

/* ─── Store ─── */

interface SettingsState {
  general: GeneralSettings
  appearance: AppearanceSettings
  chart: ChartSettings
  indicators: IndicatorSettings
  overlays: OverlaySettings
  tradePlanner: TradePlannerSettings
  risk: RiskSettings
  replay: ReplaySettings
  scanner: ScannerSettings
  notifications: NotificationPrefs
  portfolio: PortfolioPrefs
  hotkeys: HotkeyEntry[]
  workspaces: WorkspaceLayout[]
  system: SystemInfo
  activeSection: string
  dirty: boolean
  searchQuery: string

  setActiveSection: (section: string) => void
  setSearchQuery: (q: string) => void
  updateGeneral: (partial: Partial<GeneralSettings>) => void
  updateAppearance: (partial: Partial<AppearanceSettings>) => void
  updateChart: (partial: Partial<ChartSettings>) => void
  updateIndicators: (partial: Partial<IndicatorSettings>) => void
  updateOverlays: (partial: Partial<OverlaySettings>) => void
  updateTradePlanner: (partial: Partial<TradePlannerSettings>) => void
  updateRisk: (partial: Partial<RiskSettings>) => void
  updateReplay: (partial: Partial<ReplaySettings>) => void
  updateScanner: (partial: Partial<ScannerSettings>) => void
  updateNotificationPrefs: (partial: Partial<NotificationPrefs>) => void
  updatePortfolioPrefs: (partial: Partial<PortfolioPrefs>) => void
  updateHotkey: (id: string, keys: string) => void
  resetHotkeys: () => void
  addWorkspace: (ws: WorkspaceLayout) => void
  removeWorkspace: (id: string) => void
  renameWorkspace: (id: string, name: string) => void
  resetSection: (section: string) => void
  resetAll: () => void
  setDirty: (dirty: boolean) => void
}

const DEFAULT_GENERAL: GeneralSettings = {
  appName: "MarketMind AI", language: "en", timezone: "Asia/Kolkata",
  dateFormat: "12h", numberFormat: "en-IN", autoSave: true, autoUpdate: true,
}

const DEFAULT_APPEARANCE: AppearanceSettings = {
  theme: "dark", accentColor: "#6366f1", fontSize: 12, compactMode: false,
  roundedCorners: true, panelTransparency: false, animations: true, density: "normal",
}

const DEFAULT_CHART: ChartSettings = {
  defaultSymbol: "NIFTY 50", defaultInterval: "15m", crosshair: true, grid: true,
  watermark: false, priceScale: "normal", volume: true, autoScale: true,
  rightScale: true, leftScale: false, timezone: "Asia/Kolkata", sessionBreak: false,
}

const DEFAULT_INDICATORS: IndicatorSettings = {
  ema: true, sma: false, rsi: true, macd: true, atr: true, adx: true,
  vwap: true, supertrend: true, lineWidth: 1, opacity: 100, defaultVisible: true,
}

const DEFAULT_OVERLAYS: OverlaySettings = {
  supportResistance: true, supplyDemand: true, swingHighLow: true, trendlines: true,
  liquidity: true, bos: true, choch: true, aiLabels: true, entryZone: true,
  targetLines: true, stoploss: true, opacity: 80, labelSize: "sm",
}

const DEFAULT_TRADE_PLANNER: TradePlannerSettings = {
  defaultCapital: 100000, riskPercent: 2, brokerage: 0.05, slippage: 1,
  taxes: 0.18, lotSize: 1, commission: 0, currency: "INR",
  rrPreference: 1.5, positionSizingMode: "risk-based",
}

const DEFAULT_RISK: RiskSettings = {
  maxDailyLoss: 5000, maxWeeklyLoss: 15000, maxOpenPositions: 5,
  maxExposure: 80, maxDrawdown: 25, stopTrading: false, tradeCooldown: 300,
}

const DEFAULT_REPLAY: ReplaySettings = {
  defaultSpeed: 1, defaultDays: 30, defaultInterval: "15m",
  autoPause: false, showTimeline: true, showJournal: true, theme: "default",
}

const DEFAULT_SCANNER: ScannerSettings = {
  refreshInterval: 30, defaultSort: "score", minScore: 0, minConfidence: 0,
  minRR: 0, watchlist: ["NIFTY 50", "BANK NIFTY"], alertRules: true,
}

const DEFAULT_NOTIFICATIONS: NotificationPrefs = {
  desktop: true, sound: false, popup: true, grouping: true,
  autoDelete: true, historyLimit: 500,
}

const DEFAULT_PORTFOLIO: PortfolioPrefs = {
  paperCapital: 100000, defaultAccount: "Paper", defaultCurrency: "INR",
  autoJournal: true, autoScreenshot: false, pnlMode: "absolute",
}

const DEFAULT_HOTKEYS: HotkeyEntry[] = [
  { id: "toggle-drawer", label: "Toggle Notification Drawer", keys: "Ctrl+N", category: "general" },
  { id: "toggle-sidebar", label: "Toggle Sidebar", keys: "Ctrl+B", category: "workspace" },
  { id: "toggle-right", label: "Toggle Right Panel", keys: "Ctrl+M", category: "workspace" },
  { id: "search", label: "Global Search", keys: "Ctrl+Shift+F", category: "general" },
  { id: "quick-order", label: "Quick Order Entry", keys: "O", category: "trading" },
  { id: "close-position", label: "Close Position", keys: "Ctrl+Shift+C", category: "trading" },
  { id: "play-pause", label: "Replay Play/Pause", keys: "Space", category: "replay" },
  { id: "step-forward", label: "Step Forward", keys: "ArrowRight", category: "replay" },
  { id: "step-back", label: "Step Back", keys: "ArrowLeft", category: "replay" },
  { id: "fullscreen", label: "Toggle Fullscreen", keys: "F11", category: "workspace" },
  { id: "refresh", label: "Refresh Data", keys: "Ctrl+R", category: "general" },
  { id: "save", label: "Save Workspace", keys: "Ctrl+S", category: "workspace" },
]

const DEFAULT_SYSTEM: SystemInfo = {
  frontendVersion: "1.0.0",
  apiUrl: process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000",
  wsUrl: process.env.NEXT_PUBLIC_WS_URL || "ws://localhost:8000/ws",
  environment: process.env.NODE_ENV || "development",
  buildDate: new Date().toISOString(),
  browser: typeof navigator !== "undefined" ? navigator.userAgent : "",
  platform: typeof navigator !== "undefined" ? navigator.platform : "",
}

const sectionDefaults: Record<string, Record<string, unknown>> = {
  general: DEFAULT_GENERAL as unknown as Record<string, unknown>,
  appearance: DEFAULT_APPEARANCE as unknown as Record<string, unknown>,
  chart: DEFAULT_CHART as unknown as Record<string, unknown>,
  indicators: DEFAULT_INDICATORS as unknown as Record<string, unknown>,
  overlays: DEFAULT_OVERLAYS as unknown as Record<string, unknown>,
  tradePlanner: DEFAULT_TRADE_PLANNER as unknown as Record<string, unknown>,
  risk: DEFAULT_RISK as unknown as Record<string, unknown>,
  replay: DEFAULT_REPLAY as unknown as Record<string, unknown>,
  scanner: DEFAULT_SCANNER as unknown as Record<string, unknown>,
  notifications: DEFAULT_NOTIFICATIONS as unknown as Record<string, unknown>,
  portfolio: DEFAULT_PORTFOLIO as unknown as Record<string, unknown>,
}

export const useSettingsStore = create<SettingsState>()(
  persist(
    (set) => ({
      general: { ...DEFAULT_GENERAL },
      appearance: { ...DEFAULT_APPEARANCE },
      chart: { ...DEFAULT_CHART },
      indicators: { ...DEFAULT_INDICATORS },
      overlays: { ...DEFAULT_OVERLAYS },
      tradePlanner: { ...DEFAULT_TRADE_PLANNER },
      risk: { ...DEFAULT_RISK },
      replay: { ...DEFAULT_REPLAY },
      scanner: { ...DEFAULT_SCANNER },
      notifications: { ...DEFAULT_NOTIFICATIONS },
      portfolio: { ...DEFAULT_PORTFOLIO },
      hotkeys: [...DEFAULT_HOTKEYS],
      workspaces: [{ id: "default", name: "Default", sidebarOpen: true, rightPanelOpen: true, bottomPanelOpen: true, activeTab: "dashboard" }],
      system: { ...DEFAULT_SYSTEM },
      activeSection: "general",
      dirty: false,
      searchQuery: "",

      setActiveSection: (activeSection) => set({ activeSection, dirty: false }),
      setSearchQuery: (searchQuery) => set({ searchQuery }),
      setDirty: (dirty) => set({ dirty }),

      updateGeneral: (partial) => set((s) => ({ general: { ...s.general, ...partial }, dirty: true })),
      updateAppearance: (partial) => set((s) => ({ appearance: { ...s.appearance, ...partial }, dirty: true })),
      updateChart: (partial) => set((s) => ({ chart: { ...s.chart, ...partial }, dirty: true })),
      updateIndicators: (partial) => set((s) => ({ indicators: { ...s.indicators, ...partial }, dirty: true })),
      updateOverlays: (partial) => set((s) => ({ overlays: { ...s.overlays, ...partial }, dirty: true })),
      updateTradePlanner: (partial) => set((s) => ({ tradePlanner: { ...s.tradePlanner, ...partial }, dirty: true })),
      updateRisk: (partial) => set((s) => ({ risk: { ...s.risk, ...partial }, dirty: true })),
      updateReplay: (partial) => set((s) => ({ replay: { ...s.replay, ...partial }, dirty: true })),
      updateScanner: (partial) => set((s) => ({ scanner: { ...s.scanner, ...partial }, dirty: true })),
      updateNotificationPrefs: (partial) => set((s) => ({ notifications: { ...s.notifications, ...partial }, dirty: true })),
      updatePortfolioPrefs: (partial) => set((s) => ({ portfolio: { ...s.portfolio, ...partial }, dirty: true })),

      updateHotkey: (id, keys) => set((s) => ({
        hotkeys: s.hotkeys.map((h) => (h.id === id ? { ...h, keys } : h)),
        dirty: true,
      })),

      resetHotkeys: () => set({ hotkeys: [...DEFAULT_HOTKEYS], dirty: true }),

      addWorkspace: (ws) => set((s) => ({ workspaces: [...s.workspaces, ws], dirty: true })),
      removeWorkspace: (id) => set((s) => ({ workspaces: s.workspaces.filter((w) => w.id !== id), dirty: true })),
      renameWorkspace: (id, name) => set((s) => ({
        workspaces: s.workspaces.map((w) => (w.id === id ? { ...w, name } : w)),
        dirty: true,
      })),

      resetSection: (section) => {
        const defaults = sectionDefaults[section]
        if (defaults) {
          set({ [section]: { ...defaults }, dirty: true } as unknown as Partial<SettingsState>)
        }
      },

      resetAll: () => set({
        general: { ...DEFAULT_GENERAL },
        appearance: { ...DEFAULT_APPEARANCE },
        chart: { ...DEFAULT_CHART },
        indicators: { ...DEFAULT_INDICATORS },
        overlays: { ...DEFAULT_OVERLAYS },
        tradePlanner: { ...DEFAULT_TRADE_PLANNER },
        risk: { ...DEFAULT_RISK },
        replay: { ...DEFAULT_REPLAY },
        scanner: { ...DEFAULT_SCANNER },
        notifications: { ...DEFAULT_NOTIFICATIONS },
        portfolio: { ...DEFAULT_PORTFOLIO },
        hotkeys: [...DEFAULT_HOTKEYS],
        dirty: true,
      }),
    }),
    { name: "marketmind-settings", version: 1 }
  )
)
