"use client"

import { AppLayout, PageContent } from "@/components/layout/AppLayout"
import { LearningDashboard } from "@/components/learning/LearningDashboard"

export default function LearningPage() {
  return (
    <AppLayout>
      <PageContent>
        <LearningDashboard />
      </PageContent>
    </AppLayout>
  )
}
