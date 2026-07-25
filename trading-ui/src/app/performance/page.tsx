"use client"

import { AppLayout, PageContent } from "@/components/layout/AppLayout"
import { PerformanceDashboard } from "@/components/performance/PerformanceDashboard"

export default function PerformancePage() {
  return (
    <AppLayout>
      <PageContent>
        <PerformanceDashboard />
      </PageContent>
    </AppLayout>
  )
}
