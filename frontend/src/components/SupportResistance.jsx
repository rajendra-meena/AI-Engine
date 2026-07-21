import React, { useMemo } from 'react'
import { ArrowUp, ArrowDown, Minus, Target, Shield } from 'lucide-react'
import { calculatePivotPoints } from '../utils/technicalIndicators'

export default function SupportResistance({ data }) {
  const pivots = useMemo(() => {
    if (!data || data.length === 0) return null
    return calculatePivotPoints(data)
  }, [data])

  if (!pivots) {
    return (
      <div className="pivot-card">
        <div className="text-sm text-gray-400 dark:text-gray-500 text-center py-4">
          No data available for pivot calculation
        </div>
      </div>
    )
  }

  const levels = [
    { label: 'R3', value: pivots.r3, type: 'resistance' },
    { label: 'R2', value: pivots.r2, type: 'resistance' },
    { label: 'R1', value: pivots.r1, type: 'resistance' },
    { label: 'PIVOT', value: pivots.pivot, type: 'pivot' },
    { label: 'S1', value: pivots.s1, type: 'support' },
    { label: 'S2', value: pivots.s2, type: 'support' },
    { label: 'S3', value: pivots.s3, type: 'support' },
  ]

  return (
    <div className="pivot-card">
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-sm font-semibold text-gray-700 dark:text-gray-200">Pivot Points</h3>
        <div className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium ${
          pivots.isAbovePivot
            ? 'bg-emerald-50 text-emerald-600'
            : 'bg-red-50 text-red-600'
        }`}>
          {pivots.isAbovePivot ? (
            <ArrowUp className="w-3 h-3" />
          ) : (
            <ArrowDown className="w-3 h-3" />
          )}
          Price {pivots.isAbovePivot ? 'Above' : 'Below'} Pivot
        </div>
      </div>

      <div className="space-y-1">
        {levels.map((level) => {
          const isPivot = level.type === 'pivot'
          const isResistance = level.type === 'resistance'
          const isCurrentPrice = level.label === 'PIVOT'

          let levelClass = 'pivot-level-neutral'
          if (isPivot) {
            levelClass = pivots.isAbovePivot ? 'pivot-level-above' : 'pivot-level-below'
          } else if (isResistance) {
            levelClass = pivots.currentPrice < level.value ? 'pivot-level-above' : 'pivot-level-neutral'
          } else {
            levelClass = pivots.currentPrice > level.value ? 'pivot-level-below' : 'pivot-level-neutral'
          }

          return (
            <div key={level.label} className={`pivot-level ${levelClass}`}>
              <span className="font-semibold text-xs uppercase tracking-wider">{level.label}</span>
              <span className="font-mono text-sm font-medium">
                {level.value.toLocaleString('en-IN', { minimumFractionDigits: 2 })}
              </span>
            </div>
          )
        })}
      </div>
    </div>
  )
}
