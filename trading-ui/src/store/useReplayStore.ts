import { create } from "zustand"
import type { ReplaySession } from "@/services/replayService"
import type { Candle } from "@/types"

export type ReplayView = "studio" | "minimal"
export type CalendarMode = "date" | "week" | "month" | "session"

interface ReplayState {
  /* ── Session ── */
  active: boolean
  session: ReplaySession | null
  state: string

  /* ── Playback ── */
  isPlaying: boolean
  isPaused: boolean
  speed: number
  currentIndex: number
  totalCandles: number

  /* ── Data ── */
  replayCandles: Candle[]
  processedDecisions: number
  processedTrades: number

  /* ── UI ── */
  view: ReplayView
  calendarMode: CalendarMode
  selectedDate: string | null
  showJournal: boolean
  showStatistics: boolean
  showMiniMap: boolean
  showCalendar: boolean

  /* ── Analytics ── */
  startTime: number | null
  journal: ReplayJournalEntry[]

  /* ── Actions ── */
  setSession: (session: ReplaySession | null) => void
  setActive: (active: boolean) => void
  setState: (state: string) => void
  setIsPlaying: (playing: boolean) => void
  setIsPaused: (paused: boolean) => void
  setSpeed: (speed: number) => void
  setCurrentIndex: (index: number) => void
  setTotalCandles: (total: number) => void
  addCandle: (candle: Candle) => void
  setReplayCandles: (candles: Candle[]) => void
  setProcessedDecisions: (n: number) => void
  setProcessedTrades: (n: number) => void
  setStartTime: (t: number | null) => void
  addJournalEntry: (entry: ReplayJournalEntry) => void
  setJournal: (entries: ReplayJournalEntry[]) => void
  toggleJournal: () => void
  toggleStatistics: () => void
  toggleMiniMap: () => void
  toggleCalendar: () => void
  setView: (view: ReplayView) => void
  setCalendarMode: (mode: CalendarMode) => void
  setSelectedDate: (date: string | null) => void
  reset: () => void
}

export interface ReplayJournalEntry {
  timestamp: string
  index: number
  decision: string
  score: number
  confidence: number
  risk_level: string
  direction: string
  reasoning: string[]
}

const initialState = {
  active: false,
  session: null as ReplaySession | null,
  state: "idle",
  isPlaying: false,
  isPaused: false,
  speed: 1,
  currentIndex: 0,
  totalCandles: 0,
  replayCandles: [] as Candle[],
  processedDecisions: 0,
  processedTrades: 0,
  view: "studio" as ReplayView,
  calendarMode: "date" as CalendarMode,
  selectedDate: null as string | null,
  showJournal: true,
  showStatistics: true,
  showMiniMap: true,
  showCalendar: true,
  startTime: null as number | null,
  journal: [] as ReplayJournalEntry[],
}

export const useReplayStore = create<ReplayState>((set) => ({
  ...initialState,

  setSession: (session) => set({ session }),
  setActive: (active) => set({ active }),
  setState: (state) => set({ state }),
  setIsPlaying: (isPlaying) => set({ isPlaying }),
  setIsPaused: (isPaused) => set({ isPaused }),
  setSpeed: (speed) => set({ speed }),
  setCurrentIndex: (currentIndex) => set({ currentIndex }),
  setTotalCandles: (totalCandles) => set({ totalCandles }),
  addCandle: (candle) =>
    set((s) => ({ replayCandles: [...s.replayCandles, candle] })),
  setReplayCandles: (replayCandles) => set({ replayCandles }),
  setProcessedDecisions: (processedDecisions) => set({ processedDecisions }),
  setProcessedTrades: (processedTrades) => set({ processedTrades }),
  setStartTime: (startTime) => set({ startTime }),
  addJournalEntry: (entry) =>
    set((s) => ({ journal: [...s.journal, entry] })),
  setJournal: (journal) => set({ journal }),
  toggleJournal: () => set((s) => ({ showJournal: !s.showJournal })),
  toggleStatistics: () => set((s) => ({ showStatistics: !s.showStatistics })),
  toggleMiniMap: () => set((s) => ({ showMiniMap: !s.showMiniMap })),
  toggleCalendar: () => set((s) => ({ showCalendar: !s.showCalendar })),
  setView: (view) => set({ view }),
  setCalendarMode: (calendarMode) => set({ calendarMode }),
  setSelectedDate: (selectedDate) => set({ selectedDate }),
  reset: () => set({ ...initialState }),
}))
