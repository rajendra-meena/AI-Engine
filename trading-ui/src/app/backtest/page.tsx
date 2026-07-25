"use client"

import { AppLayout, PageContent } from "@/components/layout/AppLayout"
import { BacktestDashboard } from "@/components/backtest/BacktestDashboard"

export default function BacktestPage() {
  return (
    <AppLayout>
      <PageContent>
        <BacktestDashboard />
      </PageContent>
    </AppLayout>
  )
}
