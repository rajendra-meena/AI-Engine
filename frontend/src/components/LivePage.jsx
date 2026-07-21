/**
 * Live Intraday — Expert Mode
 *
 * TODO (Phase 2+): Split into smaller components:
 *   - LiveDataProvider (data fetching + WebSocket) — moves to hook
 *   - MarketContextCard (VWAP, ORB, trend, RSI, swing levels)
 *   - ActiveSetupCard (entry, SL, targets, RR, reasons)
 *   - AlertPanel (alert history table)
 *   - ChartSection (candlesticks + indicators)
 *
 * Current: ~660 lines — data, analysis, and UI are mixed.
 * Target: WebSocket-driven, display-only UI.
 */

import React, { useState, useEffect, useCallback, useRef, useMemo } from 'react'
import axios from 'axios'
import { Brain, TrendingUp, TrendingDown, Activity, RefreshCw, Clock, Bell, BellOff, Target, ShieldAlert, AlertTriangle } from 'lucide-react'
import { ComposedChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, ReferenceLine, ReferenceArea, Label } from 'recharts'
import useMarketStore from '../store/useMarketStore'
import { calculateATR, calculatePivotPoints } from '../utils/technicalIndicators'
import { calculateVWAP, generateExpertSetup } from '../utils/expertTradeEngine'
import { savePrediction } from '../utils/api'
import { isMarketOpen, getCurrentTradingDay, getMinutesFromMarketOpen, getMarketPhase, fmt } from '../utils/marketUtils'
import { CandlestickShape } from './CandlestickChart'
import { sendNotification } from '../utils/exportData'

// ── Cookie helpers ──
function getCookie(name) {
  const m = document.cookie.match(new RegExp(`(^| )${name}=([^;]+)`))
  return m ? decodeURIComponent(m[2]) : null
}
function setCookie(name, value, days = 365) {
  const d = new Date(); d.setDate(d.getDate() + days)
  document.cookie = `${name}=${encodeURIComponent(value)};expires=${d.toUTCString()};path=/`
}

const INTERVALS = [
  { label: '1 min', value: '1m', pollMs: 60 * 1000 },
  { label: '3 min', value: '3m', pollMs: 3 * 60 * 1000 },
  { label: '5 min', value: '5m', pollMs: 5 * 60 * 1000 },
  { label: '15 min', value: '15m', pollMs: 15 * 60 * 1000 },
]

export default function LivePage() {
  const { selectedIndex, setSelectedIndex, indices } = useMarketStore()
  const savedInterval = getCookie('liveInterval') || '15m'
  const [interval, setIntervalState] = useState(savedInterval)
  const [candles, setCandles] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [pivots, setPivots] = useState(null)
  const [dailyRefs, setDailyRefs] = useState(null)
  const [lastUpdate, setLastUpdate] = useState(null)
  const [alerts, setAlerts] = useState([])
  const [notificationsEnabled, setNotificationsEnabled] = useState(
    () => localStorage.getItem('marketmind-notifications') === 'true'
  )

  // New expert engine state
  const [vwap, setVwap] = useState(null)
  const [orbRange, setOrbRange] = useState({ orbHigh: null, orbLow: null, orbBrokenUp: false, orbBrokenDn: false })
  const [expertSetups, setExpertSetups] = useState([])
  const [marketContext, setMarketContext] = useState(null)
  const [activeSetup, setActiveSetup] = useState(null)

  const pollRef = useRef(null)
  const prevSignalRef = useRef(null) // dedup key for alerts
  const savedPredictionsRef = useRef(new Set())

  const curInt = INTERVALS.find(i => i.value === interval) || INTERVALS[2]

  const fetchData = useCallback(async () => {
    try {
      const resp = await axios.get('/api/intraday', {
        params: { symbol: selectedIndex, interval, days: 3 },
      })

      if (resp.data?.candles?.length) {
        const sorted = resp.data.candles.sort((a, b) => new Date(a.time) - new Date(b.time))
        setCandles(sorted)
        setError(null)
        setDailyRefs(resp.data.dailyRefs || null)
        setLastUpdate(new Date())

        // Compute VWAP from today's candles
        const todayStr = new Date().toISOString().split('T')[0]
        const todayCandles = sorted.filter(c => c.time && c.time.startsWith(todayStr))
        const vwapVal = calculateVWAP(todayCandles.length > 0 ? todayCandles : sorted)
        setVwap(vwapVal)

        // Compute ATR
        const highs = sorted.map(c => c.high)
        const lows = sorted.map(c => c.low)
        const closes = sorted.map(c => c.close)
        const atrArr = calculateATR(highs, lows, closes, Math.min(14, sorted.length))
        const atrVal = atrArr[atrArr.length - 1] || 0

        // Pivot points
        const aiData = sorted.map(c => ({ Date: c.time, Open: c.open, High: c.high, Low: c.low, Close: c.close, Volume: c.volume }))
        setPivots(calculatePivotPoints(aiData))

        // Run expert engine
        const intervalNum = parseInt(interval.replace('m', '').replace('h', '')) || 5
        const result = generateExpertSetup(sorted, resp.data.dailyRefs || null, atrVal, vwapVal, intervalNum)
        setExpertSetups(result.setups)
        setMarketContext(result.marketContext)
        setActiveSetup(result.setups.length > 0 ? result.setups[0] : null)

        // Detect ORB range
        const orb = result.marketContext?.orbRange
        setOrbRange(orb || { orbHigh: null, orbLow: null, orbBrokenUp: false, orbBrokenDn: false })

        // ── Generate alert if new valid setup appeared ──
        // Only valid setups (from engine's .filter(s => s.valid === true)) enter here — no random alerts.
        const last = sorted[sorted.length - 1]
        if (result.setups.length > 0 && last) {
          const top = result.setups[0]
          // Dedup by type + approximate time window (within 5 min of last same-type alert)
          const signalKey = `${top.type}-${Math.floor(new Date(last.time).getTime() / 300000)}`
          const isNewSignal = prevSignalRef.current !== signalKey
          if (isNewSignal) {
            prevSignalRef.current = signalKey

            const ist = new Date(new Date().getTime() + new Date().getTimezoneOffset() * 60000 + 5.5 * 3600000)
            const top = result.setups[0]

          const newAlert = {
            id: Date.now(),
            time: ist.toLocaleTimeString('en-IN'),
            candleTime: last.time,
            close: last.close,
            direction: top.direction,
            confidence: top.confidence ?? top.score,
            bias: top.direction === 'BULLISH' ? 'Buy Call' : 'Buy Put',
            entry: top.entry,
            sl: top.stopLoss,
            target: top.target1,
            target2: top.target2,
            target3: top.target3,
            setupType: top.type,
            setupLabel: top.label || top.type,
            riskReward: top.riskReward,
            valid: top.valid,
            rejectionReason: top.rejectionReason,
            analysis: top.analysisSummary,
          }

          setAlerts(prev => [newAlert, ...prev.slice(0, 49)])

          if (notificationsEnabled) {
            sendNotification(`MarketMind: ${newAlert.setupLabel}`, {
              body: `${selectedIndex} · ${top.direction} · Entry: ${fmt(top.entry)} · SL: ${fmt(top.stopLoss)} · R:R ${top.riskReward}`,
              tag: signalKey,
            })
          }

          // Save to backend for backtesting (only non-sideways setups)
          if (top.direction !== 'SIDEWAYS') {
            const hash = `${selectedIndex}-${interval}-${new Date().toISOString().split('T')[0]}`
            if (!savedPredictionsRef.current.has(hash)) {
              savedPredictionsRef.current.add(hash)
              savePrediction({
                symbol: selectedIndex,
                interval,
                predicted_date: getCurrentTradingDay(),
                direction: top.direction === 'BULLISH' ? 'BULLISH' : 'BEARISH',
                trend_label: top.label,
                confidence: Math.min(top.score, 100),
                suggested_bias: top.direction === 'BULLISH' ? 'Buy' : 'Sell',
                entry_zone: top.entry,
                stop_loss: top.stopLoss,
                target: top.target1,
                predicted_high: Math.max(top.entry, top.target1, top.target2 || top.target1),
                predicted_low: Math.min(top.entry, top.stopLoss),
                predicted_close: top.target1,
                rsi: null,
                atr: atrVal,
                adx: null,
                support_levels: null,
                resistance_levels: null,
                fibonacci_levels: null,
                buy_scenario: top.direction === 'BULLISH' ? { entry: top.entry, stopLoss: top.stopLoss, target1: top.target1, target2: top.target2 || top.target1, trigger: top.label } : null,
                sell_scenario: top.direction === 'BEARISH' ? { entry: top.entry, stopLoss: top.stopLoss, target1: top.target1, target2: top.target2 || top.target1, trigger: top.label } : null,
                notes: `${top.label} · R:R ${top.riskReward} · Confidence: ${top.confidence}%`,
              }).catch(err => console.warn('Failed to save prediction:', err))
            }
          }
        }
        }
      }
    } catch (err) {
      setError(err.message || 'Failed to fetch data')
    } finally {
      setLoading(false)
    }
  }, [interval, selectedIndex, notificationsEnabled])

  // Initial fetch
  useEffect(() => { fetchData() }, [fetchData])

  // Auto-polling with dynamic interval based on market phase
  useEffect(() => {
    const tick = () => {
      if (!isMarketOpen()) return
      const minsFromOpen = getMinutesFromMarketOpen()
      const phase = getMarketPhase(minsFromOpen)
      // Use the user-selected interval, but auto-switch to 1m during opening phase
      const effectiveMs = (phase === 'Opening' && minsFromOpen >= 0) ? 60000 : curInt.pollMs
      fetchData()
      return effectiveMs
    }

    let ms = tick()
    if (ms === undefined) return
    pollRef.current = setInterval(() => {
      const nextMs = tick()
      if (nextMs !== ms) {
        clearInterval(pollRef.current)
        ms = nextMs
        pollRef.current = setInterval(tick, ms)
      }
    }, ms)

    return () => clearInterval(pollRef.current)
  }, [curInt.pollMs, fetchData])

  // Chart data and domain
  const chartData = useMemo(() =>
    candles.map(c => ({ time: c.time, close: c.close, open: c.open, high: c.high, low: c.low, volume: c.volume })),
    [candles]
  )

  const chartDomain = useMemo(() => {
    if (!chartData.length) return ['auto', 'auto']
    let lo = Infinity, hi = -Infinity
    for (const d of chartData) { if (d.low < lo) lo = d.low; if (d.high > hi) hi = d.high }
    for (const k of ['r3', 'r2', 'r1', 'pivot', 's1', 's2', 's3']) { const v = pivots?.[k]; if (v < lo) lo = v; if (v > hi) hi = v }
    // Include VWAP in domain
    if (vwap != null) { if (vwap < lo) lo = vwap; if (vwap > hi) hi = vwap }
    // Include active setup levels
    if (activeSetup) {
      for (const k of ['entry', 'stopLoss', 'target1', 'target2', 'target3', 'target4']) { const v = activeSetup[k]; if (v != null) { if (v < lo) lo = v; if (v > hi) hi = v } }
    }
    const pad = (hi - lo) * 0.05
    return [Math.floor(lo - pad), Math.ceil(hi + pad)]
  }, [chartData, pivots, vwap, activeSetup])

  const srLines = pivots ? [
    { y: pivots.r3, l: 'R3', c: '#ef4444' }, { y: pivots.r2, l: 'R2', c: '#ef4444' },
    { y: pivots.r1, l: 'R1', c: '#ef4444' }, { y: pivots.pivot, l: 'P', c: '#6366f1' },
    { y: pivots.s1, l: 'S1', c: '#22c55e' }, { y: pivots.s2, l: 'S2', c: '#22c55e' },
    { y: pivots.s3, l: 'S3', c: '#22c55e' },
  ] : []

  const vwapBias = marketContext?.vwapBias || 'Neutral'

  return (
    <div className="space-y-3 sm:space-y-4">
      {/* Header */}
      <div className="flex flex-wrap items-start justify-between gap-1.5">
        <div className="flex items-center gap-1.5 sm:gap-2">
          <div className="hidden sm:flex w-7 h-7 rounded-lg bg-gradient-to-br from-rose-500 to-pink-600 items-center justify-center shrink-0">
            <Activity className="w-3.5 h-3.5 text-white" />
          </div>
          <div>
            <h2 className="text-xs sm:text-sm font-bold text-gray-800 dark:text-gray-100">Live Intraday — Expert Mode</h2>
            {lastUpdate && (
              <p className="text-[8px] sm:text-[9px] text-gray-400">
                Updated {lastUpdate.toLocaleTimeString('en-IN')} · {candles.length} candles
                {marketContext && <span> · {marketContext.orbState} ORB</span>}
              </p>
            )}
          </div>
        </div>
        <div className="flex items-center gap-1.5 flex-wrap justify-end">
          <select value={selectedIndex} onChange={e => {
              setSelectedIndex(e.target.value)
              setAlerts([])
              setLoading(true)
              prevSignalRef.current = null
              savedPredictionsRef.current = new Set()
            }}
            className="px-1.5 sm:px-2 py-1 bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded text-[9px] sm:text-[10px] font-medium text-gray-600 dark:text-gray-300 max-w-[80px] sm:max-w-none">
            {indices.map(idx => <option key={idx.value} value={idx.value}>{idx.label}</option>)}
          </select>
          <div className="flex rounded border border-gray-200 dark:border-gray-700 overflow-hidden">
            {INTERVALS.map(int => (
              <button key={int.value} onClick={() => { setAlerts([]); setIntervalState(int.value); setCookie('liveInterval', int.value); setLoading(true) }}
                className={`px-1.5 sm:px-2 py-1 text-[9px] sm:text-[10px] font-medium transition-all ${
                  interval === int.value ? 'bg-primary text-primary-foreground' : 'bg-white dark:bg-gray-800 text-gray-500 hover:bg-gray-50 dark:hover:bg-gray-700'
                }`}>{int.label}</button>
            ))}
          </div>
          <button
            onClick={() => {
              if (!notificationsEnabled && 'Notification' in window && Notification.permission === 'default') {
                Notification.requestPermission()
              }
              const next = !notificationsEnabled
              setNotificationsEnabled(next)
              localStorage.setItem('marketmind-notifications', String(next))
            }}
            className={`w-7 h-7 rounded border flex items-center justify-center transition-all ${
              notificationsEnabled
                ? 'bg-indigo-100 dark:bg-indigo-900/30 border-indigo-200 dark:border-indigo-700 text-indigo-500'
                : 'bg-gray-100 dark:bg-gray-800 border-gray-200 dark:border-gray-700 text-gray-400 hover:text-gray-500'
            }`}
            title={notificationsEnabled ? 'Notifications on' : 'Notifications off'}
          >
            {notificationsEnabled ? <Bell className="w-3 h-3" /> : <BellOff className="w-3 h-3" />}
          </button>
          <button onClick={() => { setLoading(true); fetchData() }} className="w-7 h-7 rounded bg-gray-100 dark:bg-gray-800 border border-gray-200 dark:border-gray-700 flex items-center justify-center hover:bg-gray-200 dark:hover:bg-gray-700">
            <RefreshCw className={`w-3 h-3 text-gray-500 ${loading ? 'animate-spin' : ''}`} />
          </button>
        </div>
      </div>

      {error && <div className="text-xs text-red-500 bg-red-50 dark:bg-red-900/20 p-2 rounded">{error}</div>}

      {loading && !candles.length ? (
        <div className="flex items-center justify-center h-64"><div className="w-8 h-8 border-4 border-blue-200 border-t-blue-600 rounded-full animate-spin" /></div>
      ) : (
        <>
          {/* Main Grid: Chart + Sidebar */}
          <div className="grid grid-cols-1 lg:grid-cols-4 gap-3 sm:gap-4">
            {/* Chart */}
            <div className="lg:col-span-3 rounded-xl border border-gray-100 dark:border-gray-700/50 bg-white/90 dark:bg-gray-800/60 p-3 shadow-sm">
              <div className="h-[250px] sm:h-[350px]">
                <ResponsiveContainer width="100%" height="100%">
                  <ComposedChart data={chartData}>
                    <CartesianGrid strokeDasharray="3 3" stroke="#f1f5f9" className="dark:stroke-gray-800" />
                    <XAxis dataKey="time" tick={{ fontSize: 9, fill: '#94a3b8' }} tickLine={false} axisLine={false}
                      tickFormatter={v => { try { return v.split('T')[1]?.slice(0, 5) || v } catch { return v } }} minTickGap={50} />
                    <YAxis yAxisId="price" domain={chartDomain} tick={{ fontSize: 10, fill: '#94a3b8' }} tickLine={false} axisLine={false}
                      tickFormatter={v => v.toLocaleString('en-IN')} />
                    <Tooltip content={({ active, payload }) => {
                      if (!active || !payload?.length) return null
                      const d = payload[0]?.payload; if (!d) return null
                      return (
                        <div className="bg-white dark:bg-gray-800 p-2 rounded-lg shadow border border-gray-100 dark:border-gray-700 text-[10px] space-y-0.5 min-w-[100px]">
                          <p className="text-gray-400 mb-0.5">{d.time?.split('T')[1]?.slice(0, 5) || d.time}</p>
                          <div className="flex justify-between gap-3"><span className="text-gray-400">O</span><span className="font-medium">{d.open?.toFixed(2)}</span></div>
                          <div className="flex justify-between gap-3"><span className="text-gray-400">H</span><span className="font-medium">{d.high?.toFixed(2)}</span></div>
                          <div className="flex justify-between gap-3"><span className="text-gray-400">L</span><span className="font-medium">{d.low?.toFixed(2)}</span></div>
                          <div className="flex justify-between gap-3"><span className="text-gray-400">C</span><span className={`font-bold ${d.close >= d.open ? 'text-emerald-500' : 'text-red-500'}`}>{d.close?.toFixed(2)}</span></div>
                        </div>
                      )
                    }} />

                    {/* Pivot Lines */}
                    {srLines.map(l => (
                      <ReferenceLine key={l.l} y={l.y} yAxisId="price" stroke={l.c} strokeDasharray="6 4" strokeWidth={1} strokeOpacity={0.6}>
                        <Label value={`${l.l}: ${l.y.toLocaleString('en-IN', { minimumFractionDigits: 0 })}`}
                          position="insideTopRight" fontSize={9} fill={l.c} fillOpacity={0.7} />
                      </ReferenceLine>
                    ))}

                    {/* VWAP Line */}
                    {vwap != null && (
                      <ReferenceLine y={vwap} yAxisId="price" stroke="#f97316" strokeDasharray="8 4" strokeWidth={1.5} strokeOpacity={0.8}>
                        <Label value={`VWAP: ${vwap.toLocaleString('en-IN', { minimumFractionDigits: 0 })}`}
                          position="insideTopLeft" fontSize={9} fill="#f97316" fillOpacity={0.8} />
                      </ReferenceLine>
                    )}

                    {/* ORB Zone */}
                    {orbRange.orbHigh != null && orbRange.orbLow != null && (
                      <ReferenceArea y1={orbRange.orbLow} y2={orbRange.orbHigh} yAxisId="price"
                        fill="#f97316" fillOpacity={0.06} stroke="#f97316" strokeOpacity={0.2} strokeDasharray="4 4" />
                    )}

                    {/* Active Setup Entry/SL/Target Markers */}
                    {activeSetup && (
                      <>
                        <ReferenceLine y={activeSetup.entry} yAxisId="price" stroke="#6366f1" strokeWidth={1} strokeOpacity={0.8}>
                          <Label value={`Entry: ${activeSetup.entry.toFixed(0)}`}
                            position="insideBottomLeft" fontSize={9} fill="#6366f1" />
                        </ReferenceLine>
                        <ReferenceLine y={activeSetup.stopLoss} yAxisId="price" stroke="#ef4444" strokeWidth={1} strokeOpacity={0.8}>
                          <Label value={`SL: ${activeSetup.stopLoss.toFixed(0)}`}
                            position="insideBottomLeft" fontSize={9} fill="#ef4444" />
                        </ReferenceLine>
                        <ReferenceLine y={activeSetup.target1} yAxisId="price" stroke="#22c55e" strokeWidth={1} strokeOpacity={0.8}>
                          <Label value={`T1: ${activeSetup.target1.toFixed(0)}`}
                            position="insideBottomLeft" fontSize={9} fill="#22c55e" />
                        </ReferenceLine>
                        {activeSetup.target2 && (
                          <ReferenceLine y={activeSetup.target2} yAxisId="price" stroke="#22c55e" strokeWidth={0.8} strokeOpacity={0.5} strokeDasharray="4 4">
                            <Label value={`T2: ${activeSetup.target2.toFixed(0)}`}
                              position="insideBottomLeft" fontSize={8} fill="#22c55e" fillOpacity={0.6} />
                          </ReferenceLine>
                        )}
                        {activeSetup.target3 && (
                          <ReferenceLine y={activeSetup.target3} yAxisId="price" stroke="#eab308" strokeWidth={0.7} strokeOpacity={0.4} strokeDasharray="6 4">
                            <Label value={`T3: ${activeSetup.target3.toFixed(0)}`}
                              position="insideBottomLeft" fontSize={7} fill="#eab308" fillOpacity={0.5} />
                          </ReferenceLine>
                        )}
                        {activeSetup.target4 && (
                          <ReferenceLine y={activeSetup.target4} yAxisId="price" stroke="#eab308" strokeWidth={0.5} strokeOpacity={0.25} strokeDasharray="8 6">
                            <Label value={`T4: ${activeSetup.target4.toFixed(0)}`}
                              position="insideBottomLeft" fontSize={7} fill="#eab308" fillOpacity={0.35} />
                          </ReferenceLine>
                        )}
                      </>
                    )}

                    {/* Candles */}
                    <Bar yAxisId="price" dataKey="close" shape={<CandlestickShape domain={chartDomain} />} isAnimationActive={false} />
                  </ComposedChart>
                </ResponsiveContainer>
              </div>
            </div>

            {/* Sidebar */}
            <div className="space-y-2 sm:space-y-3">
              {/* 1. Market Context Card */}
              {marketContext && (
                <div className="rounded-xl border border-orange-100/50 dark:border-orange-500/20 bg-gradient-to-br from-white via-orange-50/20 to-white dark:from-gray-800 dark:via-orange-900/10 dark:to-gray-800 p-3 shadow-sm">
                  <div className="flex items-center gap-1.5 mb-2">
                    <Activity className="w-3.5 h-3.5 text-orange-500" />
                    <span className="text-[10px] font-semibold text-gray-700 dark:text-gray-200">Market Context</span>
                  </div>
                  <div className="space-y-1.5 text-[9px]">
                    {/* VWAP */}
                    <div className="flex items-center justify-between">
                      <span className="text-gray-400">VWAP</span>
                      <span className="font-mono font-bold text-orange-600 dark:text-orange-400">{fmt(marketContext.vwapValue)}</span>
                    </div>
                    {/* VWAP Bias */}
                    <div className="flex items-center justify-between">
                      <span className="text-gray-400">VWAP Bias</span>
                      <span className={`inline-flex items-center gap-0.5 px-1.5 py-0.5 rounded text-[8px] font-bold ${
                        vwapBias === 'Bullish' ? 'bg-emerald-100 text-emerald-700 dark:bg-emerald-900/40 dark:text-emerald-400' :
                        vwapBias === 'Bearish' ? 'bg-red-100 text-red-700 dark:bg-red-900/40 dark:text-red-400' :
                        'bg-amber-100 text-amber-700 dark:bg-amber-900/40 dark:text-amber-400'
                      }`}>
                        {vwapBias === 'Bullish' ? <TrendingUp className="w-2.5 h-2.5" /> : vwapBias === 'Bearish' ? <TrendingDown className="w-2.5 h-2.5" /> : null}
                        {vwapBias}
                      </span>
                    </div>
                    {/* Market Direction */}
                    <div className="flex items-center justify-between">
                      <span className="text-gray-400">Direction</span>
                      <span className={`font-mono font-bold text-[8px] ${
                        marketContext.marketDirection?.includes('UPTREND') ? 'text-emerald-500' :
                        marketContext.marketDirection?.includes('DOWNTREND') ? 'text-red-500' : 'text-gray-500'
                      }`}>{marketContext.trend || '--'}</span>
                    </div>
                    {/* RSI */}
                    {marketContext.rsi != null && (
                      <div className="flex items-center justify-between">
                        <span className="text-gray-400">RSI (14)</span>
                        <span className={`font-mono font-bold ${
                          marketContext.rsi > 70 ? 'text-red-500' : marketContext.rsi < 30 ? 'text-emerald-500' : marketContext.rsi > 60 ? 'text-emerald-500' : marketContext.rsi < 40 ? 'text-red-500' : 'text-gray-500'
                        }`}>{marketContext.rsi.toFixed(1)}</span>
                      </div>
                    )}
                    {/* Volume */}
                    {marketContext.volumeAvg > 0 && (
                      <div className="flex items-center justify-between">
                        <span className="text-gray-400">Avg Volume</span>
                        <span className="font-mono font-medium text-gray-600 dark:text-gray-300">{marketContext.volumeAvg.toFixed(0)}</span>
                      </div>
                    )}
                    {/* Price vs VWAP */}
                    <div className="flex items-center justify-between">
                      <span className="text-gray-400">Price vs VWAP</span>
                      <span className={`font-mono font-medium ${marketContext.close > marketContext.vwapValue ? 'text-emerald-500' : 'text-red-500'}`}>
                        {marketContext.close > marketContext.vwapValue ? '+' : ''}{(marketContext.close - marketContext.vwapValue).toFixed(1)}
                      </span>
                    </div>
                    {/* ATR */}
                    <div className="flex items-center justify-between">
                      <span className="text-gray-400">ATR (14)</span>
                      <span className="font-mono font-medium text-gray-700 dark:text-gray-200">{marketContext.atr.toFixed(1)}</span>
                    </div>
                    {/* ORB Status */}
                    <div className="flex items-center justify-between">
                      <span className="text-gray-400">ORB Status</span>
                      <span className={`font-mono font-medium ${
                        marketContext.orbState === 'Broken Up' ? 'text-emerald-500' :
                        marketContext.orbState === 'Broken Down' ? 'text-red-500' :
                        'text-gray-500'
                      }`}>{marketContext.orbState}</span>
                    </div>
                    {/* Trend */}
                    <div className="flex items-center justify-between">
                      <span className="text-gray-400">Trend (3 bars)</span>
                      <span className={`font-mono font-medium ${
                        marketContext.trend === 'UPTREND' ? 'text-emerald-500' :
                        marketContext.trend === 'DOWNTREND' ? 'text-red-500' :
                        'text-gray-500'
                      }`}>{marketContext.trend}</span>
                    </div>
                    {/* Trend Strength */}
                    <div className="flex items-center justify-between">
                      <span className="text-gray-400">Trend Strength</span>
                      <span className={`font-mono font-medium text-[8px] ${
                        marketContext.trendStrength === 'STRONG' ? 'text-emerald-500' :
                        marketContext.trendStrength === 'MODERATE' ? 'text-amber-500' : 'text-gray-500'
                      }`}>{marketContext.trendStrength || '--'}</span>
                    </div>
                    {/* Swing Highs / Lows */}
                    {marketContext.swingHighs?.length > 0 && (
                      <div className="flex items-center justify-between">
                        <span className="text-gray-400">Swing Highs</span>
                        <span className="font-mono font-medium text-red-400 text-[8px]">
                          {marketContext.swingHighs.slice(-3).map(s => s.toFixed(0)).join(', ')}
                        </span>
                      </div>
                    )}
                    {marketContext.swingLows?.length > 0 && (
                      <div className="flex items-center justify-between">
                        <span className="text-gray-400">Swing Lows</span>
                        <span className="font-mono font-medium text-emerald-400 text-[8px]">
                          {marketContext.swingLows.slice(-3).map(s => s.toFixed(0)).join(', ')}
                        </span>
                      </div>
                    )}
                    {/* Market Phase */}
                    <div className="flex items-center justify-between">
                      <span className="text-gray-400">Phase</span>
                      <span className="font-mono font-medium text-gray-600 dark:text-gray-300">
                        {getMarketPhase(getMinutesFromMarketOpen())}
                      </span>
                    </div>
                  </div>
                </div>
              )}

              {/* 2. Active Setup Card */}
              {activeSetup ? (
                <div className={`rounded-xl border p-3 shadow-sm ${
                  activeSetup.direction === 'BULLISH'
                    ? 'border-emerald-200/70 dark:border-emerald-800/30 bg-gradient-to-br from-white via-emerald-50/30 to-white dark:from-gray-800 dark:via-emerald-900/20 dark:to-gray-800'
                    : 'border-red-200/70 dark:border-red-800/30 bg-gradient-to-br from-white via-red-50/30 to-white dark:from-gray-800 dark:via-red-900/20 dark:to-gray-800'
                }`}>
                  <div className="flex items-center gap-1.5 mb-2">
                    {activeSetup.direction === 'BULLISH' ? <TrendingUp className="w-3.5 h-3.5 text-emerald-500" /> : <TrendingDown className="w-3.5 h-3.5 text-red-500" />}
                    <span className="text-[10px] font-semibold text-gray-700 dark:text-gray-200">{activeSetup.label}</span>
                    <span className={`ml-auto text-[8px] font-bold px-1.5 py-0.5 rounded ${
                      activeSetup.confidence >= 70 ? 'bg-emerald-100 text-emerald-700 dark:bg-emerald-900/40 dark:text-emerald-400' :
                      activeSetup.confidence >= 50 ? 'bg-amber-100 text-amber-700 dark:bg-amber-900/40 dark:text-amber-400' :
                      'bg-gray-100 text-gray-600'
                    }`}>
                      {activeSetup.confidence}%
                    </span>
                  </div>

                  {/* Valid/Invalid badge */}
                  {activeSetup.valid === false && (
                    <div className="text-[8px] bg-red-50 dark:bg-red-900/20 text-red-600 dark:text-red-400 px-1.5 py-1 rounded mb-1.5">
                      ⛔ {activeSetup.rejectionReason}
                    </div>
                  )}

                  {activeSetup.direction === 'BULLISH' ? (
                    <div className="text-[9px] text-emerald-700 dark:text-emerald-300 font-bold mb-1.5 flex items-center gap-1">
                      <TrendingUp className="w-3 h-3" /> Buy Call
                    </div>
                  ) : (
                    <div className="text-[9px] text-red-700 dark:text-red-300 font-bold mb-1.5 flex items-center gap-1">
                      <TrendingDown className="w-3 h-3" /> Buy Put
                    </div>
                  )}

                  <div className="space-y-1 text-[9px]">
                    <div className="flex justify-between">
                      <span className="text-gray-400">Entry</span>
                      <span className="font-mono font-bold text-gray-700 dark:text-gray-200">{fmt(activeSetup.entry)}</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="flex items-center gap-1 text-gray-400"><ShieldAlert className="w-2.5 h-2.5" /> SL</span>
                      <span className="font-mono font-bold text-red-500">{fmt(activeSetup.stopLoss)}</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="flex items-center gap-1 text-gray-400"><Target className="w-2.5 h-2.5" /> T1</span>
                      <span className="font-mono font-bold text-emerald-500">{fmt(activeSetup.target1)}</span>
                    </div>
                    {activeSetup.target2 && (
                      <div className="flex justify-between">
                        <span className="text-gray-400">T2</span>
                        <span className="font-mono font-bold text-emerald-400">{fmt(activeSetup.target2)}</span>
                      </div>
                    )}
                    {activeSetup.target3 && (
                      <div className="flex justify-between">
                        <span className="text-gray-400">T3</span>
                        <span className="font-mono font-bold text-yellow-500">{fmt(activeSetup.target3)}</span>
                      </div>
                    )}
                    {activeSetup.target4 && (
                      <div className="flex justify-between">
                        <span className="text-gray-400">T4</span>
                        <span className="font-mono font-bold text-amber-400">{fmt(activeSetup.target4)}</span>
                      </div>
                    )}
                    <div className="border-t border-gray-100 dark:border-gray-700 my-1 pt-1">
                      <div className="flex justify-between">
                        <span className="text-gray-400">Risk</span>
                        <span className="font-mono font-medium text-red-400">{activeSetup.riskAmount.toFixed(0)} pts</span>
                      </div>
                      <div className="flex justify-between">
                        <span className="text-gray-400">Reward</span>
                        <span className="font-mono font-medium text-emerald-400">{activeSetup.rewardAmount.toFixed(0)} pts</span>
                      </div>
                      <div className="flex justify-between mt-1 pt-1 border-t border-gray-100 dark:border-gray-700">
                        <span className="text-gray-400 font-semibold">R:R</span>
                        <span className={`font-mono font-bold text-[11px] ${activeSetup.riskReward >= 2 ? 'text-emerald-500' : activeSetup.riskReward >= 1 ? 'text-amber-500' : 'text-red-500'}`}>
                          1:{activeSetup.riskReward.toFixed(1)}
                        </span>
                      </div>
                    </div>
                  </div>

                  {/* Entry reason */}
                  {activeSetup.entryReason && (
                    <div className="mt-1.5 pt-1.5 border-t border-gray-100 dark:border-gray-700">
                      <div className="text-[8px] text-gray-500 mb-0.5">Why entry?</div>
                      <div className="text-[7px] text-gray-500 leading-tight">{activeSetup.entryReason}</div>
                    </div>
                  )}

                  {/* SL reason */}
                  {activeSetup.slReason && (
                    <div className="mt-1 pt-1">
                      <div className="text-[8px] text-gray-500 mb-0.5">Why SL here?</div>
                      <div className="text-[7px] text-red-400 leading-tight">{activeSetup.slReason}</div>
                    </div>
                  )}

                  {vwapBias !== 'Neutral' && (
                    <div className={`mt-2 text-[7px] text-center px-1 py-0.5 rounded ${
                      (vwapBias === 'Bullish' && activeSetup.direction === 'BULLISH') || (vwapBias === 'Bearish' && activeSetup.direction === 'BEARISH')
                        ? 'bg-emerald-50 text-emerald-600 dark:bg-emerald-900/30 dark:text-emerald-400'
                        : 'bg-amber-50 text-amber-600 dark:bg-amber-900/30 dark:text-amber-400'
                    }`}>
                      {vwapBias === activeSetup.direction ? '✓ Aligned with VWAP' : '⚠️ VWAP Neutral zone'}
                    </div>
                  )}
                </div>
              ) : (
                <div className="rounded-xl border border-gray-100 dark:border-gray-700/50 bg-white/80 dark:bg-gray-800/60 p-3 shadow-sm">
                  <div className="flex items-center gap-1.5 mb-2">
                    <Brain className="w-3.5 h-3.5 text-indigo-500" />
                    <span className="text-[10px] font-semibold text-gray-700 dark:text-gray-200">Expert Setup</span>
                  </div>
                  <div className="text-center py-3 text-[10px] text-gray-400">
                    No active setup detected
                  </div>
                </div>
              )}

              {/* 3. Intraday Pivots */}
              {pivots && (
                <div className="rounded-xl border border-gray-100 dark:border-gray-700/50 bg-white/80 dark:bg-gray-800/60 p-3 shadow-sm">
                  <h3 className="text-[10px] font-semibold text-gray-500 dark:text-gray-400 mb-1.5">Intraday Pivots</h3>
                  {[
                    { l: 'R3', v: pivots.r3, c: 'text-red-500' }, { l: 'R2', v: pivots.r2, c: 'text-red-500' },
                    { l: 'R1', v: pivots.r1, c: 'text-red-500' }, { l: 'P', v: pivots.pivot, c: 'text-indigo-500' },
                    { l: 'S1', v: pivots.s1, c: 'text-emerald-500' }, { l: 'S2', v: pivots.s2, c: 'text-emerald-500' },
                    { l: 'S3', v: pivots.s3, c: 'text-emerald-500' },
                  ].map(l => (
                    <div key={l.l} className="flex justify-between text-[10px] py-0.5 px-1.5 rounded bg-gray-50 dark:bg-gray-700/30 mb-0.5">
                      <span className="font-semibold text-gray-400">{l.l}</span>
                      <span className={`font-mono font-medium ${l.c}`}>{fmt(l.v)}</span>
                    </div>
                  ))}
                </div>
              )}

              {/* 4. Reference Levels */}
              {dailyRefs && (
                <div className="rounded-xl border border-gray-100 dark:border-gray-700/50 bg-white/80 dark:bg-gray-800/60 p-3 shadow-sm">
                  <h3 className="text-[10px] font-semibold text-gray-500 dark:text-gray-400 mb-1.5">Reference Levels</h3>
                  <div className="text-[9px] space-y-1">
                    <div className="flex justify-between"><span className="text-gray-400">Prev High</span><span className="font-mono font-medium text-red-500">{fmt(dailyRefs.prevDayHigh)}</span></div>
                    <div className="flex justify-between"><span className="text-gray-400">Prev Low</span><span className="font-mono font-medium text-emerald-500">{fmt(dailyRefs.prevDayLow)}</span></div>
                    <div className="flex justify-between"><span className="text-gray-400">Prev Close</span><span className="font-mono font-medium text-gray-500">{fmt(dailyRefs.prevDayClose)}</span></div>
                    <div className="flex justify-between"><span className="text-gray-400">Prev Range</span><span className="font-mono font-medium text-gray-500">{fmt(dailyRefs.prevDayRange)}</span></div>
                    <div className="border-t border-gray-100 dark:border-gray-700 my-1" />
                    <div className="flex justify-between"><span className="text-gray-400">Weekly High</span><span className="font-mono font-medium text-red-500">{fmt(dailyRefs.weeklyHigh)}</span></div>
                    <div className="flex justify-between"><span className="text-gray-400">Weekly Low</span><span className="font-mono font-medium text-emerald-500">{fmt(dailyRefs.weeklyLow)}</span></div>
                  </div>
                </div>
              )}

              {/* 5. Fibonacci Levels */}
              {expertSetups.length > 0 && activeSetup?.target2 && (
                <div className="rounded-xl border border-gray-100 dark:border-gray-700/50 bg-white/80 dark:bg-gray-800/60 p-3 shadow-sm">
                  <h3 className="text-[10px] font-semibold text-gray-500 dark:text-gray-400 mb-1.5">Trade Levels</h3>
                  <div className="text-[9px] space-y-1">
                    <div className="flex justify-between"><span className="text-gray-400">Entry</span><span className="font-mono font-medium text-indigo-500">{fmt(activeSetup.entry)}</span></div>
                    <div className="flex justify-between"><span className="text-gray-400">Stop Loss</span><span className="font-mono font-medium text-red-500">{fmt(activeSetup.stopLoss)}</span></div>
                    <div className="flex justify-between"><span className="text-gray-400">Target 1</span><span className="font-mono font-medium text-emerald-500">{fmt(activeSetup.target1)}</span></div>
                    <div className="flex justify-between"><span className="text-gray-400">Target 2</span><span className="font-mono font-medium text-emerald-400">{fmt(activeSetup.target2)}</span></div>
                    <div className="border-t border-gray-100 dark:border-gray-700 my-1 pt-1">
                      <div className="flex justify-between"><span className="text-gray-400 font-semibold">R:R</span><span className={`font-mono font-bold ${activeSetup.riskReward >= 2 ? 'text-emerald-500' : activeSetup.riskReward >= 1 ? 'text-amber-500' : 'text-red-500'}`}>1:{activeSetup.riskReward.toFixed(1)}</span></div>
                    </div>
                  </div>
                </div>
              )}
            </div>
          </div>

          {/* Alert Table */}
          <div className="rounded-xl border border-gray-100 dark:border-gray-700/50 bg-white/90 dark:bg-gray-800/60 p-3 shadow-sm">
            <div className="flex items-center justify-between mb-2">
              <span className="text-[10px] font-semibold text-gray-500 dark:text-gray-400">Expert Alert History</span>
              <div className="flex items-center gap-2 text-[8px] text-gray-400">
                <Clock className="w-2.5 h-2.5" /> Every {curInt.label}
                <button onClick={() => setAlerts([])} className="text-red-400 hover:text-red-500">Clear</button>
              </div>
            </div>
            {alerts.length === 0 ? (
              <div className="text-center py-4 text-[10px] text-gray-400">
                AI Engine monitoring live market...<br />
                <span className="text-[8px] text-gray-500">Only validated setups with minimum 1:2 RR appear here</span>
              </div>
            ) : (
              <div className="overflow-x-auto max-h-[300px] overflow-y-auto">
                <table className="w-full text-[9px]">
                  <thead className="text-gray-400 border-b border-gray-100 dark:border-gray-700 sticky top-0 bg-white dark:bg-gray-800">
                    <tr>
                      <th className="text-left py-1 pr-1 font-medium">Time</th>
                      <th className="text-left pr-1 font-medium">Setup</th>
                      <th className="text-center pr-1 font-medium">Conf</th>
                      <th className="text-center pr-1 font-medium">Bias</th>
                      <th className="text-right pr-1 font-medium">Entry</th>
                      <th className="text-right pr-1 font-medium">SL</th>
                      <th className="text-right pr-1 font-medium">T1</th>
                      <th className="text-right pr-1 font-medium">T2</th>
                      <th className="text-right pr-1 font-medium">R:R</th>
                    </tr>
                  </thead>
                  <tbody>
                    {alerts.map(a => (
                      <tr key={a.id} className={`border-b border-gray-50 dark:border-gray-700/30 hover:bg-gray-50 dark:hover:bg-gray-700/20 ${a.valid === false ? 'opacity-50' : ''}`}>
                        <td className="py-1 pr-1 text-gray-500 font-mono whitespace-nowrap text-[8px]">{a.time}</td>
                        <td className="pr-1">
                          <span className={`inline-flex items-center gap-0.5 px-1 py-0.5 rounded text-[8px] font-medium max-w-[100px] truncate ${
                            a.direction === 'BULLISH' ? 'bg-emerald-50 text-emerald-600 dark:bg-emerald-900/30 dark:text-emerald-400' :
                            a.direction === 'BEARISH' ? 'bg-red-50 text-red-600 dark:bg-red-900/30 dark:text-red-400' : 'bg-gray-50 text-gray-500'
                          }`}>
                            {a.valid === false && '⛔'}
                            {a.setupLabel || a.direction}
                          </span>
                        </td>
                        <td className={`text-center pr-1 font-mono font-bold text-[8px] ${
                          a.confidence >= 70 ? 'text-emerald-500' : a.confidence >= 50 ? 'text-amber-500' : 'text-gray-500'
                        }`}>{a.confidence}%</td>
                        <td className={`text-center pr-1 font-medium text-[8px] ${a.bias === 'Buy Call' ? 'text-emerald-600' : a.bias === 'Buy Put' ? 'text-red-600' : 'text-amber-600'}`}>{a.bias}</td>
                        <td className="text-right pr-1 font-mono text-emerald-600">{fmt(a.entry)}</td>
                        <td className="text-right pr-1 font-mono text-red-500">{fmt(a.sl)}</td>
                        <td className="text-right pr-1 font-mono text-emerald-500">{fmt(a.target)}</td>
                        <td className="text-right pr-1 font-mono text-emerald-400">{a.target2 ? fmt(a.target2) : '--'}</td>
                        <td className={`text-right pr-1 font-mono font-bold text-[9px] ${a.riskReward >= 2 ? 'text-emerald-500' : a.riskReward >= 1 ? 'text-amber-500' : 'text-red-500'}`}>
                          1:{a.riskReward.toFixed(1)}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        </>
      )}
    </div>
  )
}
