import { create } from 'zustand'
import { subDays } from 'date-fns'

const INDICES = [
  { label: 'NIFTY 50', value: 'NIFTY 50' },
  { label: 'BANKNIFTY', value: 'BANKNIFTY' },
  { label: 'SENSEX', value: 'SENSEX' },
]

const PRESETS = [
  { label: '4D', days: 4 },
  { label: '1W', days: 7 },
  { label: '2W', days: 14 },
  { label: '1M', days: 30 },
  { label: '45D', days: 45 },
  { label: '2M', days: 60 },
]

const useMarketStore = create((set, get) => ({
  selectedIndex: 'NIFTY 50',
  indices: INDICES,
  datePresets: PRESETS,
  activePreset: '2M',
  customStartDate: null,
  customEndDate: null,

  fullData: [],
  data: [],

  loading: false,
  error: null,

  showCandlestick: false,

  // Refresh trigger — bump this to signal useMarketData to re-fetch
  refreshTrigger: 0,
  triggerRefresh: () => set((s) => ({ refreshTrigger: s.refreshTrigger + 1 })),

  setSelectedIndex: (index) => set({ selectedIndex: index }),

  setActivePreset: (preset) =>
    set({ activePreset: preset, customStartDate: null, customEndDate: null }),

  setCustomDateRange: (start, end) =>
    set({ customStartDate: start, customEndDate: end, activePreset: null }),

  _getWindowStart: () => {
    const { activePreset, customStartDate, customEndDate } = get()
    const endDate = new Date()
    if (customStartDate && customEndDate) return new Date(customStartDate)
    if (activePreset) {
      const preset = PRESETS.find(p => p.label === activePreset)
      return subDays(endDate, preset ? preset.days : 60)
    }
    return subDays(endDate, 60)
  },

  sliceData: () => {
    const { fullData } = get()
    if (!fullData || fullData.length === 0) { set({ data: [] }); return }
    const startStr = get()._getWindowStart().toISOString().split('T')[0]
    const idx = fullData.findIndex(d => d.Date >= startStr)
    set({ data: idx >= 0 ? fullData.slice(idx) : [] })
  },

  setFullDataAndSlice: (fullData) => {
    const startStr = get()._getWindowStart().toISOString().split('T')[0]
    const idx = fullData.findIndex(d => d.Date >= startStr)
    set({ fullData, data: idx >= 0 ? fullData.slice(idx) : [] })
  },

  setLoading: (loading) => set({ loading }),
  setError: (error) => set({ error }),

  toggleIndicator: (indicator) =>
    set((state) => ({ ...state, [indicator]: !state[indicator] })),
}))

export default useMarketStore
