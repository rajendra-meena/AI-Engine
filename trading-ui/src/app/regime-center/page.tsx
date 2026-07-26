"use client"

import { AppLayout, PageContent } from "@/components/layout/AppLayout"
import { MarketRegimeDashboard } from "@/components/regime/MarketRegimeDashboard"

export default function RegimeCenterPage() {
  return (
    <AppLayout>
      <PageContent>
        <MarketRegimeDashboard />
      </PageContent>
    </AppLayout>
  )
}
