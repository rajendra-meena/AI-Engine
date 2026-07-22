/**
 * indicatorEngine.ts
 * Client-side technical indicator computation from candle data.
 * Used for rendering full time-series overlays on the chart.
 * Backend API snapshots provide the latest confirmed values;
 * this engine computes full series for visual rendering.
 */

import type { Candle, OverlaySeriesPoint } from "@/types"

/* ── Helpers ── */

function sum(arr: number[]): number {
  return arr.reduce((a, b) => a + b, 0)
}

function avg(arr: number[]): number {
  return arr.length === 0 ? 0 : sum(arr) / arr.length
}

function stddev(arr: number[], mean: number): number {
  if (arr.length < 2) return 0
  const sqDiffs = arr.map((v) => (v - mean) ** 2)
  return Math.sqrt(sum(sqDiffs) / (arr.length - 1))
}

/* ── Moving Averages ── */

export function computeSMA(candles: Candle[], period: number, source: "close" | "high" | "low" | "hl2" | "hlc3" = "close"): (number | null)[] {
  const values = candles.map((c) => {
    if (source === "hl2") return (c.high + c.low) / 2
    if (source === "hlc3") return (c.high + c.low + c.close) / 3
    return c[source]
  })
  const result: (number | null)[] = []
  for (let i = 0; i < values.length; i++) {
    if (i < period - 1) {
      result.push(null)
    } else {
      result.push(avg(values.slice(i - period + 1, i + 1)))
    }
  }
  return result
}

export function computeEMA(candles: Candle[], period: number, source: "close" | "high" | "low" | "hl2" | "hlc3" = "close"): (number | null)[] {
  const values = candles.map((c) => {
    if (source === "hl2") return (c.high + c.low) / 2
    if (source === "hlc3") return (c.high + c.low + c.close) / 3
    return c[source]
  })
  const k = 2 / (period + 1)
  const result: (number | null)[] = []
  let emaPrev = 0
  for (let i = 0; i < values.length; i++) {
    if (i < period - 1) {
      result.push(null)
    } else if (i === period - 1) {
      emaPrev = avg(values.slice(0, period))
      result.push(emaPrev)
    } else {
      emaPrev = values[i] * k + emaPrev * (1 - k)
      result.push(emaPrev)
    }
  }
  return result
}

/* ── VWAP ── */

export function computeVWAP(candles: Candle[]): (number | null)[] {
  const result: (number | null)[] = []
  let cumPV = 0
  let cumV = 0
  for (let i = 0; i < candles.length; i++) {
    const c = candles[i]
    const typicalPrice = (c.high + c.low + c.close) / 3
    cumPV += typicalPrice * c.volume
    cumV += c.volume
    result.push(cumV > 0 ? cumPV / cumV : null)
  }
  return result
}

/* ── ATR ── */

export function computeATR(candles: Candle[], period = 14): (number | null)[] {
  if (candles.length < 2) return candles.map(() => null)
  const tr: number[] = []
  for (let i = 1; i < candles.length; i++) {
    const prev = candles[i - 1]
    const curr = candles[i]
    const trueRange = Math.max(
      curr.high - curr.low,
      Math.abs(curr.high - prev.close),
      Math.abs(curr.low - prev.close)
    )
    tr.push(trueRange)
  }
  // SMA of TR as initial ATR, then EMA
  const result: (number | null)[] = [null] // first candle has no TR
  let atr = avg(tr.slice(0, period))
  result.push(atr)
  const k = 2 / (period + 1)
  for (let i = 1; i < tr.length; i++) {
    if (i < period) {
      atr = avg(tr.slice(0, i + 1))
    } else {
      atr = tr[i] * k + atr * (1 - k)
    }
    result.push(atr)
  }
  return result
}

/* ── SuperTrend ── */

export interface SuperTrendResult {
  trend: Array<"up" | "down">
  supertrend: (number | null)[]
  close: number[]
}

export function computeSuperTrend(candles: Candle[], period = 10, multiplier = 3): SuperTrendResult {
  const atr = computeATR(candles, period)
  const hl2 = candles.map((c) => (c.high + c.low) / 2)
  const closes = candles.map((c) => c.close)

  const result: SuperTrendResult = {
    trend: [],
    supertrend: [],
    close: closes,
  }

  let prevUpper = 0
  let prevLower = 0
  let prevTrend: "up" | "down" = "up"

  for (let i = 0; i < candles.length; i++) {
    if (atr[i] === null || i === 0) {
      result.trend.push("up")
      result.supertrend.push(null)
      continue
    }

    const mid = hl2[i]
    const upper = mid + multiplier * atr[i]!
    const lower = mid - multiplier * atr[i]!

    let finalUpper = upper
    let finalLower = lower

    if (upper < prevUpper || closes[i - 1] > prevUpper) {
      finalUpper = upper
    } else {
      finalUpper = prevUpper
    }
    if (lower > prevLower || closes[i - 1] < prevLower) {
      finalLower = lower
    } else {
      finalLower = prevLower
    }

    let trend: "up" | "down"
    if (prevTrend === "up" && closes[i] < finalLower) {
      trend = "down"
    } else if (prevTrend === "down" && closes[i] > finalUpper) {
      trend = "up"
    } else {
      trend = prevTrend
    }

    result.trend.push(trend)
    result.supertrend.push(trend === "up" ? finalLower : finalUpper)
    prevUpper = finalUpper
    prevLower = finalLower
    prevTrend = trend
  }

  return result
}

/* ── Bollinger Bands ── */

export interface BollingerResult {
  upper: (number | null)[]
  middle: (number | null)[]
  lower: (number | null)[]
}

export function computeBollingerBands(candles: Candle[], period = 20, multiplier = 2): BollingerResult {
  const middle = computeSMA(candles, period)
  const values = candles.map((c) => c.close)
  const upper: (number | null)[] = []
  const lower: (number | null)[] = []

  for (let i = 0; i < values.length; i++) {
    if (middle[i] === null) {
      upper.push(null)
      lower.push(null)
    } else {
      const slice = values.slice(Math.max(0, i - period + 1), i + 1)
      const sd = stddev(slice, middle[i]!)
      upper.push(middle[i]! + multiplier * sd)
      lower.push(middle[i]! - multiplier * sd)
    }
  }

  return { upper, middle, lower }
}

/* ── RSI ── */

export function computeRSI(candles: Candle[], period = 14): (number | null)[] {
  if (candles.length < 2) return candles.map(() => null)
  const changes: number[] = []
  for (let i = 1; i < candles.length; i++) {
    changes.push(candles[i].close - candles[i - 1].close)
  }

  const result: (number | null)[] = [null]
  let avgGain = 0
  let avgLoss = 0

  for (let i = 0; i < changes.length; i++) {
    const gain = changes[i] > 0 ? changes[i] : 0
    const loss = changes[i] < 0 ? -changes[i] : 0

    if (i < period) {
      avgGain += gain / period
      avgLoss += loss / period
      if (i === period - 1) {
        const rs = avgLoss === 0 ? 100 : avgGain / avgLoss
        result.push(100 - 100 / (1 + rs))
      } else {
        result.push(null)
      }
    } else {
      avgGain = (avgGain * (period - 1) + gain) / period
      avgLoss = (avgLoss * (period - 1) + loss) / period
      const rs = avgLoss === 0 ? 100 : avgGain / avgLoss
      result.push(100 - 100 / (1 + rs))
    }
  }

  return result
}

/* ── Convert typed arrays to OverlaySeriesPoint[] ── */

export function toSeriesPoints(candles: Candle[], values: (number | null)[]): OverlaySeriesPoint[] {
  const points: OverlaySeriesPoint[] = []
  for (let i = 0; i < candles.length; i++) {
    if (values[i] !== null) {
      points.push({ time: candles[i].time, value: values[i]! })
    }
  }
  return points
}

export function toSeriesPointsWithKey(candles: Candle[], values: (number | null)[], timeKey: string): OverlaySeriesPoint[] {
  const points: OverlaySeriesPoint[] = []
  for (let i = 0; i < candles.length; i++) {
    if (values[i] !== null) {
      points.push({ time: (candles[i] as unknown as Record<string, string>)[timeKey] || candles[i].time, value: values[i]! })
    }
  }
  return points
}
