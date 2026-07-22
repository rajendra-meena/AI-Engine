"use client"

import { Navbar } from "@/components/navbar"
import { SettingsPage } from "@/components/settings/SettingsPage"
import { useRealtime } from "@/hooks/useRealtime"

export default function SettingsRoute() {
  useRealtime()

  return (
    <div className="min-h-screen flex flex-col">
      <Navbar />
      <main className="flex-1 p-4 md:p-6 max-w-[1580px] mx-auto w-full">
        <SettingsPage />
      </main>
    </div>
  )
}
