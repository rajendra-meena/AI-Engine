/**
 * Subscription manager — batches subscriptions, tracks state, auto-resubscribes.
 */

// eslint-disable-next-line @typescript-eslint/no-explicit-any
export type Subscriber = (msg: any) => void

interface SubscriptionEntry {
  channels: Set<string>
  symbols: Set<string>
  handler: Subscriber
}

export class SubscriptionManager {
  private _subscriptions: Map<string, SubscriptionEntry> = new Map()
  private _pendingQueue: Array<{ action: "subscribe" | "unsubscribe"; channels: string[]; symbols: string[] }> = []
  private _ws: () => WebSocket | null
  private _sendTimer: ReturnType<typeof setTimeout> | null = null
  private _batchDelay = 100 // ms

  constructor(ws: () => WebSocket | null) {
    this._ws = ws
  }

  subscribe(id: string, channels: string[], symbols: string[], handler: Subscriber) {
    this._subscriptions.set(id, {
      channels: new Set(channels),
      symbols: new Set(symbols),
      handler,
    })
    this._enqueue("subscribe", channels, symbols)
  }

  unsubscribe(id: string) {
    const entry = this._subscriptions.get(id)
    if (entry) {
      this._subscriptions.delete(id)
      this._enqueue("unsubscribe", [...entry.channels], [...entry.symbols])
    }
  }

  getHandler(type: string): Subscriber | undefined {
    for (const entry of this._subscriptions.values()) {
      if (entry.channels.has(type) || entry.channels.has("*")) {
        return entry.handler
      }
    }
    return undefined
  }

  resubscribeAll() {
    const channels = new Set<string>()
    const symbols = new Set<string>()
    for (const entry of this._subscriptions.values()) {
      entry.channels.forEach((c) => channels.add(c))
      entry.symbols.forEach((s) => symbols.add(s))
    }
    if (channels.size > 0 || symbols.size > 0) {
      this._send({ action: "subscribe", channels: [...channels], symbols: [...symbols] })
    }
  }

  private _enqueue(action: "subscribe" | "unsubscribe", channels: string[], symbols: string[]) {
    this._pendingQueue.push({ action, channels, symbols })
    if (!this._sendTimer) {
      this._sendTimer = setTimeout(() => this._flush(), this._batchDelay)
    }
  }

  private _flush() {
    this._sendTimer = null
    if (this._pendingQueue.length === 0) return

    // Merge: take the latest action for each channel/symbol pair
    const subscribeChs = new Set<string>()
    const subscribeSyms = new Set<string>()

    for (const item of this._pendingQueue) {
      if (item.action === "subscribe") {
        item.channels.forEach((c) => subscribeChs.add(c))
        item.symbols.forEach((s) => subscribeSyms.add(s))
      }
    }

    this._pendingQueue = []
    this._send({ action: "subscribe", channels: [...subscribeChs], symbols: [...subscribeSyms] })
  }

  private _send(msg: { action: string; channels: string[]; symbols: string[] }) {
    const ws = this._ws()
    if (ws && ws.readyState === WebSocket.OPEN) {
      ws.send(JSON.stringify({
        type: msg.action === "subscribe" ? "subscribe" : "unsubscribe",
        payload: { channels: msg.channels, symbols: msg.symbols },
      }))
    }
  }
}
