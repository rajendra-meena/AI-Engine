"use client"

import { AppLayout, PageContent } from "@/components/layout/AppLayout"
import { AIDecisionValidationDashboard } from "@/components/ai-decision/AIDecisionValidationDashboard"

export default function AIDecisionPage() {
  return (
    <AppLayout>
      <PageContent>
        <AIDecisionValidationDashboard />
      </PageContent>
    </AppLayout>
  )
}
