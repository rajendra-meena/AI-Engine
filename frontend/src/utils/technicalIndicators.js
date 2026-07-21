export function calculateSMA(data, period) {
  const result = []
  for (let i = 0; i < data.length; i++) {
    if (i < period - 1) { result.push(null); continue }
    let sum = 0
    for (let j = i - period + 1; j <= i; j++) sum += data[j]
    result.push(sum / period)
  }
  return result
}

export function calculateEMA(data, period) {
  const result = []
  const multiplier = 2 / (period + 1)
  let sum = 0
  const count = Math.min(period, data.length)
  for (let i = 0; i < count; i++) sum += data[i]
  const sma = sum / count
  for (let i = 0; i < data.length; i++) {
    if (i < period - 1) result.push(null)
    else if (i === period - 1) result.push(sma)
    else result.push((data[i] - result[i - 1]) * multiplier + result[i - 1])
  }
  return result
}

export function calculateRSI(data, period = 14) {
  if (data.length < period + 1) return data.map(() => null)
  const changes = []
  for (let i = 1; i < data.length; i++) changes.push(data[i] - data[i - 1])
  const gains = changes.map(c => c > 0 ? c : 0)
  const losses = changes.map(c => c < 0 ? -c : 0)
  const rsi = [null]
  let avgGain = gains.slice(0, period).reduce((a, b) => a + b, 0) / period
  let avgLoss = losses.slice(0, period).reduce((a, b) => a + b, 0) / period
  for (let i = period; i < data.length; i++) {
    if (i === period) {
      const rs = avgLoss === 0 ? Infinity : avgGain / avgLoss
      rsi.push(rs === Infinity ? 100 : 100 - 100 / (1 + rs))
    } else {
      avgGain = (avgGain * (period - 1) + gains[i - 1]) / period
      avgLoss = (avgLoss * (period - 1) + losses[i - 1]) / period
      const rs = avgLoss === 0 ? Infinity : avgGain / avgLoss
      rsi.push(rs === Infinity ? 100 : 100 - 100 / (1 + rs))
    }
  }
  return rsi
}

export function calculateATR(high, low, close, period = 14) {
  if (high.length < 2) return high.map(() => null)
  const tr = []
  for (let i = 0; i < high.length; i++) {
    if (i === 0) tr.push(high[i] - low[i])
    else {
      const hl = high[i] - low[i]
      const hc = Math.abs(high[i] - close[i - 1])
      const lc = Math.abs(low[i] - close[i - 1])
      tr.push(Math.max(hl, hc, lc))
    }
  }
  return calculateSMA(tr, period)
}

export function calculateADX(high, low, close, period = 14) {
  if (high.length < period + 1) return high.map(() => null)
  const tr = []; const plusDM = []; const minusDM = []
  for (let i = 1; i < high.length; i++) {
    const hl = high[i] - low[i]
    const hc = Math.abs(high[i] - close[i - 1])
    const lc = Math.abs(low[i] - close[i - 1])
    tr.push(Math.max(hl, hc, lc))
    const upMove = high[i] - high[i - 1]
    const downMove = low[i - 1] - low[i]
    const pdm = upMove > downMove && upMove > 0 ? upMove : 0
    const mdm = downMove > upMove && downMove > 0 ? downMove : 0
    plusDM.push(pdm); minusDM.push(mdm)
  }
  const atr = calculateSMA(tr, period)
  const pdi = calculateSMA(plusDM, period); const ndi = calculateSMA(minusDM, period)

  // Build DX array aligned to original data indices (index 0 = null, no prior bar)
  const dx = [null]
  for (let i = 0; i < tr.length; i++) {
    if (atr[i] && atr[i] > 0) {
      const p = (pdi[i] || 0) / atr[i] * 100
      const n = (ndi[i] || 0) / atr[i] * 100
      const diff = Math.abs(p - n)
      dx.push(p + n === 0 ? 0 : roundTo((diff / (p + n)) * 100, 1))
    } else dx.push(null)
  }
  const result = calculateSMA(dx, period)
  return result.map(v => (v != null && isNaN(v)) ? null : v)
}

function roundTo(v, d) { const m = Math.pow(10, d); return Math.round(v * m) / m }

export function calculatePivotPoints(data) {
  if (!data || data.length === 0) return null
  const last = data[data.length - 1]
  let windowHigh = -Infinity, windowLow = Infinity
  for (const d of data) { if (d.High > windowHigh) windowHigh = d.High; if (d.Low < windowLow) windowLow = d.Low }
  const high = windowHigh; const low = windowLow; const close = last.Close
  const pivot = (high + low + close) / 3
  return {
    pivot: roundTo(pivot, 2), r1: roundTo(2 * pivot - low, 2), r2: roundTo(pivot + (high - low), 2), r3: roundTo(high + 2 * (pivot - low), 2),
    s1: roundTo(2 * pivot - high, 2), s2: roundTo(pivot - (high - low), 2), s3: roundTo(low - 2 * (high - pivot), 2),
    currentPrice: close, isAbovePivot: close > pivot, windowHigh: high, windowLow: low,
  }
}

// ─────────────────────────────────────────────
// NEW: WINDOW-AWARE PREDICTION ENGINE
// Each preset has its own analysis rules.
// The function accepts data (the exact window) and a windowLabel string.
// ─────────────────────────────────────────────

export function runPrediction(data, windowLabel) {
  const n = data ? data.length : 0
  if (n < 3) return null

  const closes = data.map(d => d.Close)
  const highs = data.map(d => d.High)
  const lows = data.map(d => d.Low)
  const opens = data.map(d => d.Open)
  const volumes = data.map(d => d.Volume || 0)
  const last = data[n - 1]; const first = data[0]

  // Common calculations
  const sma9 = calculateSMA(closes, Math.min(9, n))
  const sma21 = calculateSMA(closes, Math.min(21, n))
  const sma50 = calculateSMA(closes, Math.min(50, n))
  const sma200 = calculateSMA(closes, Math.min(200, n))
  const lastSma9 = sma9[n - 1] ?? closes[n - 1]
  const lastSma21 = sma21[n - 1] ?? closes[n - 1]
  const lastSma50 = sma50[n - 1] ?? closes[n - 1]
  const lastSma200 = sma200[n - 1] ?? closes[n - 1]
  const lastClose = closes[n - 1]
  const lastOpen = opens[n - 1]
  const lastHigh = highs[n - 1]
  const lastLow = lows[n - 1]
  const atr14 = calculateATR(highs, lows, closes, 14)
  const lastATR = atr14[n - 1] ?? 0
  const rsi14 = calculateRSI(closes, Math.min(14, n))
  const lastRSI = rsi14[n - 1] ?? 50
  const adx14 = calculateADX(highs, lows, closes, Math.min(14, n))
  const lastADX = adx14[n - 1] ?? 0

  const pivots = calculatePivotPoints(data)

  // Window high/low/close ranges
  const winHigh = Math.max(...highs); const winLow = Math.min(...lows)
  const pricePosition = winHigh - winLow > 0 ? ((lastClose - winLow) / (winHigh - winLow)) * 100 : 50

  // Volume analysis
  const avgVol = volumes.reduce((a, b) => a + b, 0) / volumes.length
  const lastVol = volumes[n - 1]
  const volRatio = avgVol > 0 ? lastVol / avgVol : 1

  // Gap detection
  const gapUp = n > 1 ? lastLow > highs[n - 2] : false
  const gapDown = n > 1 ? lastHigh < lows[n - 2] : false
  const gapPercent = n > 1 ? ((lastOpen - highs[n - 2]) / highs[n - 2]) * 100 : 0

  // Higher High / Lower Low detection
  let higherHigh = false, lowerLow = false, lowerHigh = false, higherLow = false
  if (n > 2) {
    const mid = Math.floor(n / 2)
    const firstHalf = highs.slice(0, mid); const secondHalf = highs.slice(mid)
    higherHigh = Math.max(...secondHalf) > Math.max(...firstHalf)
    lowerLow = Math.min(...secondHalf) < Math.min(...firstHalf)
    lowerHigh = Math.max(...secondHalf) < Math.max(...firstHalf)
    higherLow = Math.min(...secondHalf) > Math.min(...firstHalf)
  }

  // Swing highs/lows (simple peaks/valleys)
  const swingHighs = []; const swingLows = []
  for (let i = 2; i < n - 1; i++) {
    if (highs[i] > highs[i - 1] && highs[i] > highs[i + 1]) swingHighs.push(highs[i])
    if (lows[i] < lows[i - 1] && lows[i] < lows[i + 1]) swingLows.push(lows[i])
  }
  const nearestResistance = swingHighs.length > 0 ? swingHighs[swingHighs.length - 1] : winHigh
  const nearestSupport = swingLows.length > 0 ? swingLows[swingLows.length - 1] : winLow

  // Trend channel
  const trendUp = higherHigh && higherLow
  const trendDown = lowerHigh && lowerLow

  // ── Fibonacci Retracement Levels ──
  const fibRange = winHigh - winLow
  const fibLevels = {
    '0.236': roundTo(winHigh - fibRange * 0.236, 2),
    '0.382': roundTo(winHigh - fibRange * 0.382, 2),
    '0.500': roundTo(winHigh - fibRange * 0.500, 2),
    '0.618': roundTo(winHigh - fibRange * 0.618, 2),
    '0.786': roundTo(winHigh - fibRange * 0.786, 2),
  }

  // ── VWAP (Volume-Weighted Average Price) ──
  let vwap = null
  let totalVol = 0, totalPV = 0
  for (let i = 0; i < n; i++) {
    const typicalPrice = (highs[i] + lows[i] + closes[i]) / 3
    totalVol += volumes[i]; totalPV += typicalPrice * volumes[i]
  }
  if (totalVol > 0) vwap = roundTo(totalPV / totalVol, 2)

  // ── Candlestick Pattern Detection ──
  const doji = n > 0 && Math.abs(lastClose - lastOpen) < (lastHigh - lastLow) * 0.1
  const hammer = n > 0 && (lastClose - lastLow) > (lastHigh - lastLow) * 0.6 && Math.abs(lastClose - lastOpen) < (lastHigh - lastLow) * 0.3
  const shootingStar = n > 0 && (lastHigh - Math.max(lastClose, lastOpen)) > (lastHigh - lastLow) * 0.6 && Math.abs(lastClose - lastOpen) < (lastHigh - lastLow) * 0.3
  const bullishEngulfing = n > 1 && lastClose > lastOpen && lastOpen < lows[n - 2] && lastClose > highs[n - 2]
  const bearishEngulfing = n > 1 && lastClose < lastOpen && lastOpen > highs[n - 2] && lastClose < lows[n - 2]

  // ── Dispatch to window-specific analyzer ──
  const label = windowLabel || ''

  if (label.includes('4D')) return analyze4D()
  if (label.includes('1W')) return analyze1W()
  if (label.includes('2W')) return analyze2W()
  if (label.includes('1M')) return analyze1M()
  if (label.includes('45D')) return analyze45D()
  if (label.includes('2M')) return analyze2M()

  // Fallback: use data-length heuristic
  if (n <= 4) return analyze4D()
  if (n <= 7) return analyze1W()
  if (n <= 14) return analyze2W()
  if (n <= 30) return analyze1M()
  if (n <= 50) return analyze45D()
  return analyze2M()

  // ═══════════════════════════════════════
  // 4D Analyzer
  // ═══════════════════════════════════════
  function analyze4D() {
    let score = 0; let factors = []

    // Higher High / Higher Low
    if (higherHigh && higherLow) { score += 30; factors.push('Higher highs and higher lows forming') }
    else if (lowerHigh && lowerLow) { score -= 30; factors.push('Lower highs and lower lows forming') }
    else factors.push('No clear short-term pattern')

    // Gap
    if (gapUp) { score += 20; factors.push(`Gap up of ${gapPercent.toFixed(1)}% shows buying pressure`) }
    else if (gapDown) { score -= 20; factors.push(`Gap down of ${Math.abs(gapPercent).toFixed(1)}% shows selling pressure`) }

    // Volume
    if (volRatio > 1.5) { score += 15; factors.push('Volume spike confirms momentum') }
    else if (volRatio < 0.5) { score -= 5; factors.push('Low volume suggests weak conviction') }

    // Closing strength
    const closePos = lastHigh - lastLow > 0 ? ((lastClose - lastLow) / (lastHigh - lastLow)) * 100 : 50
    if (closePos > 70) { score += 15; factors.push('Strong close near day high') }
    else if (closePos < 30) { score -= 15; factors.push('Weak close near day low') }

    // Price vs SMA9
    if (lastClose > lastSma9) { score += 10; factors.push('Price above SMA9 showing short-term strength') }
    else { score -= 10; factors.push('Price below SMA9 showing short-term weakness') }

    // RSI
    if (lastRSI > 70) { score -= 10; factors.push('RSI overbought at ' + lastRSI.toFixed(1)) }
    else if (lastRSI > 50) { score += 10; factors.push('RSI bullish at ' + lastRSI.toFixed(1)) }
    else if (lastRSI < 30) { score += 10; factors.push('RSI oversold at ' + lastRSI.toFixed(1) + ' — bounce possible') }
    else { score -= 10; factors.push('RSI bearish at ' + lastRSI.toFixed(1)) }

    const trend = score > 15 ? 'Bullish' : score < -15 ? 'Bearish' : 'Sideways'
    const strength = Math.abs(score) > 30 ? 'Strong' : Math.abs(score) > 15 ? 'Moderate' : 'Weak'
    const momentum = score > 0 ? 'Increasing' : 'Decreasing'
    const confidence = Math.min(Math.abs(score) + 40, 90)
    const risk = Math.abs(score) > 25 ? 'Low' : 'Medium'

    return buildResult({ trend, strength, momentum, confidence, risk, factors, score, label: '4D' })
  }

  // ═══════════════════════════════════════
  // 1W Analyzer
  // ═══════════════════════════════════════
  function analyze1W() {
    let score = 0; let factors = []

    // Weekly structure
    const weeklyRange = winHigh - winLow

    if (trendUp) { score += 25; factors.push('Weekly uptrend with higher highs') }
    else if (trendDown) { score -= 25; factors.push('Weekly downtrend with lower lows') }

    // SMA20 / SMA50
    if (lastClose > lastSma21) { score += 15; factors.push('Price above SMA21 (weekly strength)') }
    else { score -= 15; factors.push('Price below SMA21 (weekly weakness)') }
    if (lastSma21 > lastSma9) { score += 10; factors.push('SMA21 trending above SMA9 (bullish alignment)') }
    else { score -= 10; factors.push('SMA9 below SMA21 (bearish cross)') }

    // RSI
    if (lastRSI > 60) { score += 15; factors.push(`RSI at ${lastRSI.toFixed(1)} — bullish momentum`) }
    else if (lastRSI < 40) { score -= 15; factors.push(`RSI at ${lastRSI.toFixed(1)} — bearish momentum`) }
    else factors.push(`RSI at ${lastRSI.toFixed(1)} — neutral`)

    // ADX
    if (lastADX > 25) { score > 0 ? score += 10 : score -= 10; factors.push(`ADX at ${lastADX.toFixed(1)} — trending market`) }
    else if (lastADX > 0) factors.push(`ADX at ${lastADX.toFixed(1)} — range-bound market`)

    // Volume
    if (volRatio > 1.3) { score > 0 ? score += 10 : score -= 10; factors.push('Above-average volume confirms move') }
    else factors.push('Normal volume levels')

    // Engulfing
    if (bullishEngulfing) { score += 15; factors.push('Bullish engulfing pattern spotted') }
    if (bearishEngulfing) { score -= 15; factors.push('Bearish engulfing pattern spotted') }

    // Price position
    if (pricePosition > 60) { score += 10; factors.push('Price in upper half of weekly range') }
    else if (pricePosition < 40) { score -= 10; factors.push('Price in lower half of weekly range') }

    const trend = score > 20 ? 'Bullish' : score < -20 ? 'Bearish' : 'Sideways'
    const strength = Math.abs(score) > 35 ? 'Strong' : Math.abs(score) > 15 ? 'Moderate' : 'Weak'
    const momentum = score > 0 ? 'Increasing' : 'Decreasing'
    const confidence = Math.min(Math.abs(score) + 45, 92)
    const risk = Math.abs(score) > 30 ? 'Low' : 'Medium'

    return buildResult({ trend, strength, momentum, confidence, risk, factors, score, label: '1W' })
  }

  // ═══════════════════════════════════════
  // 2W Analyzer
  // ═══════════════════════════════════════
  function analyze2W() {
    let score = 0; let factors = []

    // Trend continuation / breakout
    const breakoutUp = lastClose > winHigh * 0.98 && volRatio > 1.2
    const breakdownDown = lastClose < winLow * 1.02 && volRatio > 1.2

    if (breakoutUp) { score += 35; factors.push('Price approaching window high with volume — breakout possible') }
    else if (breakdownDown) { score -= 35; factors.push('Price near window low with volume — breakdown risk') }

    if (trendUp) { score += 20; factors.push('Trend continuation pattern — higher highs and lows') }
    else if (trendDown) { score -= 20; factors.push('Trend breakdown pattern — lower highs and lows') }

    // Support/Resistance
    if (lastClose > (swingHighs[swingHighs.length - 1] || winHigh) * 0.95) factors.push('Testing resistance zone')
    if (lastClose < (swingLows[swingLows.length - 1] || winLow) * 1.05) factors.push('Testing support zone')

    // SMA20/50
    if (lastClose > lastSma21) { score += 12; factors.push('Price above SMA21') } else { score -= 12 }
    if (lastSma21 > lastSma50) { score += 10; factors.push('SMA21 above SMA50 — bullish alignment') } else { score -= 10 }

    // ATR expansion
    const atrStart = atr14[Math.min(5, n - 1)] ?? lastATR
    if (lastATR > atrStart * 1.2) { score > 0 ? score += 10 : score -= 10; factors.push('ATR expanding — volatility increasing') }

    // Volume expansion
    if (volRatio > 1.4) { score > 0 ? score += 10 : score -= 10; factors.push('Volume expansion confirms move') }

    const trend = score > 20 ? 'Bullish' : score < -20 ? 'Bearish' : 'Sideways'
    const strength = Math.abs(score) > 30 ? 'Strong' : 'Moderate'
    const momentum = score > 0 ? 'Increasing' : 'Decreasing'
    const breakoutProb = breakoutUp ? Math.min(score + 40, 85) : Math.min(Math.max(score * 0.7 + 50, 10), 80)
    const breakdownProb = breakdownDown ? Math.min(-score + 40, 85) : Math.min(Math.max(-score * 0.7 + 50, 10), 80)
    const confidence = Math.min(Math.abs(score) + 45, 93)
    const risk = Math.abs(score) > 25 ? 'Low' : 'Medium'

    return buildResult({ trend, strength, momentum, confidence, risk, factors, score, label: '2W', breakoutProb, breakdownProb })
  }

  // ═══════════════════════════════════════
  // 1M Analyzer
  // ═══════════════════════════════════════
  function analyze1M() {
    let score = 0; let factors = []

    // Highest/Lowest
    if (lastClose >= winHigh * 0.95) { score += 20; factors.push('Price near monthly high — bullish momentum') }
    else if (lastClose <= winLow * 1.05) { score -= 20; factors.push('Price near monthly low — bearish pressure') }

    // Price position in range
    if (pricePosition > 75) { score += 15; factors.push(`Price in upper quartile (${pricePosition.toFixed(0)}%) of monthly range`) }
    else if (pricePosition < 25) { score -= 15; factors.push(`Price in lower quartile (${pricePosition.toFixed(0)}%) of monthly range`) }

    // SMA alignment
    if (lastClose > lastSma21) { score += 10; factors.push('Price above SMA21') } else { score -= 10 }
    if (lastClose > lastSma50) { score += 15; factors.push('Price above SMA50 — medium-term bullish') } else { score -= 15 }
    if (lastSma21 > lastSma50) { score += 10; factors.push('SMA21 > SMA50 — golden alignment') } else { score -= 10 }

    // RSI
    if (lastRSI > 70) { score -= 10; factors.push('RSI overbought — caution for longs') }
    else if (lastRSI > 60) { score += 10; factors.push('RSI bullish without being overbought') }
    else if (lastRSI < 30) { score += 15; factors.push('RSI oversold — reversal possible') }
    else if (lastRSI < 40) { score -= 10; factors.push('RSI bearish territory') }
    else factors.push(`RSI neutral at ${lastRSI.toFixed(1)}`)

    // ADX
    if (lastADX > 30) { score > 0 ? score += 10 : score -= 10; factors.push(`ADX ${lastADX.toFixed(1)} — strong trend`) }
    else if (lastADX > 20) { factors.push(`ADX ${lastADX.toFixed(1)} — trend developing`) }
    else factors.push(`ADX ${lastADX.toFixed(1)} — low trend strength`)

    // Volume
    if (volRatio > 1.3) { score > 0 ? score += 10 : score -= 10; factors.push('Volume confirms monthly trend') }

    // Volatility
    const atrPercent = (lastATR / lastClose) * 100
    if (atrPercent > 3) factors.push('High volatility — wide stops recommended')
    else if (atrPercent < 1) factors.push('Low volatility environment')

    const trend = score > 25 ? 'Strong Bullish' : score > 10 ? 'Bullish' : score < -25 ? 'Strong Bearish' : score < -10 ? 'Bearish' : 'Neutral'
    const strength = Math.abs(score) > 35 ? 'Strong' : Math.abs(score) > 15 ? 'Moderate' : 'Weak'
    const momentum = score > 0 ? 'Increasing' : 'Decreasing'
    const confidence = Math.min(Math.abs(score) + 50, 95)
    const risk = Math.abs(score) > 30 ? 'Low' : 'Medium'

    return buildResult({ trend, strength, momentum, confidence, risk, factors, score, label: '1M' })
  }

  // ═══════════════════════════════════════
  // 45D Analyzer
  // ═══════════════════════════════════════
  function analyze45D() {
    let score = 0; let factors = []

    // Trend strength
    const maSlope = lastSma21 - sma21[Math.min(Math.floor(n * 0.5), n - 1)] ?? lastSma21
    if (maSlope > lastATR * 0.1) { score += 20; factors.push('Moving average sloping up — bullish structure') }
    else if (maSlope < -lastATR * 0.1) { score -= 20; factors.push('Moving average sloping down — bearish structure') }
    else factors.push('Moving averages flat — consolidation')

    // Swing structure
    if (trendUp) { score += 20; factors.push('Higher highs and higher lows — uptrend intact') }
    else if (trendDown) { score -= 20; factors.push('Lower highs and lower lows — downtrend intact') }

    // Price momentum
    const midIdx = Math.floor(n / 2)
    const firstHalfAvg = closes.slice(0, midIdx).reduce((a, b) => a + b, 0) / midIdx
    const secondHalfAvg = closes.slice(midIdx).reduce((a, b) => a + b, 0) / (n - midIdx)
    const momentumPct = ((secondHalfAvg - firstHalfAvg) / firstHalfAvg) * 100

    if (momentumPct > 2) { score += 15; factors.push(`Positive momentum of ${momentumPct.toFixed(1)}% in recent half`) }
    else if (momentumPct < -2) { score -= 15; factors.push(`Negative momentum of ${Math.abs(momentumPct).toFixed(1)}% in recent half`) }
    else factors.push('Momentum flat')

    // ATR for volatility context
    const atrPct = (lastATR / lastClose) * 100
    if (atrPct > 4) factors.push('High volatility regime — wider ranges expected')
    else if (atrPct < 1.5) factors.push('Low volatility — tightening ranges')

    // Breakout zones
    if (lastClose > winHigh * 0.95) { score += 10; factors.push('Approaching breakout zone') }
    else if (lastClose < winLow * 1.05) { score -= 10; factors.push('Near breakdown zone') }

    // Volume trend
    const firstHalfVol = volumes.slice(0, midIdx).reduce((a, b) => a + b, 0) / midIdx
    const secondHalfVol = volumes.slice(midIdx).reduce((a, b) => a + b, 0) / (n - midIdx)
    if (secondHalfVol > firstHalfVol * 1.2) { score > 0 ? score += 10 : score -= 10; factors.push('Volume rising — conviction building') }

    const trend = score > 20 ? 'Bullish' : score < -20 ? 'Bearish' : 'Sideways'
    const strength = Math.abs(score) > 35 ? 'Strong' : Math.abs(score) > 15 ? 'Moderate' : 'Weak'
    const momentum = momentumPct > 2 ? 'Increasing' : 'Decreasing'
    const confidence = Math.min(Math.abs(score) + 50, 94)
    const risk = Math.abs(score) > 25 ? 'Low' : 'Medium'

    return buildResult({ trend, strength, momentum, confidence, risk, factors, score, label: '45D' })
  }

  // ═══════════════════════════════════════
  // 2M Analyzer
  // ═══════════════════════════════════════
  function analyze2M() {
    let score = 0; let factors = []

    // SMA alignment (primary trend)
    if (lastSma9 > lastSma21 && lastSma21 > lastSma50) { score += 20; factors.push('SMA9 > SMA21 > SMA50 — strong bullish alignment') }
    else if (lastSma9 < lastSma21 && lastSma21 < lastSma50) { score -= 20; factors.push('SMA9 < SMA21 < SMA50 — strong bearish alignment') }
    else if (lastSma21 > lastSma50) { score += 10; factors.push('SMA21 above SMA50 — bullish bias') }
    else if (lastSma21 < lastSma50) { score -= 10; factors.push('SMA21 below SMA50 — bearish bias') }
    else factors.push('Moving averages mixed')

    // SMA200 for major trend
    if (lastSma200 > 0 && lastClose > lastSma200) { score += 15; factors.push('Price above SMA200 — long-term bullish') }
    else if (lastSma200 > 0) { score -= 15; factors.push('Price below SMA200 — long-term bearish') }

    // Major S/R via swings
    const majorResistance = swingHighs.length > 2 ? swingHighs.sort((a, b) => b - a)[0] : winHigh
    const majorSupport = swingLows.length > 2 ? swingLows.sort((a, b) => a - b)[0] : winLow
    if (lastClose >= majorResistance * 0.97) factors.push('Testing major resistance')
    if (lastClose <= majorSupport * 1.03) factors.push('Testing major support')

    // Trend channel
    if (trendUp) { score += 15; factors.push('Higher timeframe uptrend channel intact') }
    else if (trendDown) { score -= 15; factors.push('Higher timeframe downtrend channel intact') }

    // RSI
    if (lastRSI > 70 && score > 0) { score -= 5; factors.push('RSI overbought — trend may be extended') }
    else if (lastRSI > 60) { score += 10; factors.push('RSI confirms uptrend') }
    else if (lastRSI < 30 && score < 0) { score += 5; factors.push('RSI oversold — selling may be exhausted') }
    else if (lastRSI < 40) { score -= 10; factors.push('RSI confirms downtrend') }

    // ADX
    if (lastADX > 30) { score > 0 ? score += 10 : score -= 10; factors.push(`ADX ${lastADX.toFixed(1)} — strong directional trend`) }
    else factors.push(`ADX ${lastADX.toFixed(1)} — trend building or range`)

    // Volume profile
    if (volRatio > 1.3) { score > 0 ? score += 10 : score -= 10; factors.push('Volume spike confirms institutional interest') }

    // ATR
    const atrPct = (lastATR / lastClose) * 100
    if (atrPct > 3) factors.push(`${atrPct.toFixed(1)}% ATR — place wider stops`)
    else factors.push(`${atrPct.toFixed(1)}% ATR — normal volatility`)

    // Trend reversal probability
    const reversalProb = (score > 0 && lastRSI > 70) || (score < 0 && lastRSI < 30) ? 'Moderate' : 'Low'

    const primaryTrend = score > 10 ? 'Bullish' : score < -10 ? 'Bearish' : 'Sideways'
    const secondaryTrend = (score > 0 && lastRSI > 70) ? 'Overextended — pullback possible' : (score < 0 && lastRSI < 30) ? 'Oversold — bounce possible' : 'Aligns with primary'
    const strength = Math.abs(score) > 35 ? 'Strong' : Math.abs(score) > 15 ? 'Moderate' : 'Weak'
    const momentum = score > 0 ? 'Increasing' : 'Decreasing'
    const confidence = Math.min(Math.abs(score) + 52, 96)
    const risk = Math.abs(score) > 30 ? 'Low' : 'Medium'

    return {
      ...buildResult({ trend: primaryTrend, strength, momentum, confidence, risk, factors, score, label: '2M' }),
      secondaryTrend,
      reversalProbability: reversalProb,
    }
  }

  // ─────────────────────────────────────────────
  // Shared result builder
  // ─────────────────────────────────────────────
  function buildResult({ trend, strength, momentum, confidence, risk, factors, score, label, breakoutProb, breakdownProb }) {
    const isBullish = trend === 'Bullish' || trend === 'Strong Bullish'
    const atr = lastATR

    // Entry/SL/Target logic adapted to trend
    let entryZone, stopLoss, target
    let bias = 'Wait'

    if (isBullish && pivots) {
      entryZone = pivots.r1
      stopLoss = pivots.s1
      target = pivots.r2
      bias = 'Buy'
    } else if (trend === 'Bearish' || trend === 'Strong Bearish') {
      if (pivots) {
        entryZone = pivots.s1
        stopLoss = pivots.r1
        target = pivots.s2
      }
      bias = 'Sell'
    } else {
      // Sideways / Neutral: use nearest S/R
      entryZone = lastClose
      stopLoss = lastClose - atr * 1.5
      target = lastClose + atr * 1.5
    }

    // Normalize numbers
    const fmt = (v) => v != null ? roundTo(v, 2) : null

    const explanation = factors.join('. ') + '.'

    return {
      direction: trend === 'Strong Bullish' ? 'BULLISH' : trend === 'Strong Bearish' ? 'BEARISH' : trend === 'Bullish' ? 'BULLISH' : trend === 'Bearish' ? 'BEARISH' : 'SIDEWAYS',
      trendLabel: trend,
      trendStrength: strength,
      momentum,
      confidence: Math.round(confidence),
      riskLevel: risk,
      buyEntry: bias === 'Buy' ? fmt(entryZone) : null,
      sellEntry: bias === 'Sell' ? fmt(entryZone) : null,
      stopLoss: fmt(stopLoss),
      target1: fmt(target),
      target2: fmt(target * (isBullish ? 1.02 : 0.98)),
      supportLevels: pivots ? [fmt(pivots.s3), fmt(pivots.s2), fmt(pivots.s1)] : [fmt(winLow)],
      resistanceLevels: pivots ? [fmt(pivots.r1), fmt(pivots.r2), fmt(pivots.r3)] : [fmt(winHigh)],
      breakoutProbability: breakoutProb != null ? Math.round(breakoutProb) : score > 0 ? Math.min(score + 45, 85) : Math.max(score + 50, 10),
      breakdownProbability: breakdownProb != null ? Math.round(breakdownProb) : score < 0 ? Math.min(-score + 45, 85) : Math.max(-score + 50, 10),
      suggestedBias: bias,
      suggestedEntryZone: fmt(entryZone),
      suggestedStopLoss: fmt(stopLoss),
      suggestedTarget: fmt(target),
      rsi: roundTo(lastRSI, 1),
      atr: roundTo(atr, 2),
      adx: roundTo(lastADX, 1),
      notes: explanation,
      predictedHigh: fmt(isBullish ? lastClose + atr * 1.2 : lastClose + atr * 0.3),
      predictedLow: fmt(isBullish ? lastClose - atr * 0.3 : lastClose - atr * 1.2),
      predictedClose: fmt(isBullish ? lastClose + atr * 0.6 : lastClose - atr * 0.6),
      fibonacciLevels: { fib0236: fibLevels['0.236'], fib0382: fibLevels['0.382'], fib0500: fibLevels['0.500'], fib0618: fibLevels['0.618'], fib0786: fibLevels['0.786'] },
      vwap,
      patterns: { doji, hammer, shootingStar, bullishEngulfing, bearishEngulfing },
      buyScenario: pivots && (isBullish || trend === 'Sideways') ? {
        entry: fmt(pivots.r1), stopLoss: fmt(pivots.s1 || lastClose - atr * 1.5),
        target1: fmt(pivots.r2), target2: fmt(pivots.r3),
        trigger: 'Price breaks above R1 with volume',
      } : null,
      sellScenario: pivots && (!isBullish) ? {
        entry: fmt(pivots.s1), stopLoss: fmt(pivots.r1 || lastClose + atr * 1.5),
        target1: fmt(pivots.s2), target2: fmt(pivots.s3),
        trigger: 'Price breaks below S1 with volume',
      } : null,
      _windowLabel: label,
      _score: score,
      _pricePosition: roundTo(pricePosition, 1),
    }
  }
}

export function generateAIPrediction(data, windowLabel) {
  return runPrediction(data, windowLabel) || {
    direction: 'SIDEWAYS', trendLabel: 'Neutral', trendStrength: 'Weak', momentum: 'Flat',
    confidence: 0, riskLevel: 'Medium',
    buyEntry: null, sellEntry: null, stopLoss: null, target1: null, target2: null,
    supportLevels: [], resistanceLevels: [],
    breakoutProbability: 0, breakdownProbability: 0,
    suggestedBias: 'Wait', suggestedEntryZone: null, suggestedStopLoss: null, suggestedTarget: null,
    notes: 'Insufficient data for analysis. Need at least 3 trading days.',
    predictedHigh: null, predictedLow: null, predictedClose: null, rsi: null, atr: null, adx: null,
    buyScenario: null, sellScenario: null,
    _windowLabel: windowLabel,
  }
}

export function generateForecastData(data, prediction) {
  if (!data || data.length < 3 || !prediction) return []
  const last3 = data.slice(-3).map(d => ({ date: d.Date, close: d.Close, high: d.High, low: d.Low, isForecast: false }))
  const lastDate = new Date(data[data.length - 1].Date)
  const nextDate = new Date(lastDate)
  nextDate.setDate(nextDate.getDate() + 1)
  while (nextDate.getDay() === 0 || nextDate.getDay() === 6) nextDate.setDate(nextDate.getDate() + 1)
  const lastClose = data[data.length - 1].Close
  // Insert a null gap so the forecast line doesn't connect to actual data
  const gap = { date: '', close: null, high: null, low: null, isForecast: false }
  return [...last3, gap, {
    date: nextDate.toISOString().split('T')[0],
    close: prediction.predictedClose || lastClose,
    high: prediction.predictedHigh || lastClose * 1.01,
    low: prediction.predictedLow || lastClose * 0.99,
    isForecast: true,
  }]
}
