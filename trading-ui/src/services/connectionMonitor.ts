/**
 * Connection monitor — tracks reconnect attempts, quality, and history.
 */

import type { ConnectionQuality, ReconnectEvent } from "@/types/websocket"

export type QualityListener = (quality: ConnectionQuality) => void
export type ReconnectListener = (event: ReconnectEvent) => void

export class ConnectionMonitor {
  private _reconnectCount = 0
  private _qualityListeners: QualityListener[] = []
  private _reconnectListeners: ReconnectListener[] = []
  private _lastQuality: ConnectionQuality = "dead"

  onQuality(listener: QualityListener) {
    this._qualityListeners.push(listener)
    return () => {
      this._qualityListeners = this._qualityListeners.filter((l) => l !== listener)
    }
  }

  onReconnect(listener: ReconnectListener) {
    this._reconnectListeners.push(listener)
    return () => {
      this._reconnectListeners = this._reconnectListeners.filter((l) => l !== listener)
    }
  }

  recordReconnect(reason: string): ReconnectEvent {
    this._reconnectCount++
    const event: ReconnectEvent = {
      attempt: this._reconnectCount,
      delay: Math.min(1000 * 2 ** Math.min(this._reconnectCount - 1, 5), 30000),
      reason,
      timestamp: new Date().toISOString(),
    }
    this._reconnectListeners.forEach((l) => l(event))
    return event
  }

  setQuality(quality: ConnectionQuality) {
    if (quality !== this._lastQuality) {
      this._lastQuality = quality
      this._qualityListeners.forEach((l) => l(quality))
    }
  }

  reset() {
    this._reconnectCount = 0
  }

  get reconnectCount() {
    return this._reconnectCount
  }

  get quality() {
    return this._lastQuality
  }
}
