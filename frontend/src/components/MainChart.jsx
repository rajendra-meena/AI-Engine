import React, { useMemo } from 'react'
import {
  Area,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Brush,
  ComposedChart,
  Bar,
  Cell,
  ReferenceLine,
  Label,
} from 'recharts'
import { format, parseISO } from 'date-fns'
import useMarketStore from '../store/useMarketStore'
import { calculatePivotPoints } from '../utils/technicalIndicators'
import { CandlestickShape } from './CandlestickChart'

export default function MainChart({ prediction }) {
  const { data, showCandlestick, toggleIndicator } = useMarketStore()

  const chartData = useMemo(() => {
    if (!data || data.length === 0) return []
    return data.map((d, i) => ({
      date: d.Date,
      close: d.Close,
      open: d.Open,
      high: d.High,
      low: d.Low,
      volume: d.Volume || 0,
      volumeColor: i > 0 ? (d.Close >= data[i - 1].Close ? '#22c55e' : '#ef4444') : '#94a3b8',
    }))
  }, [data])

  const pivots = useMemo(() => calculatePivotPoints(data), [data])

  const sRLines = useMemo(() => {
    if (!pivots) return []
    return [
      { y: pivots.r3, label: 'R3', color: '#ef4444' },
      { y: pivots.r2, label: 'R2', color: '#ef4444' },
      { y: pivots.r1, label: 'R1', color: '#ef4444' },
      { y: pivots.pivot, label: 'P', color: '#6366f1' },
      { y: pivots.s1, label: 'S1', color: '#22c55e' },
      { y: pivots.s2, label: 'S2', color: '#22c55e' },
      { y: pivots.s3, label: 'S3', color: '#22c55e' },
    ]
  }, [pivots])

  // Predicted price markers from AI
  const predLines = useMemo(() => {
    if (!prediction) return []
    const lines = []
    if (prediction.predictedHigh != null) lines.push({ y: prediction.predictedHigh, label: 'PH', color: '#6366f1' })
    if (prediction.predictedClose != null) lines.push({ y: prediction.predictedClose, label: 'PC', color: '#6366f1' })
    if (prediction.predictedLow != null) lines.push({ y: prediction.predictedLow, label: 'PL', color: '#6366f1' })
    return lines
  }, [prediction])

  // Compute Y-axis domain that includes price data, pivot lines, and prediction markers
  const chartDomain = useMemo(() => {
    if (chartData.length === 0) return ['auto', 'auto']
    let minVal = Infinity, maxVal = -Infinity
    for (const d of chartData) {
      if (d.low < minVal) minVal = d.low
      if (d.high > maxVal) maxVal = d.high
    }
    const allLines = [...sRLines, ...predLines]
    for (const line of allLines) {
      if (line.y < minVal) minVal = line.y
      if (line.y > maxVal) maxVal = line.y
    }
    const padding = Math.max((maxVal - minVal) * 0.02, maxVal * 0.001 || 1)
    return [Math.floor(minVal - padding), Math.ceil(maxVal + padding)]
  }, [chartData, sRLines, predLines])

  const CandleTooltip = ({ active, payload, label }) => {
    if (!active || !payload || !payload.length) return null
    const d = payload[0]?.payload
    if (!d) return null
    const isUp = d.close >= d.open
    const val = (v) => v?.toFixed(2) ?? '--'
    return (
      <div className="glass-card-strong p-3 shadow-lg border border-gray-200/50 dark:border-gray-700/50 min-w-[130px]">
        <p className="text-xs text-gray-500 dark:text-gray-400 mb-1.5 font-medium">{label}</p>
        <div className="space-y-0.5 text-xs">
          <div className="flex justify-between gap-4"><span className="text-gray-400">O</span><span className="font-medium text-gray-700 dark:text-gray-200">{val(d.open)}</span></div>
          <div className="flex justify-between gap-4"><span className="text-gray-400">H</span><span className="font-medium text-gray-700 dark:text-gray-200">{val(d.high)}</span></div>
          <div className="flex justify-between gap-4"><span className="text-gray-400">L</span><span className="font-medium text-gray-700 dark:text-gray-200">{val(d.low)}</span></div>
          <div className="flex justify-between gap-4"><span className="text-gray-400">C</span><span className={`font-bold ${isUp ? 'text-emerald-500' : 'text-red-500'}`}>{val(d.close)}</span></div>
        </div>
      </div>
    )
  }

  const AreaTooltip = ({ active, payload, label }) => {
    if (!active || !payload || !payload.length) return null
    const d = payload[0]?.payload
    if (!d) return null
    const val = (v) => v?.toFixed(2) ?? '--'
    return (
      <div className="glass-card-strong p-3 shadow-lg border border-gray-200/50 dark:border-gray-700/50 min-w-[130px]">
        <p className="text-xs text-gray-500 dark:text-gray-400 mb-1.5 font-medium">{label}</p>
        <div className="text-sm font-medium text-blue-600">Close: {val(d.close)}</div>
      </div>
    )
  }

  return (
    <div className="chart-container">
      <div className="flex flex-wrap items-center justify-between gap-3 mb-4">
        <h3 className="text-sm font-semibold text-gray-700 dark:text-gray-200">Price Chart</h3>
        <label className="flex items-center gap-1.5 text-xs text-gray-500 dark:text-gray-400 cursor-pointer select-none">
          <input
            type="checkbox"
            checked={showCandlestick}
            onChange={() => toggleIndicator('showCandlestick')}
            className="w-3.5 h-3.5 rounded border-gray-300 dark:border-gray-600 text-blue-600 focus:ring-blue-500"
          />
          Candlestick
        </label>
      </div>

      <div className="h-[250px] sm:h-[350px] w-full">
        <ResponsiveContainer width="100%" height="100%">
          <ComposedChart data={chartData}>
            <defs>
              <linearGradient id="colorClose" x1="0" y1="0" x2="0" y2="1">
                <stop offset="5%" stopColor="#3b82f6" stopOpacity={0.15} />
                <stop offset="95%" stopColor="#3b82f6" stopOpacity={0} />
              </linearGradient>
            </defs>
            <CartesianGrid strokeDasharray="3 3" stroke="#f1f5f9" className="dark:stroke-gray-800" />
            <XAxis dataKey="date" tick={{ fontSize: 11, fill: '#94a3b8' }} tickLine={false} axisLine={false}
              tickFormatter={(val) => { try { return format(parseISO(val), 'dd MMM') } catch { return val } }} minTickGap={40} />
            <YAxis yAxisId="price" domain={chartDomain} tick={{ fontSize: 11, fill: '#94a3b8' }} tickLine={false} axisLine={false}
              tickFormatter={(val) => val.toLocaleString('en-IN')} />
            <Tooltip content={showCandlestick ? <CandleTooltip /> : <AreaTooltip />} />

            {sRLines.map(line => (
              <ReferenceLine key={line.label} y={line.y} yAxisId="price" stroke={line.color} strokeDasharray="6 4" strokeWidth={1} strokeOpacity={0.7}>
                <Label value={`${line.label}: ${line.y.toLocaleString('en-IN', { minimumFractionDigits: 0 })}`}
                  position="insideTopRight" fontSize={10} fill={line.color} fillOpacity={0.8} />
              </ReferenceLine>
            ))}

            {/* Predicted price markers */}
            {predLines.map(line => (
              <ReferenceLine key={line.label} y={line.y} yAxisId="price" stroke={line.color} strokeDasharray="4 4" strokeWidth={1.5} strokeOpacity={0.5}>
                <Label value={`${line.label}: ${line.y.toLocaleString('en-IN', { minimumFractionDigits: 0 })}`}
                  position="insideTopLeft" fontSize={9} fill={line.color} fillOpacity={0.6} />
              </ReferenceLine>
            ))}

            {showCandlestick ? (
              <Bar yAxisId="price" dataKey="close" shape={<CandlestickShape domain={chartDomain} />} isAnimationActive={false} />
            ) : (
              <Area yAxisId="price" type="monotone" dataKey="close" stroke="#3b82f6" strokeWidth={2} fill="url(#colorClose)" dot={false} name="Close" />
            )}

            <Brush dataKey="date" height={24} stroke="#94a3b8" fill="#f8fafc" className="dark:fill-gray-700"
              tickFormatter={(val) => { try { return format(parseISO(val), 'MMM dd') } catch { return val } }} />
          </ComposedChart>
        </ResponsiveContainer>
      </div>

      <div className="h-[60px] w-full mt-1">
        <ResponsiveContainer width="100%" height="100%">
          <ComposedChart data={chartData}>
            <XAxis dataKey="date" hide />
            <YAxis hide domain={['auto', 'auto']} />
            <Bar dataKey="volume" opacity={0.5} minPointSize={1}>
              {chartData.map((entry, idx) => <Cell key={idx} fill={entry.volumeColor} />)}
            </Bar>
          </ComposedChart>
        </ResponsiveContainer>
      </div>
    </div>
  )
}
