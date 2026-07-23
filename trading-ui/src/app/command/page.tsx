"use client"

import { AppLayout, PageContent } from "@/components/layout/AppLayout"
import { CommandCenter } from "@/components/command/CommandCenter"

export default function CommandRoute() {
  return (
    <AppLayout>
      <PageContent>
        <CommandCenter />
      </PageContent>
    </AppLayout>
  )
}
