import React, { useMemo } from 'react'
import {
  ComposedChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Area,
} from 'recharts'
import { format, parseISO } from 'date-fns'
import { TrendingUp, TrendingDown, Target, ShieldAlert } from 'lucide-react'
import { generateForecastData } from '../utils/technicalIndicators'

export default function PredictionChart({ data, prediction, windowLabel }) {
  const forecastData = useMemo(() => {
    if (!data || !prediction) return []
    return generateForecastData(data, prediction)
  }, [data, prediction])

  if (!prediction || forecastData.length === 0) return null

  const isBullish = prediction.direction === 'BULLISH'
  const forecastColor = isBullish ? '#10b981' : '#ef4444'

  const CustomTooltip = ({ active, payload, label }) => {
    if (!active || !payload || !payload.length) return null
    return (
      <div className="glass-card-strong p-3 shadow-lg border border-gray-200/50 dark:border-gray-700/50">
        <p className="text-xs text-gray-500 dark:text-gray-400 mb-1">{label}</p>
        {payload.map((entry, idx) => (
          <p key={idx} className="text-sm font-medium" style={{ color: entry.color }}>
            {entry.name}: {typeof entry.value === 'number' ? entry.value.toFixed(2) : entry.value}
          </p>
        ))}
      </div>
    )
  }

  const fmt = (val) => val?.toLocaleString('en-IN', { minimumFractionDigits: 2 }) ?? '--'

  return (
    <div className="chart-container">
      <div className="flex items-center justify-between mb-4">
        <div>
          <h3 className="text-sm font-semibold text-gray-700 dark:text-gray-200">Next-Day Forecast</h3>
          <p className="text-xs text-gray-400 dark:text-gray-500">Last 3 days + AI projected movement</p>
        </div>
        <div className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium ${
          isBullish ? 'bg-emerald-50 dark:bg-emerald-900/30 text-emerald-600 dark:text-emerald-400' : 'bg-red-50 dark:bg-red-900/30 text-red-600 dark:text-red-400'
        }`}>
          {isBullish ? <TrendingUp className="w-3 h-3" /> : <TrendingDown className="w-3 h-3" />}
          Forecast: {prediction.direction}
        </div>
      </div>

      <div className="h-[180px] sm:h-[200px] w-full">
        <ResponsiveContainer width="100%" height="100%">
          <ComposedChart data={forecastData}>
            <defs>
              <linearGradient id="colorClose" x1="0" y1="0" x2="0" y2="1">
                <stop offset="5%" stopColor="#3b82f6" stopOpacity={0.15} />
                <stop offset="95%" stopColor="#3b82f6" stopOpacity={0} />
              </linearGradient>
              <linearGradient id="forecastGrad" x1="0" y1="0" x2="0" y2="1">
                <stop offset="5%" stopColor={forecastColor} stopOpacity={0.1} />
                <stop offset="95%" stopColor={forecastColor} stopOpacity={0} />
              </linearGradient>
            </defs>
            <CartesianGrid strokeDasharray="3 3" stroke="#f1f5f9" className="dark:stroke-gray-800" />
            <XAxis
              dataKey="date"
              tick={{ fontSize: 10, fill: '#94a3b8' }}
              tickLine={false} axisLine={false}
              tickFormatter={(val) => { if (!val) return ''; try { return format(parseISO(val), 'dd MMM') } catch { return val } }}
            />
            <YAxis
              domain={['auto', 'auto']}
              tick={{ fontSize: 10, fill: '#94a3b8' }}
              tickLine={false} axisLine={false}
              tickFormatter={(val) => val.toLocaleString('en-IN')}
            />
            <Tooltip content={<CustomTooltip />} />
            <Area type="monotone" dataKey="close" stroke="#3b82f6" strokeWidth={2} fill="url(#colorClose)" dot={false} name="Close" />
            <Line type="monotone" dataKey="close" stroke={forecastColor} strokeWidth={2.5} strokeDasharray="6 3" dot={{ fill: forecastColor, r: 4 }} name="Forecast" connectNulls={false} />
            <Area type="monotone" dataKey="high" stroke="none" fill={forecastColor} fillOpacity={0.08} name="High" />
            <Area type="monotone" dataKey="low" stroke="none" fill={forecastColor} fillOpacity={0.08} name="Low" />
          </ComposedChart>
        </ResponsiveContainer>
      </div>

      {/* Trade Scenarios — only show when direction is clear */}
      {prediction.direction !== 'SIDEWAYS' ? (
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 mt-4">
          {/* Bullish Scenario */}
          <div className={`rounded-lg p-3 border ${
            isBullish
              ? 'bg-emerald-50/70 dark:bg-emerald-900/20 border-emerald-200/70 dark:border-emerald-800/30 ring-1 ring-emerald-400/30'
              : 'bg-gray-50/50 dark:bg-gray-700/20 border-gray-200/50 dark:border-gray-700/30'
          }`}>
            <div className="flex items-center gap-1.5 mb-2">
              <TrendingUp className={`w-3.5 h-3.5 ${isBullish ? 'text-emerald-600 dark:text-emerald-400' : 'text-gray-400'}`} />
              <span className={`text-xs font-semibold ${isBullish ? 'text-emerald-700 dark:text-emerald-300' : 'text-gray-400'}`}>
                {isBullish ? '✓ Primary Scenario (Bullish)' : 'Alternate Scenario (Bullish)'}
              </span>
            </div>
            {prediction.buyScenario ? (
              <div className="space-y-1 text-xs">
                <div className="flex justify-between">
                  <span className="text-gray-400">Entry</span>
                  <span className="font-mono font-medium text-emerald-600 dark:text-emerald-400">{fmt(prediction.buyScenario.entry)}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-gray-400">SL</span>
                  <span className="font-mono font-medium text-red-500">{fmt(prediction.buyScenario.stopLoss)}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-gray-400">Target 1</span>
                  <span className="font-mono font-medium text-emerald-600 dark:text-emerald-400">{fmt(prediction.buyScenario.target1)}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-gray-400">Target 2</span>
                  <span className="font-mono font-medium text-emerald-600 dark:text-emerald-400">{fmt(prediction.buyScenario.target2)}</span>
                </div>
                <p className="text-[10px] text-gray-400 dark:text-gray-500 mt-1 italic">{prediction.buyScenario.trigger}</p>
              </div>
            ) : (
              <p className="text-xs text-gray-400 italic">Insufficient data</p>
            )}
          </div>

          {/* Bearish Scenario */}
          <div className={`rounded-lg p-3 border ${
            !isBullish
              ? 'bg-red-50/70 dark:bg-red-900/20 border-red-200/70 dark:border-red-800/30 ring-1 ring-red-400/30'
              : 'bg-gray-50/50 dark:bg-gray-700/20 border-gray-200/50 dark:border-gray-700/30'
          }`}>
            <div className="flex items-center gap-1.5 mb-2">
              <TrendingDown className={`w-3.5 h-3.5 ${!isBullish ? 'text-red-600 dark:text-red-400' : 'text-gray-400'}`} />
              <span className={`text-xs font-semibold ${!isBullish ? 'text-red-700 dark:text-red-300' : 'text-gray-400'}`}>
                {!isBullish ? '✓ Primary Scenario (Bearish)' : 'Alternate Scenario (Bearish)'}
              </span>
            </div>
            {prediction.sellScenario ? (
              <div className="space-y-1 text-xs">
                <div className="flex justify-between">
                  <span className="text-gray-400">Entry</span>
                  <span className="font-mono font-medium text-red-600 dark:text-red-400">{fmt(prediction.sellScenario.entry)}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-gray-400">SL</span>
                  <span className="font-mono font-medium text-red-500">{fmt(prediction.sellScenario.stopLoss)}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-gray-400">Target 1</span>
                  <span className="font-mono font-medium text-red-600 dark:text-red-400">{fmt(prediction.sellScenario.target1)}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-gray-400">Target 2</span>
                  <span className="font-mono font-medium text-red-600 dark:text-red-400">{fmt(prediction.sellScenario.target2)}</span>
                </div>
                <p className="text-[10px] text-gray-400 dark:text-gray-500 mt-1 italic">{prediction.sellScenario.trigger}</p>
              </div>
            ) : (
              <p className="text-xs text-gray-400 italic">Insufficient data</p>
            )}
          </div>
        </div>
      ) : (
        <div className="mt-4 p-3 bg-gray-50/50 dark:bg-gray-700/20 rounded-lg border border-gray-200/50 dark:border-gray-700/30 text-center">
          <p className="text-xs text-gray-400 dark:text-gray-500">Market is sideways — no clear directional scenario available.</p>
        </div>
      )}
    </div>
  )
}
