"use client"

import { AppLayout, PageContent } from "@/components/layout/AppLayout"
import { ResearchDashboard } from "@/components/research/ResearchDashboard"

export default function ResearchRoute() {
  return (
    <AppLayout>
      <PageContent>
        <ResearchDashboard />
      </PageContent>
    </AppLayout>
  )
}
