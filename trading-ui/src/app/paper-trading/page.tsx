"use client"

import { AppLayout, PageContent } from "@/components/layout/AppLayout"
import { PaperTradingDashboard } from "@/components/paper/PaperTradingDashboard"

export default function PaperTradingPage() {
  return (
    <AppLayout>
      <PageContent>
        <PaperTradingDashboard />
      </PageContent>
    </AppLayout>
  )
}
