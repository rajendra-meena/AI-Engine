"use client"

import { AppLayout, PageContent } from "@/components/layout/AppLayout"
import { CommandCenter } from "@/components/operations/CommandCenter"

export default function CommandCenterPage() {
  return (
    <AppLayout>
      <PageContent>
        <CommandCenter />
      </PageContent>
    </AppLayout>
  )
}
