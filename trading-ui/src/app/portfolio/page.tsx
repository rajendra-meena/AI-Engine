"use client"

import { AppLayout, PageContent } from "@/components/layout/AppLayout"
import { PortfolioPage } from "@/components/portfolio/PortfolioPage"

export default function PortfolioRoute() {
  return (
    <AppLayout>
      <PageContent>
        <PortfolioPage />
      </PageContent>
    </AppLayout>
  )
}
