"use client"

import { AppLayout, PageContent } from "@/components/layout/AppLayout"
import { SettingsPage } from "@/components/settings/SettingsPage"

export default function SettingsRoute() {
  return (
    <AppLayout>
      <PageContent>
        <SettingsPage />
      </PageContent>
    </AppLayout>
  )
}
