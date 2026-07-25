"use client"

import { AppLayout, PageContent } from "@/components/layout/AppLayout"
import { OrchestratorDashboard } from "@/components/orchestrator/OrchestratorDashboard"

export default function OrchestratorPage() {
  return (
    <AppLayout>
      <PageContent>
        <OrchestratorDashboard />
      </PageContent>
    </AppLayout>
  )
}
