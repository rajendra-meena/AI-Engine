import React, { useState, useMemo } from 'react'
import { useMarketData } from '../hooks/useMarketData'
import useMarketStore from '../store/useMarketStore'
import { generateAIPrediction } from '../utils/technicalIndicators'
import StatsCard from './StatsCard'
import MainChart from './MainChart'
import SupportResistance from './SupportResistance'
import AIPredictionCard from './AIPredictionCard'
import PredictionChart from './PredictionChart'
import { AlertCircle, RefreshCw, Download } from 'lucide-react'
import { StatsCardSkeleton, ChartSkeleton, PredictionCardSkeleton, SupportResistanceSkeleton } from './Skeleton'
import { exportToCSV, getOHLCExportColumns } from '../utils/exportData'

function formatRelativeTime(dateStr) {
  if (!dateStr) return null
  const diff = Date.now() - new Date(dateStr).getTime()
  const mins = Math.floor(diff / 60000)
  if (mins < 1) return 'just now'
  if (mins < 60) return `${mins}m ago`
  const hours = Math.floor(mins / 60)
  if (hours < 24) return `${hours}h ago`
  return dateStr
}

export default function Dashboard() {
  const { data, loading, error, refetch, cacheInfo } = useMarketData()
  const activePreset = useMarketStore(s => s.activePreset)
  const setActivePreset = useMarketStore(s => s.setActivePreset)
  const setCustomDateRange = useMarketStore(s => s.setCustomDateRange)
  const customStartDate = useMarketStore(s => s.customStartDate)
  const customEndDate = useMarketStore(s => s.customEndDate)

  const [showDatePicker, setShowDatePicker] = useState(false)

  const handleExportCSV = () => {
    if (!data || data.length === 0) return
    const exportData = data.map(d => ({
      Date: d.Date,
      Open: d.Open,
      High: d.High,
      Low: d.Low,
      Close: d.Close,
      Volume: d.Volume || 0,
    }))
    exportToCSV(exportData, getOHLCExportColumns(), `marketmind-${useMarketStore.getState().selectedIndex}-${activePreset || 'custom'}`)
  }

  const latest = data && data.length > 0 ? data[data.length - 1] : null
  const prev = data && data.length > 1 ? data[data.length - 2] : null
  const changePercent = latest && prev ? ((latest.Close - prev.Close) / prev.Close) * 100 : null

  // Compute AI prediction here to pass predicted levels to the chart
  const prediction = useMemo(() => {
    if (!data || data.length < 3) return null
    return generateAIPrediction(data, activePreset)
  }, [data, activePreset])

  if (loading && (!data || data.length === 0)) {
    return (
      <div className="space-y-4 sm:space-y-6 animate-fadeIn">
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
          <StatsCardSkeleton />
          <StatsCardSkeleton />
          <StatsCardSkeleton />
          <StatsCardSkeleton />
        </div>
        <div className="grid grid-cols-1 lg:grid-cols-4 gap-4 sm:gap-6">
          <div className="lg:col-span-3 space-y-4 sm:space-y-6">
            <ChartSkeleton />
            <ChartSkeleton />
          </div>
          <div className="space-y-4 sm:space-y-6">
            <SupportResistanceSkeleton />
            <PredictionCardSkeleton />
          </div>
        </div>
      </div>
    )
  }

  if (error) {
    return (
      <div className="flex items-center justify-center min-h-[60vh]">
        <div className="text-center">
          <div className="w-16 h-16 bg-red-50 dark:bg-red-900/30 rounded-full flex items-center justify-center mx-auto mb-4">
            <AlertCircle className="w-8 h-8 text-red-500" />
          </div>
          <p className="text-sm font-medium text-gray-700 dark:text-gray-200 mb-1">Failed to load data</p>
          <p className="text-xs text-gray-400 dark:text-gray-500 mb-4">{error}</p>
          <button onClick={refetch} className="inline-flex items-center gap-1.5 px-4 py-2 bg-primary text-primary-foreground text-sm rounded-lg hover:bg-primary/90 transition-colors">
            <RefreshCw className="w-4 h-4" /> Retry
          </button>
        </div>
      </div>
    )
  }

  return (
    <div className="space-y-4 sm:space-y-6">
      {/* Info bar: cache status + custom date picker toggle */}
      <div className="flex flex-wrap items-center justify-between gap-2 text-[10px] text-gray-400 dark:text-gray-500">
        <div className="flex items-center gap-3">
          {cacheInfo && <span>📅 Data: {cacheInfo.last_updated || 'N/A'} <span className="hidden sm:inline">({cacheInfo.total_days ?? '?'} days)</span></span>}
          {cacheInfo?.last_updated && <span className="text-[9px] text-gray-300 dark:text-gray-600">· {formatRelativeTime(cacheInfo.last_updated)}</span>}
          <span>View: {data?.length || 0} days ({activePreset || 'Custom'})</span>
        </div>
        <div className="flex items-center gap-3">
          <button
            onClick={handleExportCSV}
            disabled={!data || data.length === 0}
            className="inline-flex items-center gap-1 text-[10px] text-gray-400 hover:text-gray-600 dark:hover:text-gray-300 transition-colors disabled:opacity-30"
          >
            <Download className="w-3 h-3" /> CSV
          </button>
          <button
            onClick={() => setShowDatePicker(!showDatePicker)}
            className="text-[10px] text-primary hover:text-primary/80 transition-colors"
          >
            {showDatePicker ? 'Close' : 'Custom Range'}
          </button>
        </div>
      </div>

      {/* Custom date picker */}
      {showDatePicker && (
        <div className="flex flex-wrap items-center gap-3 p-3 bg-white/50 dark:bg-gray-800/30 rounded-lg border border-gray-100 dark:border-gray-700/50">
          <div className="flex items-center gap-2">
            <span className="text-[10px] text-gray-400">From</span>
            <input
              type="date"
              value={customStartDate || ''}
              onChange={(e) => setCustomDateRange(e.target.value, customEndDate)}
              className="px-2 py-1 bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded text-xs text-gray-700 dark:text-gray-200"
            />
          </div>
          <div className="flex items-center gap-2">
            <span className="text-[10px] text-gray-400">To</span>
            <input
              type="date"
              value={customEndDate || ''}
              onChange={(e) => setCustomDateRange(customStartDate, e.target.value)}
              className="px-2 py-1 bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded text-xs text-gray-700 dark:text-gray-200"
            />
          </div>
          {(customStartDate || customEndDate) && (
            <button
              onClick={() => { setCustomDateRange(null, null); setActivePreset('2M') }}
              className="text-[10px] text-red-500 hover:text-red-400 transition-colors"
            >
              Clear
            </button>
          )}
        </div>
      )}

      {/* Stats Cards */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        <StatsCard label="Open" value={latest?.Open} change={null} />
        <StatsCard label="High" value={latest?.High} change={null} />
        <StatsCard label="Low" value={latest?.Low} change={null} />
        <StatsCard label="Close" value={latest?.Close} change={changePercent} />
      </div>

      {/* Main Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-4 gap-4 sm:gap-6">
        <div className="lg:col-span-3 space-y-4 sm:space-y-6">
          <MainChart prediction={prediction} />
          <PredictionChart data={data} prediction={prediction} windowLabel={activePreset} />
        </div>
        <div className="space-y-4 sm:space-y-6">
          <SupportResistance data={data} />
          <AIPredictionCard data={data} windowLabel={activePreset} prediction={prediction} />
        </div>
      </div>
    </div>
  )
}
