"use client"

import { AppLayout, PageContent } from "@/components/layout/AppLayout"
import { ExecutionControlCenter } from "@/components/execution/ExecutionControlCenter"

export default function ExecutionPage() {
  return (
    <AppLayout>
      <PageContent>
        <ExecutionControlCenter />
      </PageContent>
    </AppLayout>
  )
}
