/**
 * Heartbeat manager — sends periodic pings, measures latency.
 */

const PING_INTERVAL = 15_000
const PONG_TIMEOUT = 5_000

export class HeartbeatManager {
  private _ws: () => WebSocket | null
  private _onLatency: (ms: number) => void
  private _onDeath: () => void
  private _pingTimer: ReturnType<typeof setInterval> | null = null
  private _pongTimer: ReturnType<typeof setTimeout> | null = null
  private _pingStart = 0

  constructor(
    ws: () => WebSocket | null,
    onLatency: (ms: number) => void,
    onDeath: () => void
  ) {
    this._ws = ws
    this._onLatency = onLatency
    this._onDeath = onDeath
  }

  start() {
    this.stop()
    this._pingTimer = setInterval(() => this._ping(), PING_INTERVAL)
  }

  stop() {
    if (this._pingTimer) { clearInterval(this._pingTimer); this._pingTimer = null }
    if (this._pongTimer) { clearTimeout(this._pongTimer); this._pongTimer = null }
  }

  handlePong() {
    if (this._pongTimer) {
      clearTimeout(this._pongTimer)
      this._pongTimer = null
    }
    const elapsed = Date.now() - this._pingStart
    this._onLatency(Math.min(elapsed, 9999))
  }

  private _ping() {
    const ws = this._ws()
    if (!ws || ws.readyState !== WebSocket.OPEN) return

    this._pingStart = Date.now()
    ws.send(JSON.stringify({ type: "ping" }))

    this._pongTimer = setTimeout(() => {
      this._onDeath()
    }, PONG_TIMEOUT)
  }
}
