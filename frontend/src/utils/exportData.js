/**
 * Utility functions for exporting data (CSV, etc.)
 */

/**
 * Export an array of objects as a CSV file and trigger download.
 * @param {Array<Object>} data - Array of row objects
 * @param {Array<{key: string, label: string}>} columns - Column definitions
 * @param {string} filename - Output filename (without extension)
 */
export function exportToCSV(data, columns, filename = 'export') {
  if (!data || data.length === 0) return

  const headerRow = columns.map(c => `"${c.label}"`).join(',')
  const dataRows = data.map(row =>
    columns.map(c => {
      const val = row[c.key]
      if (val === null || val === undefined) return ''
      const str = typeof val === 'object' ? JSON.stringify(val) : String(val)
      return `"${str.replace(/"/g, '""')}"`
    }).join(',')
  )

  const csv = [headerRow, ...dataRows].join('\n')
  const BOM = '﻿'
  const blob = new Blob([BOM + csv], { type: 'text/csv;charset=utf-8;' })
  const url = URL.createObjectURL(blob)

  const link = document.createElement('a')
  link.href = url
  link.download = `${filename}.csv`
  document.body.appendChild(link)
  link.click()
  document.body.removeChild(link)
  URL.revokeObjectURL(url)
}

/**
 * Get OHLC data formatted for CSV export.
 */
export function getOHLCExportColumns() {
  return [
    { key: 'Date', label: 'Date' },
    { key: 'Open', label: 'Open' },
    { key: 'High', label: 'High' },
    { key: 'Low', label: 'Low' },
    { key: 'Close', label: 'Close' },
    { key: 'Volume', label: 'Volume' },
  ]
}

/**
 * Get predictions data formatted for CSV export.
 */
export function getPredictionExportColumns() {
  return [
    { key: 'predicted_date', label: 'Date' },
    { key: 'symbol', label: 'Symbol' },
    { key: 'interval', label: 'Interval' },
    { key: 'direction', label: 'Direction' },
    { key: 'suggested_bias', label: 'Bias' },
    { key: 'confidence', label: 'Confidence' },
    { key: 'entry_zone', label: 'Entry' },
    { key: 'stop_loss', label: 'Stop Loss' },
    { key: 'target', label: 'Target' },
    { key: 'status', label: 'Status' },
    { key: 'actual_high', label: 'Actual High' },
    { key: 'actual_low', label: 'Actual Low' },
    { key: 'actual_close', label: 'Actual Close' },
  ]
}

/**
 * Request browser notification permission and send a notification.
 */
export function sendNotification(title, options = {}) {
  if (!('Notification' in window)) return
  if (Notification.permission === 'granted') {
    new Notification(title, {
      icon: '/vite.svg',
      ...options,
    })
  } else if (Notification.permission !== 'denied') {
    Notification.requestPermission().then(permission => {
      if (permission === 'granted') {
        new Notification(title, {
          icon: '/vite.svg',
          ...options,
        })
      }
    })
  }
}