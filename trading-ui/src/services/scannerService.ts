/**
 * scannerService.ts
 *
 * Institutional Market Scanner — aggregates data from existing backend APIs
 * to build a real-time market watchlist with AI-powered scoring.
 *
 * NO mock data. Every field comes from real backend endpoints.
 */

import { marketService } from "./marketService"
import { decisionService } from "./decisionService"
import { structureService } from "./structureService"
import { indicatorService } from "./indicatorService"
import { patternService } from "./patternService"
import { srService } from "./srService"
import { mtfService } from "./mtfService"
import type { ScannerRow } from "@/store/useScannerStore"
import type { Candle } from "@/types"

/* ─── Supported scan symbols ─── */

export const SCAN_SYMBOLS = ["NIFTY 50", "BANK NIFTY", "SENSEX", "FIN NIFTY", "MIDCP NIFTY"]

/* ─── Scanner Service ─── */

export const scannerService = {
  /**
   * Scan all configured symbols and produce ScannerRow[].
   * Each symbol is scanned independently using existing backend APIs.
   */
  async scanAll(interval = "15m"): Promise<ScannerRow[]> {
    const results: ScannerRow[] = []

    for (const symbol of SCAN_SYMBOLS) {
      try {
        const row = await this.scanSymbol(symbol, interval)
        results.push(row)
      } catch {
        // Skip symbols that fail to scan
      }
    }

    return results.sort((a, b) => b.score - a.score)
  },

  /**
   * Scan a single symbol — fetches data from all engines and composes a row.
   */
  async scanSymbol(symbol: string, interval = "15m"): Promise<ScannerRow> {
    const [marketData, decision, structure, , pattern, sr, mtf] = await Promise.all([
      this._safeFetch(() => marketService.getIntraday(symbol, interval, 1)),
      this._safeFetch(() => decisionService.getLatest(symbol)),
      this._safeFetch(() => structureService.getLatest(symbol, interval)),
      this._safeFetch(() => indicatorService.getLatest(symbol, interval)),
      this._safeFetch(() => patternService.getLatest(symbol, interval)),
      this._safeFetch(() => srService.getLatest(symbol)),
      this._safeFetch(() => mtfService.getLatest(symbol)),
    ])

    const candles: Candle[] = marketData?.candles ?? []
    const lastCandle = candles[candles.length - 1]
    const price = lastCandle?.close ?? 0
    const prevCandle = candles[candles.length - 2]
    const change = prevCandle ? ((price - prevCandle.close) / prevCandle.close) * 100 : 0
    const volume = lastCandle?.volume ?? 0

    const score = decision?.score ?? 0
    const confidence = decision?.confidence ?? 0
    const risk = decision?.risk_level ?? "MEDIUM"
    const plan = decision?.trade_plan ?? {}
    const rr = this._computeRR(plan)
    const decisionText = decision?.decision ?? "NO_TRADE"

    const trend = structure?.trend ?? "RANGING"
    const bias = mtf?.institutional_bias ?? (score >= 60 ? "BULLISH" : score <= 40 ? "BEARISH" : "NEUTRAL")
    const alignment = mtf?.alignment_level ?? "NEUTRAL"
    const patternName = pattern?.strongest_pattern ?? null

    const nearestSupport = sr?.nearest_support ?? null
    const nearestResistance = sr?.nearest_resistance ?? null
    const supportDist = nearestSupport != null && price > 0 ? ((price - nearestSupport) / price) * 100 : null
    const resistanceDist = nearestResistance != null && price > 0 ? ((nearestResistance - price) / price) * 100 : null

    const rank = this._computeRank(score, confidence, risk, rr)

    return {
      symbol,
      price,
      change,
      volume,
      trend,
      score,
      confidence,
      risk,
      rr,
      institutionalBias: bias,
      mtfAlignment: alignment,
      supportDistance: supportDist ? Math.round(supportDist * 100) / 100 : null,
      resistanceDistance: resistanceDist ? Math.round(resistanceDist * 100) / 100 : null,
      pattern: patternName,
      decision: decisionText,
      lastUpdate: new Date().toISOString(),
      rank,
    }
  },

  /** Compute a simple risk-reward ratio from the trade plan. */
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  _computeRR(plan: any): number {
    if (!plan?.valid) return 0
    const entry = plan.entry_zone?.price ?? plan.entry_zone?.top ?? 0
    const sl = plan.sl_zone?.price ?? 0
    const target = plan.target_zones?.[0]?.price ?? 0
    if (!entry || !sl || !target) return 0
    const risk = Math.abs(entry - sl)
    const reward = Math.abs(target - entry)
    return risk > 0 ? Math.round((reward / risk) * 10) / 10 : 0
  },

  /** Compute a 1-5 rank from score/confidence/risk/rr. */
  _computeRank(score: number, confidence: number, risk: string, rr: number): number {
    let stars = 0
    if (score >= 80) stars += 2
    else if (score >= 60) stars += 1
    if (confidence >= 80) stars += 1
    else if (confidence >= 60) stars += 0.5
    if (rr >= 2) stars += 1
    else if (rr >= 1) stars += 0.5
    if (risk === "LOW") stars += 1
    else if (risk === "MEDIUM") stars += 0.5
    else if (risk === "EXTREME") stars -= 0.5
    return Math.max(1, Math.min(5, Math.round(stars)))
  },

  /** Safely fetch data — returns null on failure instead of throwing. */
  async _safeFetch<T>(fn: () => Promise<T>): Promise<T | null> {
    try {
      return await fn()
    } catch {
      return null
    }
  },
}
