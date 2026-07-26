"use client"

import { AppLayout, PageContent } from "@/components/layout/AppLayout"
import { AIPerformanceDashboard } from "@/components/ai-performance/AIPerformanceDashboard"

export default function AIPerformancePage() {
  return (
    <AppLayout>
      <PageContent>
        <AIPerformanceDashboard />
      </PageContent>
    </AppLayout>
  )
}
