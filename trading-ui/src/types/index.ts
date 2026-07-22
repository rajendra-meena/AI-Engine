export interface Candle {
  time: string
  open: number
  high: number
  low: number
  close: number
  volume: number
}

export interface DailyCandle {
  Date: string
  Open: number
  High: number
  Low: number
  Close: number
  Volume: number
}

export interface DailyRefs {
  prevDayHigh: number
  prevDayLow: number
  prevDayClose: number
  prevDayOpen: number
  weeklyHigh: number
  weeklyLow: number
  prevDayRange: number
  prevDayMidpoint: number
  prevDayVWAP: number
}

export interface MarketDataResponse {
  symbol: string
  candles: Candle[]
  dailyRefs: DailyRefs | null
  cached: boolean
  cache_size: number
}

export interface DailyDataResponse {
  symbol: string
  data: DailyCandle[]
  error?: string
}

export interface Prediction {
  id: number
  symbol: string
  interval: string
  predicted_date: string
  direction: string
  confidence: number | null
  suggested_bias: string | null
  entry_zone: number | null
  stop_loss: number | null
  target: number | null
  status: string
  created_at: string
  notes: string | null
}

export interface PredictionStats {
  total_predictions: number
  total_checked: number
  hit_rate: number
  stoploss_rate: number
  no_trade_rate: number
  average_confidence: number | null
}

export interface ProviderStatus {
  provider: string
  type: string
  status: string
  last_success: string | null
  supported_symbols: string[]
  supported_intervals: string[]
}

// ── Overlay Types ──

export interface OverlaySeriesPoint {
  time: string
  value: number
}

export interface OverlaySeries {
  id: string
  label: string
  color: string
  lineStyle?: "solid" | "dashed" | "dotted"
  lineWidth?: number
  data: OverlaySeriesPoint[]
  visible?: boolean
}

export interface OverlayZone {
  id: string
  label: string
  top: number
  bottom: number
  color: string
  borderColor?: string
  time: string
  type: "supply" | "demand" | "liquidity" | "zone"
  visible?: boolean
}

export interface OverlayTrendLine {
  id: string
  label: string
  x1: string
  y1: number
  x2: string
  y2: number
  color: string
  lineStyle?: "solid" | "dashed" | "dotted"
  lineWidth?: number
  visible?: boolean
}

export interface OverlayLabel {
  id: string
  time: string
  price: number
  text: string
  color: string
  position: "above" | "below" | "left" | "right"
  size?: "sm" | "md" | "lg"
}

// ── Pattern Types ──

export interface CandlestickPattern {
  name: string
  direction: "bullish" | "bearish"
  confidence: number
  strength?: string
}

export interface ChartPattern {
  name: string
  direction: "bullish" | "bearish"
  confidence: number
  price: number
  target?: number
}

export interface BreakoutPattern {
  name: string
  direction: "bullish" | "bearish"
  confidence: number
  price: number
  volume_confirmed?: boolean
}

// ── Liquidity Types ──

export interface LiquidityLevel {
  price: number
  type: "equal_high" | "equal_low" | "swept_high" | "swept_low" | "liquidity_zone"
  strength: number
  label: string
  time: string
}

// ── AI Decision Overlay Types ──

export interface AIOverlayData {
  bias: "bullish" | "bearish" | "neutral"
  score: number
  confidence: number
  entry_zone: { top: number; bottom: number } | null
  stoploss: number | null
  targets: number[]
  risk_reward: number | null
  decision: string
  reasoning: string[]
}

// ── Indicator Series Data (full time series for chart overlay) ──

export interface IndicatorSeriesData {
  id: string
  label: string
  color: string
  lineStyle: "solid" | "dashed" | "dotted"
  lineWidth: number
  data: OverlaySeriesPoint[]
  visible?: boolean
}

// ── Zone Rectangle (price zone spanning time) ──

export interface ZoneRectData {
  id: string
  label: string
  top: number
  bottom: number
  color: string
  borderColor?: string
  time: string
  visible?: boolean
}

// ── Trend Line (connecting swing points) ──

export interface TrendLinePoint {
  time: string
  price: number
}

export interface TrendLineData {
  id: string
  label: string
  points: [TrendLinePoint, TrendLinePoint]
  color: string
  lineStyle: "solid" | "dashed" | "dotted"
  lineWidth: number
  visible?: boolean
}

// ── Indicator Compute Result (client-side) ──

export interface ComputedIndicator {
  id: string
  label: string
  color: string
  values: (number | null)[]
}

// ── Zone Fill (filled rectangle region) ──

export interface ChartZone {
  id: string
  time: string
  top: number
  bottom: number
  color: string
  borderColor?: string
  label: string
  visible?: boolean
}

// ── WebSocket Overlay Events ──

export interface WSOverlayUpdate {
  type: "overlay_update"
  channel: "indicators" | "structure" | "patterns" | "sr" | "liquidity" | "ai"
  symbol: string
  payload: Record<string, unknown>
}
