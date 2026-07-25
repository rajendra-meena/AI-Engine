"use client"

import { AppLayout, PageContent } from "@/components/layout/AppLayout"
import { RiskDashboard } from "@/components/risk/RiskDashboard"

export default function RiskPage() {
  return (
    <AppLayout>
      <PageContent>
        <RiskDashboard />
      </PageContent>
    </AppLayout>
  )
}
