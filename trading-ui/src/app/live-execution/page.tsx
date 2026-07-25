"use client"

import { AppLayout, PageContent } from "@/components/layout/AppLayout"
import { LiveExecutionControlCenter } from "@/components/live/LiveExecutionControlCenter"

export default function LiveExecutionPage() {
  return (
    <AppLayout>
      <PageContent>
        <LiveExecutionControlCenter />
      </PageContent>
    </AppLayout>
  )
}
