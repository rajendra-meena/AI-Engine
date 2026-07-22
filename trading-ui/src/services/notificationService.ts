/**
 * notificationService.ts
 *
 * Maps backend WebSocket events to structured AppNotification objects.
 *
 * Every event type from the backend Event Bus is consumed and translated
 * into a typed notification with appropriate category, priority, and message.
 *
 * NO mock data — all events originate from the live WebSocket connection.
 */

import type { AppNotification, NotificationCategory, NotificationPriority } from "@/store/useNotificationStore"

/* ─── Event to Notification mapping ─── */

export interface BackendEventMap {
  type: string
  payload?: Record<string, unknown>
}

function getCategory(type: string): NotificationCategory {
  if (type.startsWith("ai_")) return "ai"
  if (type.startsWith("indicator")) return "indicators"
  if (type.startsWith("structure") || type.includes("bos") || type.includes("choch")) return "structure"
  if (type.startsWith("pattern") || type.includes("pattern")) return "patterns"
  if (type.startsWith("sr_") || type.includes("supply") || type.includes("demand")) return "sr"
  if (type.startsWith("replay")) return "replay"
  if (type.startsWith("portfolio") || type.includes("trade") || type.includes("order")) return "portfolio"
  if (type.startsWith("scanner")) return "scanner"
  if (type.includes("error") || type.includes("fail")) return "errors"
  if (type.includes("warn")) return "warnings"
  return "system"
}

function getPriority(type: string): NotificationPriority {
  if (type.includes("critical") || type.includes("error") || type === "connection_lost") return "CRITICAL"
  if (type.includes("warn") || type.includes("fail") || type.includes("stop") || type.includes("sweep")) return "WARNING"
  if (type.includes("finished") || type.includes("closed") || type.includes("hit") || type.includes("started") || type.includes("resumed")) return "SUCCESS"
  return "INFO"
}

function formatTitle(type: string): string {
  return type
    .replace(/_/g, " ")
    .replace(/\b\w/g, (c) => c.toUpperCase())
}

function formatMessage(type: string, payload?: Record<string, unknown>): string {
  if (!payload) return `${formatTitle(type)} event received`

  const symbol = payload.symbol as string | undefined
  const score = payload.score as number | undefined
  const decision = payload.decision as string | undefined

  if (type === "ai_decision_updated") return `AI Decision: ${decision || "Updated"}${score != null ? ` (Score: ${score})` : ""}`
  if (type === "indicator_updated") return `Indicators updated for ${symbol || "market"}`
  if (type === "structure_updated") return `Market structure updated${symbol ? ` for ${symbol}` : ""}`
  if (type === "bos_detected") return `BOS detected${symbol ? ` on ${symbol}` : ""}`
  if (type === "choch_detected") return `CHoCH detected${symbol ? ` on ${symbol}` : ""}`
  if (type === "pattern_detected") return `Pattern detected by AI engine`
  if (type === "liquidity_sweep") return `Liquidity sweep${symbol ? ` on ${symbol}` : ""}`
  if (type === "sr_supply_zone_created") return `Supply zone identified${symbol ? ` for ${symbol}` : ""}`
  if (type === "sr_demand_zone_created") return `Demand zone identified${symbol ? ` for ${symbol}` : ""}`
  if (type === "replay_started") return `Replay session started — ${payload.total_candles || "?"} candles`
  if (type === "replay_finished") return `Replay finished after ${payload.total_candles || "?"} candles`
  if (type === "replay_paused") return `Replay paused at ${payload.progress_percent || 0}%`
  if (type === "replay_resumed") return `Replay resumed`
  if (type === "connection_lost") return `WebSocket connection lost — reconnecting...`
  if (type === "connection_restored") return `WebSocket connection restored`
  if (type === "scanner_alert") return `Scanner alert triggered for ${symbol || "symbol"}`
  if (type === "trade_executed") return `Trade executed: ${payload.side || ""} ${symbol || ""}`
  if (type === "position_closed") return `Position closed: ${symbol || ""} ${payload.pnl != null ? `PnL: ${(payload.pnl as number).toFixed(2)}` : ""}`

  return `${formatTitle(type)}${symbol ? ` — ${symbol}` : ""}`
}

export const notificationService = {
  /**
   * Convert a raw backend event into an AppNotification.
   */
  eventToNotification(event: { type: string; payload?: Record<string, unknown> }): Omit<AppNotification, "id" | "timestamp" | "read" | "dismissed"> {
    return {
      title: formatTitle(event.type),
      message: formatMessage(event.type, event.payload),
      category: getCategory(event.type),
      priority: getPriority(event.type),
      source: event.type,
    }
  },

  /**
   * Generate a notification directly from a known event type + payload.
   * Used for synthetic events (connection status, etc.).
   */
  createNotification(
    type: string,
    payload?: Record<string, unknown>,
  ): Omit<AppNotification, "id" | "timestamp" | "read" | "dismissed"> {
    return this.eventToNotification({ type, payload })
  },
}
