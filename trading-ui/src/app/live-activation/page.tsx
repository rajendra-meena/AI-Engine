"use client"

import { AppLayout, PageContent } from "@/components/layout/AppLayout"
import { LiveActivationCenter } from "@/components/live/LiveActivationCenter"

export default function LiveActivationPage() {
  return (
    <AppLayout>
      <PageContent>
        <LiveActivationCenter />
      </PageContent>
    </AppLayout>
  )
}
