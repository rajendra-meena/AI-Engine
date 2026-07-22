/**
 * paperTradingService.ts
 *
 * Institutional Paper Trading Engine.
 *
 * Simulates order execution, position management, PnL calculation, and risk
 * management using real market data from existing backend APIs.
 *
 * NO mock data — all prices and decisions come from live backend endpoints.
 */

import type { Order, OrderSide, OrderType, Position } from "@/store/usePortfolioStore"
import { marketService } from "./marketService"

let _orderIdCounter = 0
const nextId = () => `order_${++_orderIdCounter}_${Date.now()}`
const posId = () => `pos_${Date.now()}_${Math.random().toString(36).slice(2, 6)}`

export interface OrderRequest {
  symbol: string
  side: OrderSide
  type: OrderType
  quantity: number
  price?: number
  stopPrice?: number
  stopLoss?: number
  takeProfit?: number
}

export interface ExecutionResult {
  success: boolean
  order?: Order
  position?: Position
  error?: string
}

export const paperTradingService = {
  /**
   * Execute a paper order using real market prices from the backend.
   */
  async executeOrder(request: OrderRequest): Promise<ExecutionResult> {
    // Fetch current market price
    let marketPrice = 0
    try {
      const data = await marketService.getIntraday(request.symbol, "1m", 1)
      const candles = data.candles ?? []
      const last = candles[candles.length - 1]
      marketPrice = last?.close ?? 0
    } catch {
      return { success: false, error: `Failed to fetch price for ${request.symbol}` }
    }

    if (marketPrice <= 0) {
      return { success: false, error: `No market data for ${request.symbol}` }
    }

    const order: Order = {
      id: nextId(),
      symbol: request.symbol,
      side: request.side,
      type: request.type,
      quantity: request.quantity,
      price: request.price ?? null,
      stopPrice: request.stopPrice ?? null,
      status: "filled",
      filledQty: request.quantity,
      avgFillPrice: marketPrice,
      createdAt: new Date().toISOString(),
      filledAt: new Date().toISOString(),
      stopLoss: request.stopLoss ?? null,
      takeProfit: request.takeProfit ?? null,
    }

    // Build the position from the filled order
    const direction = request.side === "buy" ? "LONG" : "SHORT"
    const targets = request.takeProfit ? [request.takeProfit] : []

    const position: Position = {
      id: posId(),
      symbol: request.symbol,
      direction,
      entry: marketPrice,
      currentPrice: marketPrice,
      quantity: request.quantity,
      pnl: 0,
      pnlPercent: 0,
      rr: 0,
      aiScore: null,
      aiConfidence: null,
      risk: null,
      status: "open",
      trailingStop: null,
      targets,
      partialExit: null,
      openedAt: new Date().toISOString(),
      closedAt: null,
      reason: null,
    }

    return { success: true, order, position }
  },

  /**
   * Calculate current PnL for a position using latest market price.
   */
  async calculatePnL(position: Position): Promise<{ pnl: number; pnlPercent: number; currentPrice: number }> {
    try {
      const data = await marketService.getIntraday(position.symbol, "1m", 1)
      const candles = data.candles ?? []
      const last = candles[candles.length - 1]
      const currentPrice = last?.close ?? position.currentPrice

      const priceDiff = position.direction === "LONG"
        ? currentPrice - position.entry
        : position.entry - currentPrice

      const pnl = priceDiff * position.quantity
      const pnlPercent = position.entry > 0 ? (priceDiff / position.entry) * 100 : 0

      return { pnl, pnlPercent, currentPrice }
    } catch {
      return { pnl: position.pnl, pnlPercent: position.pnlPercent, currentPrice: position.currentPrice }
    }
  },

  /**
   * Close a position at market price.
   */
  // eslint-disable-next-line @typescript-eslint/no-unused-vars
  async closePosition(position: Position, _reason = "manual"): Promise<{ exitPrice: number; pnl: number }> {
    try {
      const data = await marketService.getIntraday(position.symbol, "1m", 1)
      const candles = data.candles ?? []
      const last = candles[candles.length - 1]
      const exitPrice = last?.close ?? position.currentPrice

      const priceDiff = position.direction === "LONG"
        ? exitPrice - position.entry
        : position.entry - exitPrice

      const pnl = priceDiff * position.quantity
      return { exitPrice, pnl }
    } catch {
      return { exitPrice: position.currentPrice, pnl: position.pnl }
    }
  },

  /**
   * Modify stop loss for a position.
   */
  modifyStopLoss(position: Position, newStopLoss: number): Partial<Position> {
    return { trailingStop: newStopLoss }
  },

  /**
   * Move stop loss to break even.
   */
  moveToBreakEven(position: Position): Partial<Position> {
    return { trailingStop: position.entry }
  },

  /**
   * Set trailing stop loss based on a fixed percentage distance.
   */
  setTrailingStop(position: Position, trailPercent: number, currentPrice: number): Partial<Position> {
    const distance = currentPrice * (trailPercent / 100)
    const stop = position.direction === "LONG" ? currentPrice - distance : currentPrice + distance
    return { trailingStop: stop }
  },
}
