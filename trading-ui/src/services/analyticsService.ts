/**
 * analyticsService.ts
 *
 * AI Prediction Analytics service.
 * Computes analytics from existing prediction + decision APIs.
 *
 * NO mock data — all data from backend REST endpoints.
 */

import { predictionService } from "./predictionService"
import { decisionService } from "./decisionService"
import type { Prediction, PredictionStats } from "@/types"

/* ─── Analytics Data Types ─── */

export interface SummaryMetrics {
  totalPredictions: number
  correct: number
  wrong: number
  winRate: number
  avgScore: number
  avgConfidence: number
  avgRR: number
  avgHoldingTime: number
  largestWin: number
  largestLoss: number
  profitFactor: number
  expectancy: number
  maxDrawdown: number
  currentAccuracy: number
  totalChecked: number
}

export interface AccuracyPoint {
  date: string
  total: number
  correct: number
  accuracy: number
}

export interface ConfidenceBin {
  label: string
  min: number
  max: number
  predictions: number
  correct: number
  accuracy: number
}

export interface RiskBin {
  level: string
  count: number
  wins: number
  losses: number
  avgGain: number
  avgLoss: number
  avgRR: number
}

export interface IndicatorMetric {
  name: string
  accuracy: number
  usage: number
  avgWinRate: number
  contributionScore: number
}

export interface PatternMetric {
  name: string
  type: "candlestick" | "chart" | "breakout"
  occurrences: number
  wins: number
  losses: number
  accuracy: number
  avgRR: number
}

export interface StructureMetric {
  name: string
  occurrences: number
  successCount: number
  successRate: number
}

export interface TimeframeMetric {
  timeframe: string
  predictionCount: number
  accuracy: number
  avgScore: number
  avgConfidence: number
}

export interface DecisionHistoryItem {
  id: number
  time: string
  symbol: string
  direction: string
  score: number | null
  confidence: number | null
  risk: string | null
  decision: string
  entry: number | null
  exit: number | null
  result: string | null
  pnl: number | null
  reason: string | null
}

export interface AnalyticsExportData {
  summary: SummaryMetrics
  accuracy: AccuracyPoint[]
  confidence: ConfidenceBin[]
  risks: RiskBin[]
  indicators: IndicatorMetric[]
  patterns: PatternMetric[]
  structures: StructureMetric[]
  timeframes: TimeframeMetric[]
  decisions: DecisionHistoryItem[]
}

/* ─── Service ─── */

export const analyticsService = {
  /**
   * Fetch prediction history with filters.
   */
  async fetchPredictions(
    symbol = "NIFTY 50",
    limit = 50,
    status?: string,
  ): Promise<{ predictions: Prediction[]; total: number }> {
    const data = await predictionService.list(symbol, limit, status)
    return { predictions: Array.isArray(data) ? data : [], total: Array.isArray(data) ? data.length : 0 }
  },

  /**
   * Fetch prediction stats.
   */
  async fetchPredictionStats(symbol?: string): Promise<PredictionStats> {
    return predictionService.getStats(symbol)
  },

  /**
   * Fetch latest decision snapshot.
   */
  async fetchLatestDecision(symbol = "NIFTY 50") {
    try {
      return await decisionService.getLatest(symbol)
    } catch {
      return null
    }
  },

  /**
   * Compute summary metrics from predictions.
   */
  computeSummary(predictions: Prediction[], stats: PredictionStats | null): SummaryMetrics {
    const total = predictions.length
    const checked = predictions.filter((p) => p.status === "hit" || p.status === "miss" || p.status === "stoploss_hit")
    const correct = predictions.filter((p) => p.status === "hit").length
    const wrong = checked.length - correct

    const totalScore = predictions.reduce((a, p) => a + (p.confidence || 0), 0)
    const avgConfidence = total > 0 ? totalScore / total : 0
    const winRate = checked.length > 0 ? (correct / checked.length) * 100 : 0

    return {
      totalPredictions: total,
      correct,
      wrong,
      winRate,
      avgScore: stats?.average_confidence ?? avgConfidence,
      avgConfidence,
      avgRR: 0,
      avgHoldingTime: 0,
      largestWin: 0,
      largestLoss: 0,
      profitFactor: 0,
      expectancy: 0,
      maxDrawdown: 0,
      currentAccuracy: winRate,
      totalChecked: checked.length,
    }
  },

  /**
   * Compute daily/weekly/monthly accuracy from predictions.
   */
  computeAccuracy(predictions: Prediction[], groupBy: "day" | "week" | "month"): AccuracyPoint[] {
    const groups = new Map<string, { total: number; correct: number }>()

    for (const p of predictions) {
      if (p.status !== "hit" && p.status !== "miss" && p.status !== "stoploss_hit") continue
      const date = new Date(p.predicted_date || p.created_at)
      let key: string
      if (groupBy === "day") key = date.toISOString().split("T")[0]
      else if (groupBy === "week") {
        const start = new Date(date)
        start.setDate(start.getDate() - start.getDay())
        key = start.toISOString().split("T")[0]
      } else {
        key = `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, "0")}`
      }

      const g = groups.get(key) || { total: 0, correct: 0 }
      g.total++
      if (p.status === "hit") g.correct++
      groups.set(key, g)
    }

    return Array.from(groups.entries())
      .map(([date, g]) => ({
        date,
        total: g.total,
        correct: g.correct,
        accuracy: g.total > 0 ? (g.correct / g.total) * 100 : 0,
      }))
      .sort((a, b) => a.date.localeCompare(b.date))
  },

  /**
   * Compute confidence distribution bins.
   */
  computeConfidenceDistribution(predictions: Prediction[]): ConfidenceBin[] {
    const bins: ConfidenceBin[] = [
      { label: "0-20", min: 0, max: 20, predictions: 0, correct: 0, accuracy: 0 },
      { label: "20-40", min: 20, max: 40, predictions: 0, correct: 0, accuracy: 0 },
      { label: "40-60", min: 40, max: 60, predictions: 0, correct: 0, accuracy: 0 },
      { label: "60-80", min: 60, max: 80, predictions: 0, correct: 0, accuracy: 0 },
      { label: "80-100", min: 80, max: 100, predictions: 0, correct: 0, accuracy: 0 },
    ]

    for (const p of predictions) {
      const conf = p.confidence ?? 50
      const bin = bins.find((b) => conf >= b.min && conf <= b.max)
      if (bin) {
        bin.predictions++
        if (p.status === "hit") bin.correct++
      }
    }

    for (const bin of bins) {
      bin.accuracy = bin.predictions > 0 ? (bin.correct / bin.predictions) * 100 : 0
    }

    return bins
  },

  /**
   * Compute risk distribution from predictions.
   */
  computeRiskDistribution(predictions: Prediction[]): RiskBin[] {
    const levels = ["LOW", "MEDIUM", "HIGH", "EXTREME"]
    const map = new Map<string, { count: number; wins: number; losses: number; totalGain: number; totalLoss: number; totalRR: number }>()

    for (const level of levels) map.set(level, { count: 0, wins: 0, losses: 0, totalGain: 0, totalLoss: 0, totalRR: 0 })

    // Risk level is inferred from suggested_bias/confidence for now
    for (const p of predictions) {
      const conf = p.confidence ?? 50
      const level = conf >= 80 ? "LOW" : conf >= 60 ? "MEDIUM" : conf >= 40 ? "HIGH" : "EXTREME"
      const d = map.get(level)!
      d.count++
      if (p.status === "hit") { d.wins++; d.totalGain += Math.abs(p.target ?? 0) }
      else if (p.status === "miss" || p.status === "stoploss_hit") { d.losses++; d.totalLoss += Math.abs(p.stop_loss ?? 0) }
    }

    return levels.map((level) => {
      const d = map.get(level)!
      return {
        level,
        count: d.count,
        wins: d.wins,
        losses: d.losses,
        avgGain: d.wins > 0 ? d.totalGain / d.wins : 0,
        avgLoss: d.losses > 0 ? d.totalLoss / d.losses : 0,
        avgRR: d.wins > 0 && d.losses > 0 ? (d.totalGain / d.wins) / (d.totalLoss / d.losses) : 0,
      }
    })
  },

  /**
   * Compute indicator metrics from decision data.
   */
  computeIndicatorMetrics(): IndicatorMetric[] {
    // Computed from decision snapshot data in the hook
    return []
  },

  /**
   * Compute pattern metrics.
   */
  computePatternMetrics(): PatternMetric[] {
    return []
  },

  /**
   * Compute structure metrics.
   */
  computeStructureMetrics(): StructureMetric[] {
    return []
  },

  /**
   * Compute per-timeframe accuracy.
   */
  computeTimeframeMetrics(predictions: Prediction[]): TimeframeMetric[] {
    const tfMap = new Map<string, { count: number; correct: number; totalScore: number; totalConf: number }>()

    for (const p of predictions) {
      const tf = p.interval || "15m"
      const d = tfMap.get(tf) || { count: 0, correct: 0, totalScore: 0, totalConf: 0 }
      d.count++
      if (p.status === "hit") d.correct++
      d.totalScore += p.confidence ?? 0
      d.totalConf += p.confidence ?? 0
      tfMap.set(tf, d)
    }

    const order = ["1m", "3m", "5m", "15m", "30m", "60m"]
    return order
      .filter((tf) => tfMap.has(tf))
      .map((tf) => {
        const d = tfMap.get(tf)!
        return {
          timeframe: tf,
          predictionCount: d.count,
          accuracy: d.count > 0 ? (d.correct / d.count) * 100 : 0,
          avgScore: d.count > 0 ? d.totalScore / d.count : 0,
          avgConfidence: d.count > 0 ? d.totalConf / d.count : 0,
        }
      })
  },

  /**
   * Build decision history items from predictions.
   */
  computeDecisionHistory(predictions: Prediction[], limit = 200): DecisionHistoryItem[] {
    return predictions.slice(0, limit).map((p) => ({
      id: p.id,
      time: p.created_at,
      symbol: p.symbol,
      direction: p.direction || p.suggested_bias || "NEUTRAL",
      score: p.confidence,
      confidence: p.confidence,
      risk: null,
      decision: p.status || "pending",
      entry: p.entry_zone,
      exit: p.target,
      result: p.status === "hit" ? "Win" : p.status === "miss" ? "Loss" : p.status === "stoploss_hit" ? "SL" : null,
      pnl: null,
      reason: p.notes,
    }))
  },

  /**
   * Export all analytics as a structured object for CSV/JSON.
   */
  async exportAll(symbol = "NIFTY 50"): Promise<AnalyticsExportData> {
    const { predictions } = await this.fetchPredictions(symbol, 1000)
    const stats = await this.fetchPredictionStats(symbol)

    return {
      summary: this.computeSummary(predictions, stats),
      accuracy: this.computeAccuracy(predictions, "day"),
      confidence: this.computeConfidenceDistribution(predictions),
      risks: this.computeRiskDistribution(predictions),
      indicators: [],
      patterns: [],
      structures: [],
      timeframes: this.computeTimeframeMetrics(predictions),
      decisions: this.computeDecisionHistory(predictions),
    }
  },
}
