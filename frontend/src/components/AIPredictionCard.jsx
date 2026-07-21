import React, { useMemo } from 'react'
import { TrendingUp, TrendingDown, Brain, Target, ShieldAlert, Activity, AlertTriangle } from 'lucide-react'
import { generateAIPrediction } from '../utils/technicalIndicators'

export default function AIPredictionCard({ data, windowLabel, prediction: externalPrediction }) {
  const prediction = useMemo(() => {
    // Use external prediction if provided (avoids redundant computation)
    if (externalPrediction) return externalPrediction
    if (!data || data.length < 3) return null
    return generateAIPrediction(data, windowLabel)
  }, [data, windowLabel, externalPrediction])

  if (!prediction) {
    return (
      <div className="ai-card">
        <div className="flex items-center gap-3 mb-4">
          <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-indigo-500 to-purple-600 flex items-center justify-center">
            <Brain className="w-5 h-5 text-white" />
          </div>
          <div>
            <h3 className="text-sm font-semibold text-gray-700 dark:text-gray-200">AI Prediction Engine</h3>
            <p className="text-xs text-gray-400 dark:text-gray-500">Technical Analysis Engine</p>
          </div>
        </div>
        <div className="text-sm text-gray-400 dark:text-gray-500 text-center py-6">
          Need at least 3 days of data for analysis.
        </div>
      </div>
    )
  }

  const isBullish = prediction.direction === 'BULLISH'
  const isBearish = prediction.direction === 'BEARISH'
  const fmt = (val) => val != null ? val.toLocaleString('en-IN', { minimumFractionDigits: 2 }) : '--'

  return (
    <div className="ai-card">
      <div className="flex items-center gap-3 mb-4">
        <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-indigo-500 to-purple-600 flex items-center justify-center shadow-lg shadow-indigo-200 dark:shadow-indigo-900/30">
          <Brain className="w-5 h-5 text-white" />
        </div>
        <div>
          <h3 className="text-sm font-semibold text-gray-700 dark:text-gray-200">AI Prediction Engine</h3>
          <p className="text-xs text-gray-400 dark:text-gray-500">{windowLabel || 'Custom'} &middot; {prediction.riskLevel} Risk</p>
        </div>
      </div>

      {/* Trend & Confidence */}
      <div className="flex items-center justify-between mb-4">
        <div className={`inline-flex items-center gap-1.5 px-3 py-1.5 rounded-xl text-sm font-bold shadow-sm ${
          isBullish ? 'bg-gradient-to-r from-emerald-500 to-green-600 text-white shadow-emerald-200 dark:shadow-emerald-900/30' :
          isBearish ? 'bg-gradient-to-r from-red-500 to-rose-600 text-white shadow-red-200 dark:shadow-red-900/30' :
          'bg-gradient-to-r from-gray-400 to-gray-500 text-white shadow-gray-200'
        }`}>
          {isBullish ? <TrendingUp className="w-4 h-4" /> : isBearish ? <TrendingDown className="w-4 h-4" /> : <Activity className="w-4 h-4" />}
          {prediction.trendLabel}
        </div>
        <div className="flex items-center gap-2">
          <span className="text-[10px] text-gray-400 dark:text-gray-500 font-medium">Confidence</span>
          <div className="relative w-16 h-2 bg-gray-100 dark:bg-gray-700 rounded-full overflow-hidden">
            <div className={`absolute inset-y-0 left-0 rounded-full transition-all duration-500 ${
              prediction.confidence >= 70 ? 'bg-emerald-500' : prediction.confidence >= 50 ? 'bg-amber-500' : 'bg-red-500'
            }`} style={{ width: `${prediction.confidence}%` }} />
          </div>
          <span className="text-xs font-bold text-gray-700 dark:text-gray-200">{prediction.confidence}%</span>
        </div>
      </div>

      {/* Strength & Momentum */}
      <div className="grid grid-cols-2 gap-2 mb-4">
        <div className="bg-gray-50 dark:bg-gray-700/40 rounded-lg p-2.5">
          <div className="text-[9px] text-gray-400 dark:text-gray-500 uppercase tracking-wider">Strength</div>
          <div className={`text-xs font-bold mt-0.5 ${prediction.trendStrength === 'Strong' ? 'text-emerald-600 dark:text-emerald-400' : prediction.trendStrength === 'Moderate' ? 'text-amber-600 dark:text-amber-400' : 'text-gray-500'}`}>{prediction.trendStrength}</div>
        </div>
        <div className="bg-gray-50 dark:bg-gray-700/40 rounded-lg p-2.5">
          <div className="text-[9px] text-gray-400 dark:text-gray-500 uppercase tracking-wider">Momentum</div>
          <div className={`text-xs font-bold mt-0.5 ${prediction.momentum === 'Increasing' ? 'text-emerald-600 dark:text-emerald-400' : prediction.momentum === 'Flat' ? 'text-gray-500 dark:text-gray-400' : 'text-red-600 dark:text-red-400'}`}>{prediction.momentum}</div>
        </div>
      </div>

      {/* Breakout / Breakdown */}
      <div className="grid grid-cols-2 gap-2 mb-4">
        <div className="bg-emerald-50/50 dark:bg-emerald-900/20 rounded-lg p-2.5 border border-emerald-100/50 dark:border-emerald-800/30">
          <div className="text-[9px] text-emerald-600 dark:text-emerald-400 font-medium">Breakout ↑</div>
          <div className="text-base font-bold text-emerald-700 dark:text-emerald-300">{prediction.breakoutProbability}%</div>
        </div>
        <div className="bg-red-50/50 dark:bg-red-900/20 rounded-lg p-2.5 border border-red-100/50 dark:border-red-800/30">
          <div className="text-[9px] text-red-600 dark:text-red-400 font-medium">Breakdown ↓</div>
          <div className="text-base font-bold text-red-700 dark:text-red-300">{prediction.breakdownProbability}%</div>
        </div>
      </div>

      {/* Bias / Entry / SL / Target */}
      <div className="grid grid-cols-2 gap-2 mb-4">
        <div className={`rounded-lg p-3 border ${
          prediction.suggestedBias === 'Buy' ? 'bg-emerald-50/70 dark:bg-emerald-900/20 border-emerald-200/70 dark:border-emerald-800/30 ring-1 ring-emerald-400/30' :
          prediction.suggestedBias === 'Sell' ? 'bg-red-50/70 dark:bg-red-900/20 border-red-200/70 dark:border-red-800/30 ring-1 ring-red-400/30' :
          'bg-gray-50/50 dark:bg-gray-700/20 border-gray-200/50 dark:border-gray-700/30'
        }`}>
          <div className="text-[9px] text-gray-400 dark:text-gray-500 uppercase tracking-wider">Bias</div>
          <div className={`text-sm font-bold mt-0.5 ${prediction.suggestedBias === 'Buy' ? 'text-emerald-600 dark:text-emerald-400' : prediction.suggestedBias === 'Sell' ? 'text-red-600 dark:text-red-400' : 'text-amber-600 dark:text-amber-400'}`}>{prediction.suggestedBias}</div>
        </div>
        <div className="bg-gray-50 dark:bg-gray-700/40 rounded-lg p-3 border border-gray-100 dark:border-gray-700/30">
          <div className="text-[9px] text-gray-400 dark:text-gray-500 uppercase tracking-wider">Entry Zone</div>
          <div className="text-sm font-bold text-gray-700 dark:text-gray-200 mt-0.5 font-mono">{fmt(prediction.suggestedEntryZone)}</div>
        </div>
        <div className="bg-orange-50/50 dark:bg-orange-900/20 rounded-lg p-3 border border-orange-100/50 dark:border-orange-800/30">
          <div className="flex items-center gap-1 text-[9px] text-orange-600 dark:text-orange-400 font-medium"><ShieldAlert className="w-3 h-3" /> SL</div>
          <div className="text-sm font-bold text-orange-700 dark:text-orange-300 mt-0.5 font-mono">{fmt(prediction.suggestedStopLoss)}</div>
        </div>
        <div className="bg-violet-50/50 dark:bg-violet-900/20 rounded-lg p-3 border border-violet-100/50 dark:border-violet-800/30">
          <div className="flex items-center gap-1 text-[9px] text-violet-600 dark:text-violet-400 font-medium"><Target className="w-3 h-3" /> Target</div>
          <div className="text-sm font-bold text-violet-700 dark:text-violet-300 mt-0.5 font-mono">{fmt(prediction.suggestedTarget)}</div>
        </div>
      </div>

      {/* Support / Resistance */}
      <div className="grid grid-cols-2 gap-2 mb-4">
        <div className="bg-green-50/50 dark:bg-green-900/20 rounded-lg p-2.5 border border-green-100/50 dark:border-green-800/30">
          <div className="text-[9px] text-green-600 dark:text-green-400 font-medium mb-1">Support</div>
          {(prediction.supportLevels || []).map((s, i) => (
            <div key={i} className="text-[10px] font-mono text-green-700 dark:text-green-300">S{i + 1}: {fmt(s)}</div>
          ))}
        </div>
        <div className="bg-red-50/50 dark:bg-red-900/20 rounded-lg p-2.5 border border-red-100/50 dark:border-red-800/30">
          <div className="text-[9px] text-red-600 dark:text-red-400 font-medium mb-1">Resistance</div>
          {(prediction.resistanceLevels || []).map((r, i) => (
            <div key={i} className="text-[10px] font-mono text-red-700 dark:text-red-300">R{i + 1}: {fmt(r)}</div>
          ))}
        </div>
      </div>

      {/* Fibonacci Retracement Levels */}
      {prediction.fibonacciLevels && (
        <div className="mb-4">
          <div className="text-[9px] text-gray-400 dark:text-gray-500 uppercase tracking-wider mb-1.5">Fibonacci Retracement</div>
          <div className="grid grid-cols-3 sm:grid-cols-5 gap-1">
            {[
              { key: 'fib0236', label: '23.6%' },
              { key: 'fib0382', label: '38.2%' },
              { key: 'fib0500', label: '50.0%' },
              { key: 'fib0618', label: '61.8%' },
              { key: 'fib0786', label: '78.6%' },
            ].map(f => {
              const val = prediction.fibonacciLevels?.[f.key]
              return (
                <div key={f.key} className="bg-gray-50 dark:bg-gray-700/40 rounded-lg p-1.5 text-center">
                  <div className="text-[7px] text-gray-400 uppercase tracking-wider">{f.label}</div>
                  <div className="text-[10px] font-mono font-bold text-indigo-600 dark:text-indigo-400 mt-0.5">{val != null ? val.toLocaleString('en-IN', { minimumFractionDigits: 2 }) : '--'}</div>
                </div>
              )
            })}
          </div>
        </div>
      )}

      {/* Technical Snapshot */}
      <div className="grid grid-cols-3 gap-2 mb-4">
        <div className="bg-gray-50 dark:bg-gray-700/40 rounded-lg p-2 text-center">
          <div className="text-[8px] text-gray-400 uppercase tracking-wider">RSI</div>
          <div className={`text-xs font-bold mt-0.5 ${prediction.rsi > 70 ? 'text-red-600' : prediction.rsi > 50 ? 'text-emerald-600' : 'text-gray-600 dark:text-gray-400'}`}>{prediction.rsi?.toFixed(1)}</div>
        </div>
        <div className="bg-gray-50 dark:bg-gray-700/40 rounded-lg p-2 text-center">
          <div className="text-[8px] text-gray-400 uppercase tracking-wider">ATR</div>
          <div className="text-xs font-bold text-gray-700 dark:text-gray-200 mt-0.5">{prediction.atr?.toFixed(1)}</div>
        </div>
        <div className="bg-gray-50 dark:bg-gray-700/40 rounded-lg p-2 text-center">
          <div className="text-[8px] text-gray-400 uppercase tracking-wider">ADX</div>
          <div className={`text-xs font-bold mt-0.5 ${prediction.adx > 25 ? 'text-emerald-600' : 'text-gray-600 dark:text-gray-400'}`}>{prediction.adx?.toFixed(1)}</div>
        </div>
      </div>

      {/* Explanation */}
      <div className="bg-gradient-to-r from-indigo-50/50 to-purple-50/50 dark:from-indigo-900/20 dark:to-purple-900/20 rounded-lg p-3 border border-indigo-100/30 dark:border-indigo-800/30">
        <div className="flex items-start gap-2">
          <AlertTriangle className="w-3.5 h-3.5 text-indigo-500 mt-0.5 shrink-0" />
          <div>
            <p className="text-[10px] font-medium text-indigo-600 dark:text-indigo-400 mb-0.5">Why this prediction?</p>
            <p className="text-[10px] text-gray-600 dark:text-gray-300 leading-relaxed">{prediction.notes}</p>
          </div>
        </div>
      </div>
    </div>
  )
}
