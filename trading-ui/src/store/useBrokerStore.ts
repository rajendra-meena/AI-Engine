"use client"

import { create } from "zustand"
import { persist } from "zustand/middleware"

interface BrokerState {
  authenticated: boolean
  connected: boolean
  user_id: string
  user_name: string
  broker: string
  exchange: string
  setAuth: (data: { user_id: string; user_name: string; broker: string; exchange: string }) => void
  setConnected: (connected: boolean) => void
  clear: () => void
}

export const useBrokerStore = create<BrokerState>()(
  persist(
    (set) => ({
      authenticated: false,
      connected: false,
      user_id: "",
      user_name: "",
      broker: "ZERODHA",
      exchange: "NSE",
      setAuth: (data) =>
        set({
          authenticated: true,
          user_id: data.user_id,
          user_name: data.user_name,
          broker: data.broker,
          exchange: data.exchange,
        }),
      setConnected: (connected) => set({ connected }),
      clear: () =>
        set({
          authenticated: false,
          connected: false,
          user_id: "",
          user_name: "",
        }),
    }),
    { name: "marketmind-broker" }
  )
)
