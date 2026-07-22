/**
 * Event dispatcher — routes backend events to registered consumers.
 * Supports wildcard matching and sequence deduplication.
 */

import type { WSMessage } from "@/types/websocket"

type EventHandler = (msg: WSMessage) => void

export class EventDispatcher {
  private _handlers: Map<string, Set<EventHandler>> = new Map()
  private _seenIds: Set<string> = new Set()
  private _maxSeenIds = 500

  on(type: string, handler: EventHandler) {
    if (!this._handlers.has(type)) {
      this._handlers.set(type, new Set())
    }
    this._handlers.get(type)!.add(handler)
    return () => this.off(type, handler)
  }

  off(type: string, handler: EventHandler) {
    this._handlers.get(type)?.delete(handler)
  }

  dispatch(msg: WSMessage) {
    if (msg.id) {
      if (this._seenIds.has(msg.id)) return
      this._seenIds.add(msg.id)
      if (this._seenIds.size > this._maxSeenIds) {
        const iter = this._seenIds.values().next()
        if (iter.value) this._seenIds.delete(iter.value)
      }
    }
    this._callHandlers(msg.type, msg)
    this._callHandlers("*", msg)
  }

  private _callHandlers(type: string, msg: WSMessage) {
    const handlers = this._handlers.get(type)
    if (handlers) {
      handlers.forEach((h) => {
        try { h(msg) } catch { /* isolate handler errors */ }
      })
    }
  }
}
