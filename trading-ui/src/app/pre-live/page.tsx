"use client"

import { AppLayout, PageContent } from "@/components/layout/AppLayout"
import { PreLiveControlCenter } from "@/components/pre-live/PreLiveControlCenter"

export default function PreLivePage() {
  return (
    <AppLayout>
      <PageContent>
        <PreLiveControlCenter />
      </PageContent>
    </AppLayout>
  )
}
