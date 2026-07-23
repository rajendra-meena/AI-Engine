"use client"

import { AppLayout, PageContent } from "@/components/layout/AppLayout"
import { StrategyDashboard } from "@/components/strategy/StrategyDashboard"

export default function StrategyRoute() {
  return (
    <AppLayout>
      <PageContent>
        <StrategyDashboard />
      </PageContent>
    </AppLayout>
  )
}
