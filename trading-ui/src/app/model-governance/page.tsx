"use client"

import { AppLayout, PageContent } from "@/components/layout/AppLayout"
import { ModelGovernanceDashboard } from "@/components/model-governance/ModelGovernanceDashboard"

export default function ModelGovernancePage() {
  return (
    <AppLayout>
      <PageContent>
        <ModelGovernanceDashboard />
      </PageContent>
    </AppLayout>
  )
}
