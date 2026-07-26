"use client"

import { AppLayout, PageContent } from "@/components/layout/AppLayout"
import { ProductionReadinessDashboard } from "@/components/production-readiness/ProductionReadinessDashboard"

export default function ProductionReadinessPage() {
  return (
    <AppLayout>
      <PageContent>
        <ProductionReadinessDashboard />
      </PageContent>
    </AppLayout>
  )
}
