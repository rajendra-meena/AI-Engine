"use client"

import { AppLayout, PageContent } from "@/components/layout/AppLayout"
import { MLDashboard } from "@/components/ml/MLDashboard"

export default function MLRoute() {
  return (
    <AppLayout>
      <PageContent>
        <MLDashboard />
      </PageContent>
    </AppLayout>
  )
}
