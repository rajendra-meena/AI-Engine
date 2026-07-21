/**
 * Shared utility functions for MarketMind AI
 */

/**
 * Check if the Indian stock market is currently open.
 * Market hours: 9:15 AM to 3:30 PM IST, Monday-Friday.
 */
export function isMarketOpen() {
  const now = new Date()
  const utc = now.getTime() + now.getTimezoneOffset() * 60000
  const ist = new Date(utc + 5.5 * 3600000)
  const day = ist.getDay()
  const totalMin = ist.getHours() * 60 + ist.getMinutes()
  if (day === 0 || day === 6) return false
  return totalMin >= 555 && totalMin < 930
}

/**
 * Get the current trading day (today, or last Friday if today is weekend).
 */
export function getCurrentTradingDay() {
  const d = new Date()
  while (d.getDay() === 0 || d.getDay() === 6) d.setDate(d.getDate() - 1)
  return d.toISOString().split('T')[0]
}

/**
 * Get the next trading day (skipping weekends).
 */
export function getNextTradingDay() {
  const d = new Date()
  d.setDate(d.getDate() + 1)
  while (d.getDay() === 0 || d.getDay() === 6) d.setDate(d.getDate() + 1)
  return d.toISOString().split('T')[0]
}

/**
 * Format a number to en-IN locale with 2 decimal places.
 */
export function fmt(val) {
  return val != null ? val.toLocaleString('en-IN', { minimumFractionDigits: 2 }) : '--'
}

/**
 * Format a number to en-IN locale with 0 decimal places.
 */
export function fmtInt(val) {
  return val != null ? val.toLocaleString('en-IN', { minimumFractionDigits: 0 }) : '--'
}

/**
 * Calculate Risk-Reward ratio for a trade setup.
 * @param {number} entry - Entry price
 * @param {number} stopLoss - Stop loss price
 * @param {number} target1 - First target price
 * @returns {{ ratio: number, riskPts: number, rewardPts: number }}
 */
export function calculateRR(entry, stopLoss, target1) {
  const riskPts = Math.abs(entry - stopLoss)
  const rewardPts = Math.abs(target1 - entry)
  const ratio = riskPts > 0 ? (rewardPts / riskPts) : 0
  return { ratio: Math.round(ratio * 100) / 100, riskPts: Math.round(riskPts), rewardPts: Math.round(rewardPts) }
}

/**
 * Get the minutes elapsed since market open (9:15 AM IST).
 * @returns {number} Minutes from open (negative = pre-market)
 */
export function getMinutesFromMarketOpen() {
  const now = new Date()
  const utc = now.getTime() + now.getTimezoneOffset() * 60000
  const ist = new Date(utc + 5.5 * 3600000)
  return ist.getHours() * 60 + ist.getMinutes() - 555
}

/**
 * Determine the current market phase based on time since open.
 * @param {number} minutesFromOpen - From getMinutesFromMarketOpen()
 * @returns {'PreMarket' | 'Opening' | 'Mid' | 'Closing'}
 */
export function getMarketPhase(minutesFromOpen) {
  if (minutesFromOpen < 0) return 'PreMarket'
  if (minutesFromOpen <= 30) return 'Opening'
  if (minutesFromOpen >= 345) return 'Closing'
  return 'Mid'
}