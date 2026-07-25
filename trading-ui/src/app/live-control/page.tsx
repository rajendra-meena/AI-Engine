"use client"

import { AppLayout, PageContent } from "@/components/layout/AppLayout"
import { LiveControlCenter } from "@/components/live/LiveControlCenter"

export default function LiveControlPage() {
  return (
    <AppLayout>
      <PageContent>
        <LiveControlCenter />
      </PageContent>
    </AppLayout>
  )
}
