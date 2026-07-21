/**
 * Institutional Intraday Trading Engine
 *
 * Complete market analysis before any trade:
 * - Multi-timeframe structure (swing highs/lows, trend, Dow Theory)
 * - Price action (breakout, engulfing, pin bars, inside/outside bars, momentum)
 * - Supply & demand zones from real swing points
 * - Volume confirmation / divergence
 * - Volatility context (ATR, candle range)
 * - Momentum suite (RSI, EMA, VWAP, MACD)
 * - Logical SL beyond nearest swing / zone — never random
 * - Multiple targets with price-action reasoning
 * - Confidence score based on confluence
 * - Strict 1:2 minimum RR — reject if criteria not met
 */

// ── Constants ──

const LABEL_MAP = {
  ORB_BREAKOUT_BULL:    'ORB Breakout ↑',
  ORB_BREAKDOWN_BEAR:   'ORB Breakdown ↓',
  PREV_HIGH_BREAKOUT:   'Prev Day High Breakout ↑',
  PREV_LOW_BREAKDOWN:   'Prev Day Low Breakdown ↓',
  WEEKLY_HIGH_BREAKOUT: 'Weekly High Breakout ↑',
  WEEKLY_LOW_BREAKDOWN: 'Weekly Low Breakdown ↓',
  VWAP_REJECTION_BULL:  'VWAP Rejection ↑',
  VWAP_REJECTION_BEAR:  'VWAP Rejection ↓',
  BULLISH_ENGULFING:    'Bullish Engulfing',
  BEARISH_ENGULFING:    'Bearish Engulfing',
  TREND_BREAK_BULL:     'Trend Break Bullish',
  TREND_BREAK_BEAR:     'Trend Break Bearish',
  SUPPLY_ZONE_BREAK:    'Supply Zone Break',
  DEMAND_ZONE_BREAK:    'Demand Zone Break',
}

// ─────────────────────────────────────────────
// Utility Helpers
// ─────────────────────────────────────────────

function roundTo(v, d = 2) { const m = 10 ** d; return Math.round(v * m) / m }

function getTodayCandles(candles) {
  const today = new Date().toISOString().split('T')[0]
  return candles.filter(c => c.time && c.time.startsWith(today)).sort((a, b) => new Date(a.time) - new Date(b.time))
}

/**
 * Aggregate candles to simulate a higher timeframe.
 * E.g. 3m data → 15m candles by grouping 5 at a time.
 */
function aggregateCandles(candles, groupSize) {
  if (!candles || candles.length === 0) return []
  const result = []
  for (let i = 0; i < candles.length; i += groupSize) {
    const slice = candles.slice(i, i + groupSize)
    const first = slice[0]
    const last = slice[slice.length - 1]
    result.push({
      time: first.time,
      open: first.open,
      high: Math.max(...slice.map(c => c.high)),
      low: Math.min(...slice.map(c => c.low)),
      close: last.close,
      volume: slice.reduce((s, c) => s + (c.volume || 0), 0),
    })
  }
  return result
}

/**
 * Simple EMA calculation.
 */
function calculateEMA(values, period) {
  if (!values || values.length === 0) return []
  const k = 2 / (period + 1)
  const result = []
  // SMA seed
  let sum = 0
  for (let i = 0; i < Math.min(period, values.length); i++) sum += values[i]
  result.push(sum / Math.min(period, values.length))
  for (let i = Math.min(period, values.length); i < values.length; i++) {
    result.push((values[i] - result[result.length - 1]) * k + result[result.length - 1])
  }
  return result
}

/**
 * RSI calculation.
 */
function calculateRSI(closes, period = 14) {
  if (closes.length < period + 1) return null
  const changes = []
  for (let i = 1; i < closes.length; i++) changes.push(closes[i] - closes[i - 1])
  const gains = changes.map(c => c > 0 ? c : 0)
  const losses = changes.map(c => c < 0 ? -c : 0)
  let avgGain = gains.slice(0, period).reduce((a, b) => a + b, 0) / period
  let avgLoss = losses.slice(0, period).reduce((a, b) => a + b, 0) / period
  for (let i = period; i < changes.length; i++) {
    avgGain = (avgGain * (period - 1) + gains[i]) / period
    avgLoss = (avgLoss * (period - 1) + losses[i]) / period
  }
  if (avgLoss === 0) return 100
  const rs = avgGain / avgLoss
  return 100 - 100 / (1 + rs)
}

/**
 * Simple MACD: returns {macd, signal, histogram}.
 */
function calculateMACD(closes) {
  const ema12 = calculateEMA(closes, 12)
  const ema26 = calculateEMA(closes, 26)
  const macdLine = []
  const len = Math.min(ema12.length, ema26.length)
  for (let i = 0; i < len; i++) {
    if (ema12[i] != null && ema26[i] != null) macdLine.push(ema12[i] - ema26[i])
  }
  const signal = calculateEMA(macdLine, 9)
  const hist = []
  for (let i = 0; i < macdLine.length; i++) {
    hist.push(macdLine[i] - (signal[i] || 0))
  }
  return {
    macd: macdLine[macdLine.length - 1] || 0,
    signal: signal[signal.length - 1] || 0,
    histogram: hist[hist.length - 1] || 0,
  }
}

// ─────────────────────────────────────────────
// 1. Market Structure — Swing Highs / Lows
// ─────────────────────────────────────────────

/**
 * Zigzag-style swing detection.
 * Returns arrays of {index, price, type, time}.
 */
function findSwingPoints(candles) {
  if (!candles || candles.length < 5) return { highs: [], lows: [] }

  const highs = []
  const lows = []

  for (let i = 2; i < candles.length - 2; i++) {
    const c = candles[i]
    const left1 = candles[i - 1]
    const left2 = candles[i - 2]
    const right1 = candles[i + 1]
    const right2 = candles[i + 2]

    // Swing high: 2 lower highs on each side
    if (c.high > left1.high && c.high > left2.high &&
        c.high > right1.high && c.high > right2.high) {
      highs.push({ index: i, price: c.high, time: c.time })
    }

    // Swing low: 2 lower lows on each side
    if (c.low < left1.low && c.low < left2.low &&
        c.low < right1.low && c.low < right2.low) {
      lows.push({ index: i, price: c.low, time: c.time })
    }
  }

  return { highs, lows }
}

/**
 * Determine market direction using Higher High/Higher Low / Dow Theory.
 */
function analyzeMarketDirection(swingHighs, swingLows) {
  if (swingHighs.length < 3 || swingLows.length < 3) {
    return { direction: 'RANGING', strength: 'WEAK', description: 'Insufficient swing data' }
  }

  const recentSH = swingHighs.slice(-3)
  const recentSL = swingLows.slice(-3)

  const hh = recentSH[2].price > recentSH[1].price && recentSH[1].price > recentSH[0].price
  const hl = recentSL[2].price > recentSL[1].price && recentSL[1].price > recentSL[0].price
  const lh = recentSH[2].price < recentSH[1].price && recentSH[1].price < recentSH[0].price
  const ll = recentSL[2].price < recentSL[1].price && recentSL[1].price < recentSL[0].price

  if (hh && hl) {
    return {
      direction: 'UPTREND',
      strength: recentSH[2].price - recentSH[0].price > (recentSH[0].price * 0.001) ? 'STRONG' : 'MODERATE',
      description: 'Higher Highs & Higher Lows — bullish Dow Theory confirmation',
    }
  }
  if (lh && ll) {
    return {
      direction: 'DOWNTREND',
      strength: recentSH[0].price - recentSH[2].price > (recentSH[0].price * 0.001) ? 'STRONG' : 'MODERATE',
      description: 'Lower Highs & Lower Lows — bearish Dow Theory confirmation',
    }
  }
  if (hh && !hl) {
    return {
      direction: 'PULLBACK_BULLISH',
      strength: 'MODERATE',
      description: 'Higher highs but failing to make higher lows — bullish momentum slowing',
    }
  }
  if (lh && !ll) {
    return {
      direction: 'PULLBACK_BEARISH',
      strength: 'MODERATE',
      description: 'Lower highs but failing to make lower lows — bearish momentum slowing',
    }
  }
  return {
    direction: 'RANGING',
    strength: 'WEAK',
    description: 'No clear HH/HL/LH/LL pattern — market consolidating',
  }
}

/**
 * Find nearest swing high above a price, and lowest swing low below price.
 */
function findNearestSwing(candles, price) {
  const { highs, lows } = findSwingPoints(candles)

  let nearestHighAbove = null
  let nearestLowBelow = null
  let distHigh = Infinity
  let distLow = Infinity

  for (const sh of highs) {
    if (sh.price > price && sh.price - price < distHigh) {
      distHigh = sh.price - price
      nearestHighAbove = sh.price
    }
  }
  for (const sl of lows) {
    if (sl.price < price && price - sl.price < distLow) {
      distLow = price - sl.price
      nearestLowBelow = sl.price
    }
  }

  // Fall back to simple candle lows/highs if no clean swing found
  if (nearestLowBelow == null) {
    for (const c of candles) {
      if (c.low < price && price - c.low < distLow) {
        distLow = price - c.low
        nearestLowBelow = c.low
      }
    }
  }
  if (nearestHighAbove == null) {
    for (const c of candles) {
      if (c.high > price && c.high - price < distHigh) {
        distHigh = c.high - price
        nearestHighAbove = c.high
      }
    }
  }

  return { swingHighAbove: nearestHighAbove, swingLowBelow: nearestLowBelow }
}

// ─────────────────────────────────────────────
// 2. Trend Detection
// ─────────────────────────────────────────────

function detectTrendV2(candles) {
  if (candles.length < 10) return { trend: 'RANGING', strength: 'WEAK', ema9: null, ema21: null }

  const closes = candles.map(c => c.close)
  const ema9 = calculateEMA(closes, 9)
  const ema21 = calculateEMA(closes, 21)
  const lastEma9 = ema9[ema9.length - 1]
  const lastEma21 = ema21[ema21.length - 1]
  const prevEma9 = ema9.length > 1 ? ema9[ema9.length - 2] : lastEma9
  const lastClose = closes[closes.length - 1]

  let trend = 'RANGING'
  let strength = 'WEAK'

  if (lastClose > lastEma9 && lastEma9 > lastEma21) {
    trend = 'UPTREND'
    strength = lastEma9 > prevEma9 ? 'STRONG' : 'WEAKENING'
  } else if (lastClose < lastEma9 && lastEma9 < lastEma21) {
    trend = 'DOWNTREND'
    strength = lastEma9 < prevEma9 ? 'STRONG' : 'WEAKENING'
  } else if (lastClose > lastEma9 && lastEma9 < lastEma21) {
    trend = 'TRANSITION_BULLISH'
    strength = 'MODERATE'
  } else if (lastClose < lastEma9 && lastEma9 > lastEma21) {
    trend = 'TRANSITION_BEARISH'
    strength = 'MODERATE'
  }

  return { trend, strength, ema9: lastEma9, ema21: lastEma21 }
}

// ─────────────────────────────────────────────
// 3. Price Action Patterns
// ─────────────────────────────────────────────

function analyzePriceAction(candles) {
  if (!candles || candles.length < 3) return { patterns: [], signals: [] }

  const last = candles[candles.length - 1]
  const prev = candles[candles.length - 2]
  const prev2 = candles.length >= 3 ? candles[candles.length - 3] : null
  const signals = []
  const patterns = []

  if (!last || !prev) return { patterns, signals }

  const range = last.high - last.low
  const body = Math.abs(last.close - last.open)
  const upperWick = last.high - Math.max(last.close, last.open)
  const lowerWick = Math.min(last.close, last.open) - last.low
  const bodyPercent = range > 0 ? (body / range) * 100 : 0
  const prevBody = Math.abs(prev.close - prev.open)
  const prevRange = prev.high - prev.low

  // Momentum candle (large body, small wicks)
  if (bodyPercent > 70 && range > prevRange * 1.3) {
    const direction = last.close > last.open ? 'BULLISH' : 'BEARISH'
    signals.push({ type: 'MOMENTUM_CANDLE', direction, strength: 'STRONG' })
    patterns.push(`🔥 ${direction} Momentum Candle (${bodyPercent.toFixed(0)}% body)`)

    // Strong bullish/bearish
    if (bodyPercent > 85) {
      signals.push({ type: direction === 'BULLISH' ? 'STRONG_BULLISH' : 'STRONG_BEARISH', direction, strength: 'VERY_STRONG' })
      patterns.push(`💪 ${direction} candle — ${bodyPercent.toFixed(0)}% body, small wicks`)
    }
  }

  // Doji
  if (range > 0 && body < range * 0.1) {
    signals.push({ type: 'DOJI', direction: 'NEUTRAL', strength: 'MODERATE' })
    patterns.push('✧ Doji — indecision / potential reversal')
  }

  // Pin bar / hammer
  if (range > 0 && (lowerWick > body * 2.5 || upperWick > body * 2.5)) {
    const isBullishPin = lowerWick > body * 2.5 && last.close >= last.open
    const isBearishPin = upperWick > body * 2.5 && last.close <= last.open
    if (isBullishPin) {
      signals.push({ type: 'PIN_BAR_BULLISH', direction: 'BULLISH', strength: 'MODERATE' })
      patterns.push(`📌 Bullish Pin Bar — rejection at ${last.low.toFixed(0)}`)
    } else if (isBearishPin) {
      signals.push({ type: 'PIN_BAR_BEARISH', direction: 'BEARISH', strength: 'MODERATE' })
      patterns.push(`📌 Bearish Pin Bar — rejection at ${last.high.toFixed(0)}`)
    }
  }

  // Engulfing
  if (prev && prevRange > 0) {
    if (last.close > last.open && last.open < prev.low && last.close > prev.high) {
      signals.push({ type: 'BULLISH_ENGULFING', direction: 'BULLISH', strength: 'STRONG' })
      patterns.push(`🟢 Bullish Engulfing — engulfed previous ${prevRange.toFixed(0)} pt range`)
    }
    if (last.close < last.open && last.open > prev.high && last.close < prev.low) {
      signals.push({ type: 'BEARISH_ENGULFING', direction: 'BEARISH', strength: 'STRONG' })
      patterns.push(`🔴 Bearish Engulfing — engulfed previous ${prevRange.toFixed(0)} pt range`)
    }
  }

  // Inside bar
  if (prev && last.high <= prev.high && last.low >= prev.low) {
    signals.push({ type: 'INSIDE_BAR', direction: 'NEUTRAL', strength: 'WEAK' })
    patterns.push('▤ Inside Bar — contraction, awaiting breakout')
  }

  // Outside bar
  if (prev && last.high > prev.high && last.low < prev.low) {
    const direction = last.close > last.open ? 'BULLISH' : 'BEARISH'
    signals.push({ type: 'OUTSIDE_BAR', direction, strength: 'MODERATE' })
    patterns.push(`▣ Outside Bar — ${direction.toLowerCase()} expansion`)
  }

  // Marubozu
  if (bodyPercent > 95 && (upperWick < range * 0.02 || lowerWick < range * 0.02)) {
    const direction = last.close > last.open ? 'BULLISH' : 'BEARISH'
    signals.push({ type: 'MARUBOZU', direction, strength: 'STRONG' })
    patterns.push(`▬ Marubozu — ${direction.toLowerCase()} conviction, no wick`)
  }

  // Breakout / breakdown from range
  if (prev && prev2) {
    const recentRange = Math.max(prev.high, prev2.high) - Math.min(prev.low, prev2.low)
    if (last.close > Math.max(prev.high, prev2.high) && last.high > Math.max(prev.high, prev2.high)) {
      signals.push({ type: 'BREAKOUT', direction: 'BULLISH', strength: recentRange > 0 ? 'STRONG' : 'MODERATE' })
      patterns.push(`🚀 Breakout above ${Math.max(prev.high, prev2.high).toFixed(0)} range high`)
    }
    if (last.close < Math.min(prev.low, prev2.low) && last.low < Math.min(prev.low, prev2.low)) {
      signals.push({ type: 'BREAKDOWN', direction: 'BEARISH', strength: recentRange > 0 ? 'STRONG' : 'MODERATE' })
      patterns.push(`💥 Breakdown below ${Math.min(prev.low, prev2.low).toFixed(0)} range low`)
    }
  }

  // Pullback / retest detection
  if (signals.some(s => s.type === 'BREAKOUT') && signals.some(s => s.type === 'INSIDE_BAR')) {
    patterns.push('↻ Pullback / Retest after breakout — watch for continuation')
  }

  return { patterns, signals }
}

// ─────────────────────────────────────────────
// 4. Support & Resistance
// ─────────────────────────────────────────────

function buildSupportResistance(candles, dailyRefs, pivots) {
  const levels = []

  // Daily reference levels
  if (dailyRefs) {
    levels.push({ price: dailyRefs.prevDayHigh, type: 'R', label: 'Prev Day High', strength: 'STRONG' })
    levels.push({ price: dailyRefs.prevDayLow, type: 'S', label: 'Prev Day Low', strength: 'STRONG' })
    levels.push({ price: dailyRefs.weeklyHigh, type: 'R', label: 'Weekly High', strength: 'MAJOR' })
    levels.push({ price: dailyRefs.weeklyLow, type: 'S', label: 'Weekly Low', strength: 'MAJOR' })
    levels.push({ price: dailyRefs.prevDayClose, type: 'S/R', label: 'Prev Day Close', strength: 'MODERATE' })
    levels.push({ price: dailyRefs.prevDayOpen, type: 'S/R', label: 'Prev Day Open', strength: 'MODERATE' })
  }

  // Pivot levels
  if (pivots) {
    for (const [key, label] of [['r3', 'R3'], ['r2', 'R2'], ['r1', 'R1'], ['pivot', 'Pivot'], ['s1', 'S1'], ['s2', 'S2'], ['s3', 'S3']]) {
      if (pivots[key] != null) {
        levels.push({ price: pivots[key], type: key.startsWith('r') ? 'R' : key.startsWith('s') ? 'S' : 'S/R', label, strength: key === 'pivot' ? 'MAJOR' : 'MODERATE' })
      }
    }
  }

  // Current day high/low
  const todayCandles = getTodayCandles(candles)
  if (todayCandles.length > 0) {
    const cdHigh = Math.max(...todayCandles.map(c => c.high))
    const cdLow = Math.min(...todayCandles.map(c => c.low))
    levels.push({ price: cdHigh, type: 'R', label: 'Current Day High', strength: 'STRONG' })
    levels.push({ price: cdLow, type: 'S', label: 'Current Day Low', strength: 'STRONG' })
  }

  // Supply / Demand zones from swing clusters
  const { highs, lows } = findSwingPoints(candles)
  const zoneThreshold = 0.0008 // 0.08% cluster tolerance

  // Supply zones: cluster of nearby swing highs
  if (highs.length >= 2) {
    for (let i = 0; i < highs.length; i++) {
      for (let j = i + 1; j < highs.length; j++) {
        const diff = Math.abs(highs[i].price - highs[j].price) / highs[i].price
        if (diff < zoneThreshold && Math.abs(highs[i].index - highs[j].index) > 3) {
          const zoneHigh = Math.max(highs[i].price, highs[j].price)
          const zoneLow = Math.min(highs[i].price, highs[j].price)
          levels.push({ price: zoneHigh, zoneLow, type: 'SUPPLY_ZONE', label: `Supply Zone ${levels.filter(l => l.type === 'SUPPLY_ZONE').length + 1}`, strength: 'MAJOR' })
        }
      }
    }
  }

  // Demand zones: cluster of nearby swing lows
  if (lows.length >= 2) {
    for (let i = 0; i < lows.length; i++) {
      for (let j = i + 1; j < lows.length; j++) {
        const diff = Math.abs(lows[i].price - lows[j].price) / lows[i].price
        if (diff < zoneThreshold && Math.abs(lows[i].index - lows[j].index) > 3) {
          const zoneHigh = Math.max(lows[i].price, lows[j].price)
          const zoneLow = Math.min(lows[i].price, lows[j].price)
          levels.push({ price: zoneLow, zoneHigh, type: 'DEMAND_ZONE', label: `Demand Zone ${levels.filter(l => l.type === 'DEMAND_ZONE').length + 1}`, strength: 'MAJOR' })
        }
      }
    }
  }

  // Deduplicate nearby levels
  levels.sort((a, b) => a.price - b.price)
  const deduped = []
  for (const l of levels) {
    if (deduped.length === 0 || Math.abs(l.price - deduped[deduped.length - 1].price) / l.price > 0.0003) {
      deduped.push(l)
    }
  }

  return deduped
}

// ─────────────────────────────────────────────
// 5. Volume Analysis
// ─────────────────────────────────────────────

function analyzeVolume(candles) {
  if (!candles || candles.length < 5) return { avgVolume: 0, signals: [] }

  const volumes = candles.map(c => c.volume || 0).filter(v => v > 0)
  if (volumes.length < 5) return { avgVolume: 0, signals: [] }

  const avgVolume = volumes.reduce((s, v) => s + v, 0) / volumes.length
  const last = candles[candles.length - 1]
  const lastVol = last.volume || 0
  const prevVol = candles.length > 1 ? (candles[candles.length - 2].volume || 0) : 0
  const signals = []

  if (lastVol > avgVolume * 1.5) {
    signals.push({ type: 'HIGH_VOLUME', detail: `${(lastVol / avgVolume).toFixed(1)}× average`, strength: 'STRONG' })
  } else if (lastVol < avgVolume * 0.5) {
    signals.push({ type: 'LOW_VOLUME', detail: `${(lastVol / avgVolume).toFixed(1)}× average`, strength: 'WARNING' })
  }

  if (lastVol > prevVol * 1.8) {
    const direction = last.close > last.open ? 'BULLISH' : 'BEARISH'
    signals.push({ type: 'VOLUME_SPIKE', detail: `${direction} volume spike`, strength: direction === 'BULLISH' ? 'STRONG' : 'BEARISH' })
  }

  // Volume confirmation for breakouts
  const body = Math.abs(last.close - last.open)
  if (body > 0 && lastVol > avgVolume * 1.3 && body > (last.high - last.low) * 0.6) {
    const direction = last.close > last.open ? 'BULLISH' : 'BEARISH'
    signals.push({ type: 'VOLUME_CONFIRMATION', detail: `${direction} volume confirms price move`, strength: 'STRONG' })
  }

  return { avgVolume, signals }
}

// ─────────────────────────────────────────────
// 6. Volatility Analysis
// ─────────────────────────────────────────────

function analyzeVolatility(candles, atrValue) {
  if (!candles || candles.length < 3) return { atr: atrValue || 0, avgCandleRange: 0, signals: [] }

  const ranges = candles.slice(-10).map(c => c.high - c.low)
  const avgCandleRange = ranges.reduce((s, r) => s + r, 0) / ranges.length
  const last = candles[candles.length - 1]
  const currentRange = last.high - last.low
  const signals = []

  if (currentRange > avgCandleRange * 1.5) {
    signals.push({ type: 'EXPANSION', detail: `Candle range ${(currentRange / avgCandleRange).toFixed(1)}× average — volatility expanding` })
  }
  if (currentRange < avgCandleRange * 0.5) {
    signals.push({ type: 'CONTRACTION', detail: `Candle range ${(currentRange / avgCandleRange).toFixed(1)}× average — volatility contracting` })
  }

  return { atr: atrValue || 0, avgCandleRange, currentRange, signals }
}

// ─────────────────────────────────────────────
// 7. Momentum Analysis
// ─────────────────────────────────────────────

function analyzeMomentum(candles, vwapValue) {
  if (!candles || candles.length < 15) return { rsi: null, macd: null, vwap: vwapValue, signals: [] }

  const closes = candles.map(c => c.close)
  const rsi = calculateRSI(closes, 14)
  const macd = calculateMACD(closes)
  const last = candles[candles.length - 1]
  const signals = []

  // RSI
  if (rsi != null) {
    if (rsi > 70) signals.push({ type: 'RSI_OVERBOUGHT', detail: `RSI ${rsi.toFixed(1)} — overbought, potential reversal down` })
    else if (rsi < 30) signals.push({ type: 'RSI_OVERSOLD', detail: `RSI ${rsi.toFixed(1)} — oversold, potential reversal up` })
    else if (rsi > 60) signals.push({ type: 'RSI_BULLISH', detail: `RSI ${rsi.toFixed(1)} — bullish momentum` })
    else if (rsi < 40) signals.push({ type: 'RSI_BEARISH', detail: `RSI ${rsi.toFixed(1)} — bearish momentum` })
    else signals.push({ type: 'RSI_NEUTRAL', detail: `RSI ${rsi.toFixed(1)} — neutral` })
  }

  // MACD
  if (macd.histogram != null) {
    if (macd.histogram > 0 && macd.macd > macd.signal) {
      signals.push({ type: 'MACD_BULLISH', detail: `MACD histogram ${macd.histogram.toFixed(1)} — bullish crossover` })
    } else if (macd.histogram < 0 && macd.macd < macd.signal) {
      signals.push({ type: 'MACD_BEARISH', detail: `MACD histogram ${macd.histogram.toFixed(1)} — bearish crossover` })
    } else if (macd.histogram > 0) {
      signals.push({ type: 'MACD_IMPROVING', detail: `MACD histogram ${macd.histogram.toFixed(1)} — improving` })
    } else {
      signals.push({ type: 'MACD_WEAKENING', detail: `MACD histogram ${macd.histogram.toFixed(1)} — weakening` })
    }
  }

  // VWAP position
  if (vwapValue != null) {
    const vwapDiff = ((last.close - vwapValue) / vwapValue) * 100
    if (last.close > vwapValue && vwapDiff > 0.1) {
      signals.push({ type: 'ABOVE_VWAP', detail: `Price ${vwapDiff.toFixed(2)}% above VWAP — bullish bias` })
    } else if (last.close < vwapValue && vwapDiff < -0.1) {
      signals.push({ type: 'BELOW_VWAP', detail: `Price ${Math.abs(vwapDiff).toFixed(2)}% below VWAP — bearish bias` })
    } else {
      signals.push({ type: 'AT_VWAP', detail: 'Price near VWAP — neutral' })
    }
  }

  // EMA trend
  const { trend, strength, ema9, ema21 } = detectTrendV2(candles)
  signals.push({ type: `EMA_${trend}`, detail: `EMA9 ${ema9?.toFixed(0) || '?'} / EMA21 ${ema21?.toFixed(0) || '?'} — ${trend} (${strength})` })

  return { rsi, macd, ema9: detectTrendV2(candles).ema9, ema21: detectTrendV2(candles).ema21, vwap: vwapValue, signals }
}

// ─────────────────────────────────────────────
// 8. Multi-Timeframe Analysis
// ─────────────────────────────────────────────

function analyzeMultiTimeframe(candles) {
  const results = {}

  // Current interval analysis
  results.current = {
    count: candles.length,
    trend: detectTrendV2(candles),
    swings: findSwingPoints(candles),
  }

  // Simulate higher timeframe by aggregating candles
  // Try 3-5x aggregation for higher timeframe view
  if (candles.length >= 20) {
    const agg5 = aggregateCandles(candles, 5)
    if (agg5.length >= 5) {
      results.higher = {
        count: agg5.length,
        trend: detectTrendV2(agg5),
        swings: findSwingPoints(agg5),
      }
    }
  }

  return results
}

// ─────────────────────────────────────────────
// 9. Confidence Score Calculation
// ─────────────────────────────────────────────

function calculateConfidence(direction, analysis) {
  let score = 50 // base

  const trend = analysis.marketDirection.direction
  const trendStrength = analysis.marketDirection.strength
  const momentum = analysis.momentum
  const volume = analysis.volume
  const priceAction = analysis.priceAction
  const volatility = analysis.volatility

  // Trend alignment
  if (direction === 'BULLISH') {
    if (trend === 'UPTREND') score += 20
    else if (trend === 'PULLBACK_BULLISH') score += 10
    else if (trend === 'RANGING') score += 5
    else score -= 10 // downtrend = headwind

    if (trendStrength === 'STRONG') score += 10
  } else {
    if (trend === 'DOWNTREND') score += 20
    else if (trend === 'PULLBACK_BEARISH') score += 10
    else if (trend === 'RANGING') score += 5
    else score -= 10

    if (trendStrength === 'STRONG') score += 10
  }

  // Momentum alignment (up to +15)
  for (const sig of momentum.signals) {
    if (direction === 'BULLISH') {
      if (sig.type === 'RSI_BULLISH' || sig.type === 'MACD_BULLISH' || sig.type === 'ABOVE_VWAP') score += 5
      if (sig.type === 'RSI_OVERBOUGHT') score -= 5 // caution
    } else {
      if (sig.type === 'RSI_BEARISH' || sig.type === 'MACD_BEARISH' || sig.type === 'BELOW_VWAP') score += 5
      if (sig.type === 'RSI_OVERSOLD') score -= 5
    }
  }

  // Volume confirmation (up to +10)
  for (const sig of volume.signals) {
    if (sig.type === 'VOLUME_CONFIRMATION') score += 10
    if (sig.type === 'VOLUME_SPIKE') score += 5
    if (sig.type === 'HIGH_VOLUME') score += 3
    if (sig.type === 'LOW_VOLUME') score -= 5
  }

  // Price action quality (up to +15)
  for (const sig of priceAction.signals) {
    if (sig.type === 'MOMENTUM_CANDLE' || sig.type === 'MARUBOZU') {
      if (sig.direction === direction) score += 10
    }
    if (sig.type === 'BULLISH_ENGULFING' || sig.type === 'BEARISH_ENGULFING') {
      if (sig.direction === direction) score += 8
    }
    if (sig.type === 'BREAKOUT' || sig.type === 'BREAKDOWN') {
      if (sig.direction === direction) score += 8
    }
    if (sig.type === 'PIN_BAR_BULLISH' || sig.type === 'PIN_BAR_BEARISH') {
      if (sig.direction === direction) score += 5
    }
    if (sig.type === 'DOJI') score -= 3 // indecision
  }

  // Volatility (up to +5)
  for (const sig of volatility.signals) {
    if (sig.type === 'EXPANSION') score += 5
    if (sig.type === 'CONTRACTION') score -= 3
  }

  // RR adjustment: higher RR = higher confidence
  // (handled externally after targets are set)

  return Math.max(0, Math.min(100, Math.round(score)))
}

// ─────────────────────────────────────────────
// 10. Main Trade Analysis Engine
// ─────────────────────────────────────────────

/**
 * Generate a complete institutional-grade trade analysis.
 *
 * Every trade goes through:
 *   Market direction → Structure → Price action → S/R → Volume →
 *   Volatility → Momentum → Risk placement → Target selection →
 *   Confidence scoring → Validation
 *
 * Returns null if the market is too sideways or no clear signal.
 */
export function generateExpertSetup(candles, dailyRefs, atrValue, vwapValue, intervalMinutes = 5) {
  if (!candles || candles.length < 5) {
    return { setups: [], marketContext: { vwapValue, vwapBias: 'Neutral', atr: atrValue || 0, orbState: 'N/A', orbRange: {}, trend: 'N/A', close: null } }
  }

  const last = candles[candles.length - 1]
  const prev = candles.length >= 2 ? candles[candles.length - 2] : null
  const todayCandles = getTodayCandles(candles)

  // ── 1. ORB ──
  const orbRange = detectOpeningRange(candles, intervalMinutes)
  const orbState = orbRange.orbHigh
    ? orbRange.orbBrokenUp ? 'Broken Up' : orbRange.orbBrokenDn ? 'Broken Down' : 'Intact'
    : 'Forming'

  // ── 2. Market Direction (Dow Theory) ──
  const { highs, lows } = findSwingPoints(candles)
  const marketDirection = analyzeMarketDirection(highs, lows)

  // ── 3. Trend ──
  const trendAnalysis = detectTrendV2(candles)

  // ── 4. Price Action ──
  const pa = analyzePriceAction(candles)

  // ── 5. Support / Resistance ──
  const srLevels = buildSupportResistance(candles, dailyRefs, null)

  // ── 6. Volume ──
  const volumeAnalysis = analyzeVolume(candles)

  // ── 7. Volatility ──
  const volatilityAnalysis = analyzeVolatility(candles, atrValue)

  // ── 8. Momentum ──
  const momentumAnalysis = analyzeMomentum(candles, vwapValue)

  // ── 9. Multi-timeframe ──
  const mtfAnalysis = analyzeMultiTimeframe(candles)

  // ── 10. VWAP bias ──
  const diffFromVwap = last.close - vwapValue
  const vwapBias = Math.abs(diffFromVwap) < 0.5 * atrValue
    ? 'Neutral'
    : diffFromVwap > 0 ? 'Bullish' : 'Bearish'

  // ── 11. Build trade setups ──
  const rawSetups = buildRawSetups(candles, last, prev, dailyRefs, orbRange, pa, vwapValue, atrValue, todayCandles)
  const scoredSetups = scoreSetups(rawSetups, vwapBias)
  const finalSetups = scoredSetups
    .map(s => buildFullAnalysis(s, candles, dailyRefs, orbRange, vwapValue, atrValue, srLevels, marketDirection, trendAnalysis, pa, volumeAnalysis, volatilityAnalysis, momentumAnalysis, mtfAnalysis))
    .filter(s => s !== null && s.valid === true) // Only valid, actionable setups — no random alerts

  // Market context
  const marketContext = {
    vwapValue,
    vwapBias,
    atr: atrValue,
    orbState,
    orbRange,
    trend: marketDirection.direction,
    close: last.close,
    swingHighs: highs.map(h => h.price),
    swingLows: lows.map(l => l.price),
    marketDirection: marketDirection.description,
    trendStrength: trendAnalysis.strength,
    volumeAvg: volumeAnalysis.avgVolume,
    rsi: momentumAnalysis.rsi,
    srLevels: srLevels.slice(0, 10).map(l => ({ price: l.price, label: l.label, type: l.type })),
  }

  return { setups: finalSetups, marketContext }
}

// ── Raw Setup Builder ──

function buildRawSetups(candles, last, prev, dailyRefs, orbRange, pa, vwapValue, atrValue, todayCandles) {
  const raw = []

  // ORB Breakout
  if (orbRange.orbBrokenUp && orbRange.orbHigh) {
    raw.push({ type: 'ORB_BREAKOUT_BULL', direction: 'BULLISH', triggerPrice: last.close, candle: last })
  }
  if (orbRange.orbBrokenDn && orbRange.orbLow) {
    raw.push({ type: 'ORB_BREAKDOWN_BEAR', direction: 'BEARISH', triggerPrice: last.close, candle: last })
  }

  // Prev Day High/Low Breakout
  if (dailyRefs?.prevDayHigh && last.close > dailyRefs.prevDayHigh && last.high > dailyRefs.prevDayHigh) {
    raw.push({ type: 'PREV_HIGH_BREAKOUT', direction: 'BULLISH', triggerPrice: last.close, candle: last })
  }
  if (dailyRefs?.prevDayLow && last.close < dailyRefs.prevDayLow && last.low < dailyRefs.prevDayLow) {
    raw.push({ type: 'PREV_LOW_BREAKDOWN', direction: 'BEARISH', triggerPrice: last.close, candle: last })
  }

  // Weekly breakouts
  if (dailyRefs?.weeklyHigh && last.close > dailyRefs.weeklyHigh && last.high > dailyRefs.weeklyHigh) {
    raw.push({ type: 'WEEKLY_HIGH_BREAKOUT', direction: 'BULLISH', triggerPrice: last.close, candle: last })
  }
  if (dailyRefs?.weeklyLow && last.close < dailyRefs.weeklyLow && last.low < dailyRefs.weeklyLow) {
    raw.push({ type: 'WEEKLY_LOW_BREAKDOWN', direction: 'BEARISH', triggerPrice: last.close, candle: last })
  }

  // VWAP rejection
  if (prev && vwapValue != null) {
    if (last.close > vwapValue && prev.close < vwapValue) {
      raw.push({ type: 'VWAP_REJECTION_BULL', direction: 'BULLISH', triggerPrice: last.close, candle: last })
    }
    if (last.close < vwapValue && prev.close > vwapValue) {
      raw.push({ type: 'VWAP_REJECTION_BEAR', direction: 'BEARISH', triggerPrice: last.close, candle: last })
    }
  }

  // Engulfing
  for (const sig of pa.signals) {
    if (sig.type === 'BULLISH_ENGULFING') {
      raw.push({ type: 'BULLISH_ENGULFING', direction: 'BULLISH', triggerPrice: last.close, candle: last })
    }
    if (sig.type === 'BEARISH_ENGULFING') {
      raw.push({ type: 'BEARISH_ENGULFING', direction: 'BEARISH', triggerPrice: last.close, candle: last })
    }
  }

  // Momentum breakouts from price action
  if (pa.signals.some(s => s.type === 'BREAKOUT' && s.direction === 'BULLISH') && !raw.some(r => r.type === 'ORB_BREAKOUT_BULL')) {
    raw.push({ type: 'TREND_BREAK_BULL', direction: 'BULLISH', triggerPrice: last.close, candle: last })
  }
  if (pa.signals.some(s => s.type === 'BREAKDOWN' && s.direction === 'BEARISH') && !raw.some(r => r.type === 'ORB_BREAKDOWN_BEAR')) {
    raw.push({ type: 'TREND_BREAK_BEAR', direction: 'BEARISH', triggerPrice: last.close, candle: last })
  }

  return raw
}

// ── Scoring ──

function scoreSetups(setups, vwapBias) {
  return setups
    .filter(s => {
      if (vwapBias === 'Bullish' && s.direction === 'BEARISH') return false
      if (vwapBias === 'Bearish' && s.direction === 'BULLISH') return false
      return true
    })
    .map(s => {
      let score = 50
      switch (s.type) {
        case 'ORB_BREAKOUT_BULL': case 'ORB_BREAKDOWN_BEAR': score += 25; break
        case 'WEEKLY_HIGH_BREAKOUT': case 'WEEKLY_LOW_BREAKDOWN': score += 15; break
        case 'VWAP_REJECTION_BULL': case 'VWAP_REJECTION_BEAR': score += 15; break
        case 'BULLISH_ENGULFING': case 'BEARISH_ENGULFING': score += 15; break
        case 'PREV_HIGH_BREAKOUT': case 'PREV_LOW_BREAKDOWN': score += 10; break
        case 'TREND_BREAK_BULL': case 'TREND_BREAK_BEAR': score += 10; break
        default: score += 5
      }
      return { ...s, score }
    })
    .sort((a, b) => b.score - a.score)
}

// ── Full Institutional Analysis Builder ──

function buildFullAnalysis(setup, candles, dailyRefs, orbRange, vwapValue, atrValue, srLevels, marketDirection, trendAnalysis, pa, volumeAnalysis, volatilityAnalysis, momentumAnalysis, mtfAnalysis) {
  const { type, direction, triggerPrice, candle, score } = setup
  const isBullish = direction === 'BULLISH'
  const entry = triggerPrice

  // ── Find nearest swing levels for SL ──
  const { swingHighAbove, swingLowBelow } = findNearestSwing(candles, entry)

  // ── SL Placement ──
  let stopLoss = null
  let slReason = ''

  if (isBullish) {
    // BUY SL priority: swing low > demand zone > breakout candle low > VWAP
    if (swingLowBelow != null && (entry - swingLowBelow) <= atrValue * 2.5) {
      // Place SL a small buffer below the swing low so normal wick tests don't trigger it
      const slBuffer = Math.max(atrValue * 0.1, entry * 0.0003) // 10% of ATR or 0.03% of price
      stopLoss = swingLowBelow - slBuffer
      slReason = `Below nearest swing low at ${swingLowBelow.toFixed(0)} (buffer ${slBuffer.toFixed(1)}) — structural invalidation`
    } else {
      // Find demand zone below
      const demandBelow = srLevels.filter(l => (l.type === 'DEMAND_ZONE' || l.type === 'S') && l.price < entry)
      if (demandBelow.length > 0) {
        const nearestDemand = demandBelow[demandBelow.length - 1]
        stopLoss = nearestDemand.price
        slReason = `Below demand zone / support at ${nearestDemand.price.toFixed(0)} — ${nearestDemand.label}`
      } else {
        // Breakout candle low
        stopLoss = Math.min(candle.low, entry - atrValue * 0.8)
        slReason = `Below breakout candle low at ${candle.low.toFixed(0)} — pattern invalidation`
      }
    }

    // Cap SL at 2× ATR for sensible risk
    if (entry - stopLoss > atrValue * 2.5) {
      stopLoss = entry - atrValue * 2.0
      slReason += ` (capped at 2× ATR for risk control)`
    }
  } else {
    // SELL SL priority: swing high > supply zone > breakout candle high > VWAP
    if (swingHighAbove != null && (swingHighAbove - entry) <= atrValue * 2.5) {
      // Place SL a small buffer above the swing high to avoid wick-triggered stops
      const slBuffer = Math.max(atrValue * 0.1, entry * 0.0003)
      stopLoss = swingHighAbove + slBuffer
      slReason = `Above nearest swing high at ${swingHighAbove.toFixed(0)} (buffer ${slBuffer.toFixed(1)}) — structural invalidation`
    } else {
      const supplyAbove = srLevels.filter(l => (l.type === 'SUPPLY_ZONE' || l.type === 'R') && l.price > entry)
      if (supplyAbove.length > 0) {
        const nearestSupply = supplyAbove[0]
        stopLoss = nearestSupply.price
        slReason = `Above supply zone / resistance at ${nearestSupply.price.toFixed(0)} — ${nearestSupply.label}`
      } else {
        stopLoss = Math.max(candle.high, entry + atrValue * 0.8)
        slReason = `Above breakdown candle high at ${candle.high.toFixed(0)} — pattern invalidation`
      }
    }

    if (stopLoss - entry > atrValue * 2.5) {
      stopLoss = entry + atrValue * 2.0
      slReason += ` (capped at 2× ATR for risk control)`
    }
  }

  if (stopLoss == null || (isBullish ? entry - stopLoss <= 0 : stopLoss - entry <= 0)) {
    return null
  }

  const risk = isBullish ? entry - stopLoss : stopLoss - entry

  // ── Target Selection ──
  // Sort S/R levels relative to entry
  const resistances = srLevels.filter(l => l.price > entry + risk * 0.3).sort((a, b) => a.price - b.price)
  const supports = srLevels.filter(l => l.price < entry - risk * 0.3).sort((a, b) => b.price - a.price) // descending

  let target1 = null, target1Reason = ''
  let target2 = null, target2Reason = ''
  let target3 = null, target3Reason = ''
  let target4 = null, target4Reason = ''

  if (isBullish) {
    // Target 1: nearest resistance
    if (resistances.length > 0) {
      target1 = resistances[0].price
      target1Reason = `Nearest resistance: ${resistances[0].label} at ${resistances[0].price.toFixed(0)}`
    } else {
      target1 = entry + atrValue * 1.0
      target1Reason = `1× ATR projection (no nearby resistance)`
    }

    // Target 2: Prev Day High or next resistance
    if (dailyRefs?.prevDayHigh && dailyRefs.prevDayHigh > target1) {
      target2 = dailyRefs.prevDayHigh
      target2Reason = `Previous Day High at ${dailyRefs.prevDayHigh.toFixed(0)}`
    } else if (resistances.length > 1) {
      target2 = resistances[1].price
      target2Reason = `Next resistance: ${resistances[1].label} at ${resistances[1].price.toFixed(0)}`
    } else {
      target2 = entry + atrValue * 1.5
      target2Reason = `1.5× ATR extension`
    }

    // Target 3: next supply zone or weekly high
    const supplyZone = resistances.find(l => l.type === 'SUPPLY_ZONE' || l.strength === 'MAJOR')
    if (supplyZone && supplyZone.price > target2) {
      target3 = supplyZone.price
      target3Reason = `Supply zone: ${supplyZone.label} at ${supplyZone.price.toFixed(0)}`
    } else if (dailyRefs?.weeklyHigh && dailyRefs.weeklyHigh > target2) {
      target3 = dailyRefs.weeklyHigh
      target3Reason = `Weekly High at ${dailyRefs.weeklyHigh.toFixed(0)}`
    } else {
      target3 = entry + atrValue * 2.0
      target3Reason = `2× ATR measured move projection`
    }

    // Target 4: measured move (risk × 3 or 2× ATR beyond)
    target4 = entry + risk * 3
    target4Reason = `Measured move: 3× risk projection (${(risk * 3).toFixed(0)} pts)`

  } else {
    // SELL targets
    if (supports.length > 0) {
      target1 = supports[0].price
      target1Reason = `Nearest support: ${supports[0].label} at ${supports[0].price.toFixed(0)}`
    } else {
      target1 = entry - atrValue * 1.0
      target1Reason = `1× ATR projection (no nearby support)`
    }

    if (dailyRefs?.prevDayLow && dailyRefs.prevDayLow < target1) {
      target2 = dailyRefs.prevDayLow
      target2Reason = `Previous Day Low at ${dailyRefs.prevDayLow.toFixed(0)}`
    } else if (supports.length > 1) {
      target2 = supports[1].price
      target2Reason = `Next support: ${supports[1].label} at ${supports[1].price.toFixed(0)}`
    } else {
      target2 = entry - atrValue * 1.5
      target2Reason = `1.5× ATR extension`
    }

    const demandZone = supports.find(l => l.type === 'DEMAND_ZONE' || l.strength === 'MAJOR')
    if (demandZone && demandZone.price < target2) {
      target3 = demandZone.price
      target3Reason = `Demand zone: ${demandZone.label} at ${demandZone.price.toFixed(0)}`
    } else if (dailyRefs?.weeklyLow && dailyRefs.weeklyLow < target2) {
      target3 = dailyRefs.weeklyLow
      target3Reason = `Weekly Low at ${dailyRefs.weeklyLow.toFixed(0)}`
    } else {
      target3 = entry - atrValue * 2.0
      target3Reason = `2× ATR measured move projection`
    }

    target4 = entry - risk * 3
    target4Reason = `Measured move: 3× risk projection (${(risk * 3).toFixed(0)} pts)`
  }

  // ── RR Calculation ──
  const reward1 = isBullish ? target1 - entry : entry - target1
  const rr1 = risk > 0 ? reward1 / risk : 0

  // ── Trade Validation ──
  let valid = true
  let rejectionReason = null

  // Reject if RR < 1:2 on target 1
  if (rr1 < 2.0) {
    valid = false
    rejectionReason = `Risk:Reward ${rr1.toFixed(1)}:1 on Target 1 is below minimum 1:2 requirement`
  }

  // Reject if target 1 is too close (less than 0.5× risk)
  if (reward1 < risk * 0.5) {
    valid = false
    rejectionReason = `Target 1 too close (${reward1.toFixed(0)} pts) relative to risk (${risk.toFixed(0)} pts)`
  }

  // Reject if market is clearly sideways
  if (marketDirection.direction === 'RANGING' && marketDirection.strength === 'WEAK') {
    if (pa.signals.filter(s => s.type === 'DOJI' || s.type === 'INSIDE_BAR').length >= 2) {
      valid = false
      rejectionReason = 'Market is sideways — multiple doji/inside bars, no clear direction'
    }
  }

  // Reject if volume confirmation is missing for breakout setups
  const needsVolume = type.includes('BREAKOUT') || type.includes('BREAK')
  if (needsVolume && !volumeAnalysis.signals.some(s => s.type === 'VOLUME_CONFIRMATION' || s.type === 'HIGH_VOLUME')) {
    valid = false
    rejectionReason = `Volume confirmation missing for ${LABEL_MAP[type] || type} — low volume breakout is suspicious`
  }

  // Reject if support and resistance are too close
  if (resistances.length > 0 && supports.length > 0) {
    const nearestR = resistances[0].price
    const nearestS = supports[0].price
    if (nearestR - nearestS < atrValue * 0.5) {
      valid = false
      rejectionReason = `Support (${nearestS.toFixed(0)}) and resistance (${nearestR.toFixed(0)}) too close — unreliable breakout`
    }
  }

  // ── Confidence Score ──
  const analysis = {
    marketDirection,
    trend: trendAnalysis,
    priceAction: { patterns: pa.patterns, signals: pa.signals },
    volume: volumeAnalysis,
    volatility: volatilityAnalysis,
    momentum: momentumAnalysis,
    multiTimeframe: mtfAnalysis,
  }

  const baseConfidence = calculateConfidence(direction, analysis)

  // Bonus for good RR
  const rrBonus = rr1 >= 3.0 ? 10 : rr1 >= 2.5 ? 5 : 0
  // Penalty for weak setups
  const trendPenalty = marketDirection.strength === 'WEAK' && marketDirection.direction === 'RANGING' ? -10 : 0
  // Volume penalty
  const volumePenalty = volumeAnalysis.signals.some(s => s.type === 'LOW_VOLUME') ? -8 : 0

  const confidence = Math.max(0, Math.min(100, baseConfidence + rrBonus + trendPenalty + volumePenalty))

  // ── Build final setup object ──
  const priceActionPatterns = pa.patterns.slice(0, 3).join('; ')

  return {
    // Core trade fields (backward compatible)
    type,
    direction,
    triggerPrice: entry,
    score: valid ? confidence : confidence,
    candle,
    entry: roundTo(entry),
    stopLoss: roundTo(stopLoss),
    target1: roundTo(target1),
    target2: roundTo(target2),
    target3: roundTo(target3),
    target4: roundTo(target4),
    riskReward: roundTo(rr1, 1),
    riskAmount: roundTo(risk),
    rewardAmount: roundTo(reward1),
    label: LABEL_MAP[type] || type,
    slNote: slReason,

    // New institutional fields
    valid,
    rejectionReason,
    confidence,

    // Detailed reasons
    entryReason: direction === 'BULLISH'
      ? `Bullish signal: ${priceActionPatterns || LABEL_MAP[type]}. Trend: ${marketDirection.description}`
      : `Bearish signal: ${priceActionPatterns || LABEL_MAP[type]}. Trend: ${marketDirection.description}`,
    slReason,
    target1Reason,
    target2Reason,
    target3Reason,
    target4Reason,

    // Analysis summary
    analysisSummary: {
      marketDirection: marketDirection.description,
      trendStrength: trendAnalysis.strength,
      patterns: pa.patterns,
      momentumSig: momentumAnalysis.signals.slice(0, 3).map(s => s.detail),
      volumeSig: volumeAnalysis.signals.slice(0, 2).map(s => s.detail),
      volatilitySig: volatilityAnalysis.signals.slice(0, 2).map(s => s.detail),
      rsi: momentumAnalysis.rsi,
      macd: momentumAnalysis.macd,
      srLevels: srLevels.filter(l =>
        (isBullish && l.price > entry && l.price < entry + atrValue * 3) ||
        (!isBullish && l.price < entry && l.price > entry - atrValue * 3)
      ).slice(0, 5).map(l => ({ price: l.price, label: l.label })),
    },
  }
}

// ── Exported helpers ──

export function calculateVWAP(candles) {
  if (!candles || candles.length === 0) return null
  let totalPV = 0, totalVol = 0
  for (const c of candles) {
    const typicalPrice = (c.high + c.low + c.close) / 3
    const vol = c.volume || 0
    totalPV += typicalPrice * vol
    totalVol += vol
  }
  if (totalVol === 0) {
    let sum = 0
    for (const c of candles) sum += (c.high + c.low + c.close) / 3
    return sum / candles.length
  }
  return totalPV / totalVol
}

export function detectOpeningRange(candles, intervalMinutes = 5) {
  const orbCandles = Math.max(1, Math.ceil(15 / intervalMinutes))
  const todayCandles = getTodayCandles(candles)
  if (todayCandles.length < orbCandles) {
    return { orbHigh: null, orbLow: null, orbBrokenUp: false, orbBrokenDn: false, timeBroken: null }
  }
  const orbCandleSlice = todayCandles.slice(0, orbCandles)
  const orbHigh = Math.max(...orbCandleSlice.map(c => c.high))
  const orbLow = Math.min(...orbCandleSlice.map(c => c.low))
  let orbBrokenUp = false, orbBrokenDn = false, timeBroken = null
  for (const c of todayCandles.slice(orbCandles)) {
    if (!orbBrokenUp && c.close > orbHigh) { orbBrokenUp = true; timeBroken = c.time }
    if (!orbBrokenDn && c.close < orbLow) { orbBrokenDn = true; timeBroken = c.time }
  }
  return { orbHigh, orbLow, orbBrokenUp, orbBrokenDn, timeBroken }
}
