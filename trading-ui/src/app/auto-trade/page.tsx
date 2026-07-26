"use client"

import { AppLayout, PageContent } from "@/components/layout/AppLayout"
import { AutoTradeWorkspace } from "@/components/auto-trade/AutoTradeWorkspace"
import { BottomPanel } from "@/components/layout/BottomPanel"

export default function AutoTradePage() {
  return (
    <AppLayout bottom={<BottomPanel />}>
      <PageContent>
        <AutoTradeWorkspace />
      </PageContent>
    </AppLayout>
  )
}
