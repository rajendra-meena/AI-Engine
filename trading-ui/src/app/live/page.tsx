"use client"

import { AppLayout, PageContent } from "@/components/layout/AppLayout"
import { ScannerPage } from "@/components/scanner/ScannerPage"

export default function LivePage() {
  return (
    <AppLayout>
      <PageContent>
        <ScannerPage />
      </PageContent>
    </AppLayout>
  )
}
