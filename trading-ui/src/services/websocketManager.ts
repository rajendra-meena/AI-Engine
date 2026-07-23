/* eslint-disable @typescript-eslint/no-explicit-any */
/**
 * WebSocketManager — single shared production-grade WebSocket connection.
 *
 * Features:
 * - Singleton shared connection
 * - Exponential backoff reconnect (1s → 2s → 4s → 8s → 16s → 30s max)
 * - Heartbeat ping/pong with latency measurement
 * - Message queuing while disconnected
 * - Automatic resubscribe on reconnect
 * - Event dispatching to registered consumers
 * - Connection quality monitoring
 */

import { WS_URL, type WSMessage, type ConnectionState } from "@/types/websocket"
import { EventDispatcher } from "./eventDispatcher"
import { SubscriptionManager } from "./subscriptionManager"
import { HeartbeatManager } from "./heartbeat"
import { ConnectionMonitor } from "./connectionMonitor"

type StateListener = (state: ConnectionState) => void

class WebSocketManager {
  private _ws: WebSocket | null = null
  private _dispatcher = new EventDispatcher()
  private _subscriptions: SubscriptionManager
  private _heartbeat: HeartbeatManager
  private _monitor = new ConnectionMonitor()
  private _stateListeners: Set<StateListener> = new Set()
  private _messageQueue: string[] = []
  private _connectTimer: ReturnType<typeof setTimeout> | null = null
  private _destroyed = false

  // Backend event consumers — keyed by event type
  private _consumers: Map<string, Set<(payload: any) => void>> = new Map()

  constructor() {
    this._subscriptions = new SubscriptionManager(() => this._ws)
    this._heartbeat = new HeartbeatManager(
      () => this._ws,
      (latency) => this._emit("latency", latency),
      () => this._reconnect("Pong timeout")
    )
    this._monitor.onReconnect((event) => this._emit("reconnect", event))
    this._connect()
  }

  // ── Connection ──

  private _connect() {
    if (this._destroyed) return
    this._setState("connecting")
    try {
      const ws = new WebSocket(WS_URL)
      this._ws = ws

      ws.onopen = () => {
        this._setState("connected")
        this._monitor.reset()
        this._heartbeat.start()
        this._flushQueue()
        this._subscriptions.resubscribeAll()
      }

      ws.onmessage = (event) => {
        try {
          const msg = JSON.parse(event.data) as WSMessage
          this._handleMessage(msg)
        } catch {
          /* ignore parse errors */
        }
      }

      ws.onclose = () => {
        this._heartbeat.stop()
        this._setState("disconnected")
        if (!this._destroyed) this._scheduleReconnect("Connection closed")
      }

      ws.onerror = () => {
        ws.close()
      }
    } catch {
      if (!this._destroyed) this._scheduleReconnect("Connection failed")
    }
  }

  private _reconnect(reason: string) {
    this._ws?.close()
    this._monitor.recordReconnect(reason)
    this._setState("reconnecting")
    this._ws = null
    this._connect()
  }

  private _scheduleReconnect(reason: string) {
    if (this._connectTimer) return
    const event = this._monitor.recordReconnect(reason)
    this._emit("reconnect", event)
    this._setState("reconnecting")
    this._connectTimer = setTimeout(() => {
      this._connectTimer = null
      this._connect()
    }, event.delay)
  }

  private _setState(state: ConnectionState) {
    this._stateListeners.forEach((l) => l(state))
  }

  // ── Message handling ──

  private _handleMessage(msg: WSMessage) {
    if (msg.type === "pong") {
      this._heartbeat.handlePong()
      return
    }
    if (msg.type === "welcome") {
      return
    }

    this._emit("event", msg)
    this._dispatcher.dispatch(msg)

    // Route to backend event consumers
    const consumers = this._consumers.get(msg.type)
    if (consumers) {
      consumers.forEach((fn) => {
        try { fn(msg.payload || msg) } catch { /* isolate */ }
      })
    }
  }

  // ── Public API ──

  onEvent(type: string, handler: (payload: any) => void) {
    if (!this._consumers.has(type)) {
      this._consumers.set(type, new Set())
    }
    this._consumers.get(type)!.add(handler)
    return () => this._consumers.get(type)?.delete(handler)
  }

  subscribe(id: string, channels: string[], symbols: string[], handler: (msg: any) => void) {
    this._subscriptions.subscribe(id, channels, symbols, handler)
  }

  unsubscribe(id: string) {
    this._subscriptions.unsubscribe(id)
  }

  send(data: object) {
    const msg = JSON.stringify(data)
    if (this._ws?.readyState === WebSocket.OPEN) {
      this._ws.send(msg)
    } else {
      this._messageQueue.push(msg)
    }
  }

  onState(listener: StateListener) {
    this._stateListeners.add(listener)
    return () => this._stateListeners.delete(listener)
  }

  get dispatcher() {
    return this._dispatcher
  }

  get monitor() {
    return this._monitor
  }

  destroy() {
    this._destroyed = true
    this._heartbeat.stop()
    if (this._connectTimer) clearTimeout(this._connectTimer)
    this._ws?.close()
    this._ws = null
  }

  private _flushQueue() {
    while (this._messageQueue.length > 0) {
      const msg = this._messageQueue.shift()
      if (msg && this._ws?.readyState === WebSocket.OPEN) {
        this._ws.send(msg)
      }
    }
  }

  private _emit(event: string, data: any) {
    // Internal event bus for heartbeat/monitor
    if (event === "latency") {
      this._consumers.get("__latency")?.forEach((fn) => fn(data))
    }
    if (event === "reconnect") {
      this._consumers.get("__reconnect")?.forEach((fn) => fn(data))
    }
  }
}

// Singleton
let _instance: WebSocketManager | null = null

export function getWSManager(): WebSocketManager {
  if (!_instance) {
    _instance = new WebSocketManager()
  }
  return _instance
}
