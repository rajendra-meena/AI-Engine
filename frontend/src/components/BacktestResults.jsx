import React, { useState, useEffect, useCallback } from 'react'
import {
  Brain, TrendingUp, TrendingDown, Target, ShieldAlert,
  AlertCircle, RefreshCw, ChevronDown, ChevronRight, Clock,
  CheckCircle2, XCircle, MinusCircle, AlertTriangle, Trash2, Download,
} from 'lucide-react'
import { getPredictions, getPredictionStats, checkResults, deduplicatePredictions, deletePrediction } from '../utils/api'
import { exportToCSV, getPredictionExportColumns } from '../utils/exportData'
import useMarketStore from '../store/useMarketStore'

/* ── Delete confirmation modal ── */
function ConfirmDeleteModal({ show, onClose, onConfirm, symbol, date }) {
  if (!show) return null
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center px-4">
      <div className="absolute inset-0 bg-black/40 backdrop-blur-sm" onClick={onClose} />
      <div className="relative bg-white dark:bg-gray-800 rounded-xl shadow-2xl border border-gray-200 dark:border-gray-700 max-w-sm w-full p-5 animate-fadeIn">
        <div className="flex items-center gap-3 mb-4">
          <div className="w-10 h-10 rounded-full bg-red-50 dark:bg-red-900/30 flex items-center justify-center shrink-0">
            <Trash2 className="w-5 h-5 text-red-500" />
          </div>
          <div>
            <h3 className="text-sm font-bold text-gray-800 dark:text-gray-100">Delete Prediction</h3>
            <p className="text-[10px] text-gray-400 dark:text-gray-500 mt-0.5">This action cannot be undone</p>
          </div>
        </div>
        <p className="text-xs text-gray-600 dark:text-gray-300 mb-5 leading-relaxed">
          Are you sure you want to delete the prediction for{' '}
          <strong className="text-gray-800 dark:text-gray-100">{symbol}</strong>
          {' '}on{' '}
          <strong className="text-gray-800 dark:text-gray-100">{date}</strong>?
        </p>
        <div className="flex items-center gap-2 justify-end">
          <button
            onClick={onClose}
            className="px-4 py-2 text-[11px] font-medium rounded-lg bg-gray-100 dark:bg-gray-700 text-gray-600 dark:text-gray-300 hover:bg-gray-200 dark:hover:bg-gray-600 transition-colors"
          >
            Cancel
          </button>
          <button
            onClick={onConfirm}
            className="px-4 py-2 text-[11px] font-medium rounded-lg bg-red-500 hover:bg-red-600 text-white transition-colors shadow-sm"
          >
            Delete
          </button>
        </div>
      </div>
    </div>
  )
}

const STATUS_CONFIG = {
  PENDING: { label: 'Pending', classes: 'bg-amber-50 text-amber-600 dark:bg-amber-900/30 dark:text-amber-400 border-amber-200/50 dark:border-amber-700/30', icon: Clock },
  HIT_TARGET: { label: 'Hit Target', classes: 'bg-emerald-50 text-emerald-600 dark:bg-emerald-900/30 dark:text-emerald-400 border-emerald-200/50 dark:border-emerald-700/30', icon: CheckCircle2 },
  HIT_STOPLOSS: { label: 'Hit Stoploss', classes: 'bg-red-50 text-red-600 dark:bg-red-900/30 dark:text-red-400 border-red-200/50 dark:border-red-700/30', icon: XCircle },
  NO_TRADE: { label: 'No Trade', classes: 'bg-gray-50 text-gray-500 dark:bg-gray-800/50 dark:text-gray-400 border-gray-200/50 dark:border-gray-700/30', icon: MinusCircle },
  UNCHECKED: { label: 'Unchecked', classes: 'bg-orange-50 text-orange-600 dark:bg-orange-900/30 dark:text-orange-400 border-orange-200/50 dark:border-orange-700/30', icon: AlertTriangle },
}

const FMT = (v) => v != null ? v.toLocaleString('en-IN', { minimumFractionDigits: 2 }) : '--'

function StatusBadge({ status }) {
  const cfg = STATUS_CONFIG[status] || STATUS_CONFIG.PENDING
  const Icon = cfg.icon
  return (
    <span className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] font-medium border ${cfg.classes}`}>
      <Icon className="w-3 h-3" />
      {cfg.label}
    </span>
  )
}

function StatCard({ label, value, sub, color }) {
  return (
    <div className="stats-card">
      <div className="text-[10px] font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider mb-1">{label}</div>
      <div className={`text-xl sm:text-2xl font-bold tracking-tight ${color || 'text-gray-900 dark:text-gray-100'}`}>
        {value != null ? value : '--'}
      </div>
      {sub != null && <div className="text-[10px] text-gray-400 dark:text-gray-500 mt-0.5">{sub}</div>}
    </div>
  )
}

export default function BacktestResults() {
  const { indices, selectedIndex, setSelectedIndex } = useMarketStore()
  const [predictions, setPredictions] = useState([])
  const [stats, setStats] = useState(null)
  const [loading, setLoading] = useState(true)
  const [checking, setChecking] = useState(false)
  const [cleaning, setCleaning] = useState(false)
  const [error, setError] = useState(null)
  const [statusFilter, setStatusFilter] = useState('')
  const [intervalFilter, setIntervalFilter] = useState('')
  const [expandedId, setExpandedId] = useState(null)
  const [checkResult, setCheckResult] = useState(null)
  const [currentPage, setCurrentPage] = useState(1)
  const [deleteTarget, setDeleteTarget] = useState(null) // { id, symbol, date } or null
  const PAGE_SIZE = 20

  const fetchData = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const [preds, st] = await Promise.all([
        getPredictions({ limit: 100 }),
        getPredictionStats(),
      ])
      // Sort by newest first (they already come sorted, but ensure it)
      setPredictions(Array.isArray(preds) ? preds : [])
      setStats(st || null)
    } catch (err) {
      setError(err.response?.data?.detail || err.message || 'Failed to load data')
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => { fetchData() }, [fetchData])

  const handleCheckResults = async () => {
    setChecking(true)
    setCheckResult(null)
    try {
      const result = await checkResults()
      setCheckResult(result)
      await fetchData() // refresh
    } catch (err) {
      setCheckResult({ checked: 0, results: [], message: err.message || 'Check failed' })
    } finally {
      setChecking(false)
    }
  }

  const handleCleanup = async () => {
    setCleaning(true)
    try {
      const result = await deduplicatePredictions()
      setCheckResult({ checked: 0, results: [], message: `🧹 ${result.message}` })
      await fetchData()
    } catch (err) {
      setCheckResult({ checked: 0, results: [], message: `Cleanup failed: ${err.message}` })
    } finally {
      setCleaning(false)
    }
  }

  const handleDeleteClick = (id, symbol, date) => {
    setDeleteTarget({ id, symbol, date })
  }

  const handleDeleteConfirm = async () => {
    if (!deleteTarget) return
    try {
      await deletePrediction(deleteTarget.id)
      setDeleteTarget(null)
      await fetchData()
    } catch (err) {
      console.error("Delete failed:", err)
      setDeleteTarget(null)
    }
  }

  const handleDeleteCancel = () => setDeleteTarget(null)

  const filtered = predictions.filter(p => {
    if (selectedIndex && p.symbol !== selectedIndex) return false
    if (statusFilter && p.status !== statusFilter) return false
    if (intervalFilter && p.interval !== intervalFilter) return false
    return true
  })

  // Pagination
  const totalPages = Math.ceil(filtered.length / PAGE_SIZE)
  const paginatedData = filtered.slice((currentPage - 1) * PAGE_SIZE, currentPage * PAGE_SIZE)

  // Reset to page 1 when filters change
  useEffect(() => { setCurrentPage(1) }, [selectedIndex, statusFilter, intervalFilter])

  const handleExport = () => {
    exportToCSV(filtered, getPredictionExportColumns(), `marketmind-predictions-${new Date().toISOString().split('T')[0]}`)
  }

  // ── Render ──
  return (
    <div className="space-y-4 sm:space-y-6">
      {/* Header */}
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div className="flex items-center gap-2">
          <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-violet-500 to-purple-600 flex items-center justify-center shadow-lg shadow-violet-200 dark:shadow-violet-900/30">
            <Brain className="w-4 h-4 text-white" />
          </div>
          <div>
            <h2 className="text-sm sm:text-base font-bold text-gray-800 dark:text-gray-100">Backtest Results</h2>
            <p className="text-[9px] sm:text-[10px] text-gray-400 dark:text-gray-500">
              Track prediction accuracy &amp; trade outcomes
            </p>
          </div>
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={handleCheckResults}
            disabled={checking}
            className="inline-flex items-center gap-1.5 px-3 py-1.5 bg-primary text-primary-foreground text-[11px] font-medium rounded-lg hover:bg-primary/90 transition-all disabled:opacity-50 shadow-sm"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${checking ? 'animate-spin' : ''}`} />
            {checking ? 'Checking...' : 'Check Results'}
          </button>
          <button
            onClick={handleCleanup}
            disabled={cleaning}
            className="inline-flex items-center gap-1.5 px-3 py-1.5 bg-white dark:bg-gray-800 text-gray-600 dark:text-gray-300 border border-gray-200 dark:border-gray-700 text-[11px] font-medium rounded-lg hover:bg-gray-50 dark:hover:bg-gray-700 transition-all disabled:opacity-50"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${cleaning ? 'animate-spin' : ''}`} />
            {cleaning ? 'Cleaning...' : 'Cleanup Dups'}
          </button>
          <button
            onClick={handleExport}
            disabled={filtered.length === 0}
            className="inline-flex items-center gap-1.5 px-3 py-1.5 bg-white dark:bg-gray-800 text-gray-600 dark:text-gray-300 border border-gray-200 dark:border-gray-700 text-[11px] font-medium rounded-lg hover:bg-gray-50 dark:hover:bg-gray-700 transition-all disabled:opacity-50"
          >
            <Download className="w-3.5 h-3.5" />
            Export CSV
          </button>
        </div>
      </div>

      {/* Check result banner */}
      {checkResult && (
        <div className={`px-3 py-2 rounded-lg border text-[11px] ${
          checkResult.checked > 0
            ? 'bg-emerald-50 dark:bg-emerald-900/20 border-emerald-200/50 dark:border-emerald-800/30 text-emerald-700 dark:text-emerald-300'
            : 'bg-gray-50 dark:bg-gray-800/30 border-gray-200/50 dark:border-gray-700/30 text-gray-500'
        }`}>
          <span className="font-medium">Checked {checkResult.checked} predictions:</span>
          {checkResult.results?.map(r => (
            <span key={r.id} className="ml-2">
              {r.symbol} ({r.predicted_date}) → {r.status}
              {r.outcome ? ` — ${r.outcome}` : ''}
            </span>
          ))}
          {(!checkResult.results || checkResult.results.length === 0) && (
            <span className="ml-1">{checkResult.message}</span>
          )}
        </div>
      )}

      {/* Error state */}
      {error && (
        <div className="flex items-center gap-2 p-3 bg-red-50 dark:bg-red-900/20 rounded-lg border border-red-200/50 dark:border-red-800/30">
          <AlertCircle className="w-4 h-4 text-red-500 shrink-0" />
          <span className="text-xs text-red-600 dark:text-red-400">{error}</span>
          <button onClick={fetchData} className="ml-auto text-xs text-red-500 hover:text-red-400 underline">Retry</button>
        </div>
      )}

      {/* Stats Cards */}
      {stats && (
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
          <StatCard label="Total Predictions" value={stats.total_predictions} color="text-gray-900 dark:text-gray-100" />
          <StatCard
            label="Hit Rate"
            value={stats.total_checked > 0 ? `${stats.hit_rate}%` : '--'}
            sub={stats.total_checked > 0 ? `${stats.status_breakdown?.HIT_TARGET || 0}/${stats.total_checked}` : null}
            color="text-emerald-600 dark:text-emerald-400"
          />
          <StatCard
            label="Stoploss Rate"
            value={stats.total_checked > 0 ? `${stats.stoploss_rate}%` : '--'}
            sub={stats.total_checked > 0 ? `${stats.status_breakdown?.HIT_STOPLOSS || 0}/${stats.total_checked}` : null}
            color="text-red-600 dark:text-red-400"
          />
          <StatCard
            label="No Trade"
            value={stats.total_checked > 0 ? `${stats.no_trade_rate}%` : '--'}
            sub={`${stats.status_breakdown?.NO_TRADE || 0} unchecked: ${stats.status_breakdown?.PENDING || 0}`}
            color="text-gray-500 dark:text-gray-400"
          />
        </div>
      )}

      {/* Filter bar */}
      <div className="flex flex-wrap items-center gap-2">
        <select
          value={selectedIndex}
          onChange={(e) => setSelectedIndex(e.target.value)}
          className="px-2 py-1.5 bg-white/80 dark:bg-gray-800/80 border border-gray-200 dark:border-gray-700 rounded-lg text-[11px] font-medium text-gray-700 dark:text-gray-200"
        >
          <option value="">All Symbols</option>
          {indices.map(idx => <option key={idx.value} value={idx.value}>{idx.label}</option>)}
        </select>
        <select
          value={statusFilter}
          onChange={(e) => setStatusFilter(e.target.value)}
          className="px-2 py-1.5 bg-white/80 dark:bg-gray-800/80 border border-gray-200 dark:border-gray-700 rounded-lg text-[11px] font-medium text-gray-700 dark:text-gray-200"
        >
          <option value="">All Statuses</option>
          <option value="PENDING">Pending</option>
          <option value="HIT_TARGET">Hit Target</option>
          <option value="HIT_STOPLOSS">Hit Stoploss</option>
          <option value="NO_TRADE">No Trade</option>
          <option value="UNCHECKED">Unchecked</option>
        </select>
        <select
          value={intervalFilter}
          onChange={(e) => setIntervalFilter(e.target.value)}
          className="px-2 py-1.5 bg-white/80 dark:bg-gray-800/80 border border-gray-200 dark:border-gray-700 rounded-lg text-[11px] font-medium text-gray-700 dark:text-gray-200"
        >
          <option value="">All Intervals</option>
          <option value="15m">15m (Live)</option>
          <option value="4D">4D</option>
          <option value="1W">1W</option>
          <option value="2W">2W</option>
          <option value="1M">1M</option>
          <option value="45D">45D</option>
          <option value="2M">2M</option>
        </select>
        <span className="text-[10px] text-gray-400 ml-auto">
          {filtered.length} of {predictions.length} predictions
        </span>
      </div>

      {/* Loading state */}
      {loading ? (
        <div className="flex items-center justify-center min-h-[200px]">
          <div className="text-center">
            <div className="w-8 h-8 border-4 border-violet-200 border-t-violet-600 rounded-full animate-spin mx-auto mb-3" />
            <p className="text-xs text-gray-400">Loading prediction history...</p>
          </div>
        </div>
      ) : filtered.length === 0 ? (
        /* Empty state */
        <div className="flex items-center justify-center min-h-[200px]">
          <div className="text-center">
            <div className="w-12 h-12 bg-gray-100 dark:bg-gray-800 rounded-full flex items-center justify-center mx-auto mb-3">
              <Target className="w-6 h-6 text-gray-400" />
            </div>
            <p className="text-sm font-medium text-gray-600 dark:text-gray-400 mb-1">No predictions found</p>
            <p className="text-[11px] text-gray-400 dark:text-gray-500">
              Switch to the Live page to generate predictions, then check results here.
            </p>
          </div>
        </div>
      ) : (
        /* Results table */
        <div className="rounded-xl border border-gray-100 dark:border-gray-700/50 bg-white/90 dark:bg-gray-800/60 shadow-sm overflow-hidden">
          <div className="overflow-x-auto">
            <table className="w-full text-[11px]">
              <thead>
                <tr className="border-b border-gray-100 dark:border-gray-700/50 bg-gray-50/50 dark:bg-gray-800/80">
                  <th className="text-left py-2.5 px-3 font-semibold text-gray-500 dark:text-gray-400">Date</th>
                  <th className="text-left py-2.5 px-3 font-semibold text-gray-500 dark:text-gray-400">Symbol</th>
                  <th className="text-left py-2.5 px-3 font-semibold text-gray-500 dark:text-gray-400">Interval</th>
                  <th className="text-left py-2.5 px-3 font-semibold text-gray-500 dark:text-gray-400">Direction</th>
                  <th className="text-right py-2.5 px-3 font-semibold text-gray-500 dark:text-gray-400">Conf.</th>
                  <th className="text-center py-2.5 px-3 font-semibold text-gray-500 dark:text-gray-400">Bias</th>
                  <th className="text-right py-2.5 px-3 font-semibold text-gray-500 dark:text-gray-400">Entry</th>
                  <th className="text-right py-2.5 px-3 font-semibold text-gray-500 dark:text-gray-400">SL</th>
                  <th className="text-right py-2.5 px-3 font-semibold text-gray-500 dark:text-gray-400">Target</th>
                  <th className="text-center py-2.5 px-3 font-semibold text-gray-500 dark:text-gray-400">Status</th>
                  <th className="py-2.5 px-1 w-8"></th>
                  <th className="py-2.5 px-1 w-8"></th>
                </tr>
              </thead>
              <tbody>
                {paginatedData.map((p) => {
                  const isExpanded = expandedId === p.id
                  const isBullish = p.direction === 'BULLISH'
                  return (
                    <React.Fragment key={p.id}>
                      <tr
                        onClick={() => setExpandedId(isExpanded ? null : p.id)}
                        className="border-b border-gray-50 dark:border-gray-700/30 hover:bg-gray-50/50 dark:hover:bg-gray-700/20 cursor-pointer transition-colors"
                      >
                        <td className="py-2.5 px-3 text-gray-700 dark:text-gray-200 whitespace-nowrap font-medium">
                          {p.predicted_date}
                        </td>
                        <td className="py-2.5 px-3 text-gray-600 dark:text-gray-300">{p.symbol}</td>
                        <td className="py-2.5 px-3 text-gray-600 dark:text-gray-300 font-mono text-[10px]">{p.interval}</td>
                        <td className="py-2.5 px-3">
                          <span className={`inline-flex items-center gap-1 px-1.5 py-0.5 rounded text-[10px] font-medium ${
                            isBullish
                              ? 'bg-emerald-50 text-emerald-600 dark:bg-emerald-900/30 dark:text-emerald-400'
                              : p.direction === 'BEARISH'
                                ? 'bg-red-50 text-red-600 dark:bg-red-900/30 dark:text-red-400'
                                : 'bg-gray-50 text-gray-500 dark:bg-gray-800 dark:text-gray-400'
                          }`}>
                            {isBullish ? <TrendingUp className="w-2.5 h-2.5" /> : p.direction === 'BEARISH' ? <TrendingDown className="w-2.5 h-2.5" /> : null}
                            {p.trend_label || p.direction}
                          </span>
                        </td>
                        <td className="py-2.5 px-3 text-right font-mono font-medium text-gray-700 dark:text-gray-200">
                          {p.confidence != null ? `${p.confidence}%` : '--'}
                        </td>
                        <td className="py-2.5 px-3 text-center">
                          <span className={`text-[10px] font-bold ${
                            p.suggested_bias === 'Buy' ? 'text-emerald-600 dark:text-emerald-400' :
                            p.suggested_bias === 'Sell' ? 'text-red-600 dark:text-red-400' :
                            'text-amber-600 dark:text-amber-400'
                          }`}>
                            {p.suggested_bias || '--'}
                          </span>
                        </td>
                        <td className="py-2.5 px-3 text-right font-mono text-gray-700 dark:text-gray-200">{FMT(p.entry_zone)}</td>
                        <td className="py-2.5 px-3 text-right font-mono text-red-500">{FMT(p.stop_loss)}</td>
                        <td className="py-2.5 px-3 text-right font-mono text-emerald-600 dark:text-emerald-400">{FMT(p.target)}</td>
                        <td className="py-2.5 px-3 text-center">
                          <StatusBadge status={p.status} />
                        </td>
                        <td className="py-2.5 px-3 text-right font-mono text-[10px] text-gray-500">
                          {p.actual_high != null ? `${FMT(p.actual_high)} / ${FMT(p.actual_low)}` : '-- / --'}
                        </td>
                         <td className="py-2.5 px-1">
                        <button
                          onClick={(e) => { e.stopPropagation(); handleDeleteClick(p.id, p.symbol, p.predicted_date) }}
                          className="p-1 rounded hover:bg-red-50 dark:hover:bg-red-900/20 text-gray-300 hover:text-red-500 transition-colors"
                          title="Delete prediction"
                        >
                          <Trash2 className="w-3.5 h-3.5" />
                        </button>
                      </td>
                      <td className="py-2.5 px-2 text-gray-300 dark:text-gray-600">
                          {isExpanded ? <ChevronDown className="w-3.5 h-3.5" /> : <ChevronRight className="w-3.5 h-3.5" />}
                        </td>
                      </tr>

                      {/* Expanded details row */}
                      {isExpanded && (
                        <tr className="bg-gray-50/50 dark:bg-gray-800/40">
                          <td colSpan={12} className="px-3 py-3">
                            <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 text-[10px]">
                              {/* Technical Indicators */}
                              <div className="bg-white dark:bg-gray-800/60 rounded-lg p-2.5 border border-gray-100 dark:border-gray-700/30">
                                <h4 className="font-semibold text-gray-500 dark:text-gray-400 mb-1.5 uppercase tracking-wider">Indicators</h4>
                                <div className="space-y-1">
                                  <div className="flex justify-between"><span className="text-gray-400">RSI</span><span className={`font-mono font-medium ${p.rsi > 70 ? 'text-red-500' : p.rsi > 50 ? 'text-emerald-500' : 'text-gray-500'}`}>{p.rsi?.toFixed(1) ?? '--'}</span></div>
                                  <div className="flex justify-between"><span className="text-gray-400">ATR</span><span className="font-mono font-medium text-gray-700 dark:text-gray-200">{p.atr?.toFixed(1) ?? '--'}</span></div>
                                  <div className="flex justify-between"><span className="text-gray-400">ADX</span><span className={`font-mono font-medium ${p.adx > 25 ? 'text-emerald-500' : 'text-gray-500'}`}>{p.adx?.toFixed(1) ?? '--'}</span></div>
                                </div>
                              </div>

                              {/* Actual vs Predicted */}
                              <div className="bg-white dark:bg-gray-800/60 rounded-lg p-2.5 border border-gray-100 dark:border-gray-700/30">
                                <h4 className="font-semibold text-gray-500 dark:text-gray-400 mb-1.5 uppercase tracking-wider">Actual Data</h4>
                                <div className="space-y-1">
                                  <div className="flex justify-between"><span className="text-gray-400">Open</span><span className="font-mono font-medium text-gray-700 dark:text-gray-200">{FMT(p.actual_open)}</span></div>
                                  <div className="flex justify-between"><span className="text-gray-400">High</span><span className="font-mono font-medium text-gray-700 dark:text-gray-200">{FMT(p.actual_high)}</span></div>
                                  <div className="flex justify-between"><span className="text-gray-400">Low</span><span className="font-mono font-medium text-gray-700 dark:text-gray-200">{FMT(p.actual_low)}</span></div>
                                  <div className="flex justify-between"><span className="text-gray-400">Close</span><span className="font-mono font-medium text-gray-700 dark:text-gray-200">{FMT(p.actual_close)}</span></div>
                                </div>
                              </div>

                              {/* Prediction Notes */}
                              <div className="bg-white dark:bg-gray-800/60 rounded-lg p-2.5 border border-gray-100 dark:border-gray-700/30">
                                <h4 className="font-semibold text-gray-500 dark:text-gray-400 mb-1.5 uppercase tracking-wider">Details</h4>
                                <div className="space-y-1">
                                  <div className="flex justify-between"><span className="text-gray-400">Predicted H</span><span className="font-mono font-medium text-gray-700 dark:text-gray-200">{FMT(p.predicted_high)}</span></div>
                                  <div className="flex justify-between"><span className="text-gray-400">Predicted L</span><span className="font-mono font-medium text-gray-700 dark:text-gray-200">{FMT(p.predicted_low)}</span></div>
                                  <div className="flex justify-between"><span className="text-gray-400">Predicted C</span><span className="font-mono font-medium text-gray-700 dark:text-gray-200">{FMT(p.predicted_close)}</span></div>
                                  {p.result_details?.outcome && (
                                    <div className="mt-1.5 pt-1.5 border-t border-gray-100 dark:border-gray-700">
                                      <span className="text-gray-400 block">Outcome:</span>
                                      <span className="text-gray-600 dark:text-gray-300">{p.result_details.outcome}</span>
                                    </div>
                                  )}
                                </div>
                              </div>

                              {/* Notes full width */}
                              {p.notes && (
                                <div className="sm:col-span-3 bg-indigo-50/30 dark:bg-indigo-900/10 rounded-lg p-2.5 border border-indigo-100/30 dark:border-indigo-800/20">
                                  <h4 className="font-semibold text-indigo-500 dark:text-indigo-400 mb-1 uppercase tracking-wider">AI Analysis</h4>
                                  <p className="text-gray-600 dark:text-gray-300 leading-relaxed">{p.notes}</p>
                                </div>
                              )}
                            </div>
                          </td>
                        </tr>
                      )}
                    </React.Fragment>
                  )
                })}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Pagination */}
      {filtered.length > PAGE_SIZE && (
        <div className="flex items-center justify-between px-1">
          <span className="text-[10px] text-gray-400">
            Showing {(currentPage - 1) * PAGE_SIZE + 1}–{Math.min(currentPage * PAGE_SIZE, filtered.length)} of {filtered.length}
          </span>
          <div className="flex items-center gap-1">
            <button
              onClick={() => setCurrentPage(p => Math.max(1, p - 1))}
              disabled={currentPage === 1}
              className="px-2.5 py-1 text-[11px] font-medium rounded-lg bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 text-gray-600 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-gray-700 disabled:opacity-30 disabled:cursor-not-allowed transition-all"
            >
              Previous
            </button>
            {Array.from({ length: Math.min(totalPages, 5) }, (_, i) => {
              let pageNum
              if (totalPages <= 5) {
                pageNum = i + 1
              } else if (currentPage <= 3) {
                pageNum = i + 1
              } else if (currentPage >= totalPages - 2) {
                pageNum = totalPages - 4 + i
              } else {
                pageNum = currentPage - 2 + i
              }
              return (
                <button
                  key={pageNum}
                  onClick={() => setCurrentPage(pageNum)}
                  className={`w-7 h-7 text-[11px] font-medium rounded-lg transition-all ${
                    currentPage === pageNum
                      ? 'bg-primary text-primary-foreground shadow-sm'
                      : 'bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 text-gray-600 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-gray-700'
                  }`}
                >
                  {pageNum}
                </button>
              )
            })}
            <button
              onClick={() => setCurrentPage(p => Math.min(totalPages, p + 1))}
              disabled={currentPage === totalPages}
              className="px-2.5 py-1 text-[11px] font-medium rounded-lg bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 text-gray-600 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-gray-700 disabled:opacity-30 disabled:cursor-not-allowed transition-all"
            >
              Next
            </button>
          </div>
        </div>
      )}

      {/* Delete confirmation modal */}
      <ConfirmDeleteModal
        show={deleteTarget != null}
        onClose={handleDeleteCancel}
        onConfirm={handleDeleteConfirm}
        symbol={deleteTarget?.symbol}
        date={deleteTarget?.date}
      />
    </div>
  )
}
