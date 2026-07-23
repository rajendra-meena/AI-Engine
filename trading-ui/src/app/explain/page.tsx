"use client"

import { AppLayout, PageContent } from "@/components/layout/AppLayout"
import { ExplainabilityDashboard } from "@/components/explainability/ExplainabilityDashboard"

export default function ExplainRoute() {
  return (
    <AppLayout>
      <PageContent>
        <ExplainabilityDashboard />
      </PageContent>
    </AppLayout>
  )
}
