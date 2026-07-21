import React from 'react'
import { TrendingUp, TrendingDown } from 'lucide-react'

export default function StatsCard({ label, value, change, prefix = '', suffix = '' }) {
  const isPositive = change > 0
  const isNegative = change < 0

  const formatValue = (val) => {
    if (val === null || val === undefined) return '--'
    const num = typeof val === 'string' ? parseFloat(val) : val
    if (isNaN(num)) return '--'
    return new Intl.NumberFormat('en-IN', {
      minimumFractionDigits: 2,
      maximumFractionDigits: 2,
    }).format(num)
  }

  return (
    <div className="stats-card group">
      <div className="flex items-center justify-between mb-2">
        <span className="text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
          {label}
        </span>
        {change !== null && change !== undefined && change !== 0 && (
          <span
            className={`inline-flex items-center gap-1 text-xs font-semibold px-2 py-0.5 rounded-full ${
              change > 0
                ? 'bg-emerald-50 dark:bg-emerald-900/30 text-emerald-600 dark:text-emerald-400'
                : 'bg-red-50 dark:bg-red-900/30 text-red-600 dark:text-red-400'
            }`}
          >
            {change > 0 ? <TrendingUp className="w-3 h-3" /> : <TrendingDown className="w-3 h-3" />}
            {change > 0 ? '+' : ''}{change?.toFixed(2)}%
          </span>
        )}
      </div>
      <div className="text-xl sm:text-2xl font-bold text-gray-900 dark:text-gray-100 tracking-tight">
        {formatValue(value)}
        {suffix && <span className="text-sm font-normal text-gray-400 dark:text-gray-500 ml-1">{suffix}</span>}
      </div>
    </div>
  )
}
