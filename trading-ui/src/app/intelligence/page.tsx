"use client"

import { AppLayout, PageContent } from "@/components/layout/AppLayout"
import { MarketIntelligenceDashboard } from "@/components/intelligence/MarketIntelligenceDashboard"

export default function IntelligenceRoute() {
  return (
    <AppLayout>
      <PageContent>
        <MarketIntelligenceDashboard />
      </PageContent>
    </AppLayout>
  )
}
