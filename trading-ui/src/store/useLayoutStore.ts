import { create } from "zustand"
import { persist } from "zustand/middleware"

interface LayoutState {
  sidebarOpen: boolean
  rightPanelOpen: boolean
  bottomPanelOpen: boolean
  bottomPanelHeight: number
  sidebarWidth: number
  activeNav: string
  toggleSidebar: () => void
  toggleRightPanel: () => void
  toggleBottomPanel: () => void
  setBottomPanelHeight: (h: number) => void
  setActiveNav: (nav: string) => void
  setSidebarWidth: (w: number) => void
}

export const useLayoutStore = create<LayoutState>()(
  persist(
    (set) => ({
      sidebarOpen: true,
      rightPanelOpen: true,
      bottomPanelOpen: true,
      bottomPanelHeight: 220,
      sidebarWidth: 260,
      activeNav: "dashboard",
      toggleSidebar: () => set((s) => ({ sidebarOpen: !s.sidebarOpen })),
      toggleRightPanel: () => set((s) => ({ rightPanelOpen: !s.rightPanelOpen })),
      toggleBottomPanel: () => set((s) => ({ bottomPanelOpen: !s.bottomPanelOpen })),
      setBottomPanelHeight: (h) => set({ bottomPanelHeight: Math.max(100, Math.min(500, h)) }),
      setActiveNav: (nav) => set({ activeNav: nav }),
      setSidebarWidth: (w) => set({ sidebarWidth: Math.max(70, Math.min(400, w)) }),
    }),
    { name: "marketmind-layout" }
  )
)
