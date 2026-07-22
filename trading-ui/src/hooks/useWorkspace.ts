"use client"

import { useCallback, useMemo } from "react"
import { useWorkspaceStore } from "@/store/useWorkspaceStore"
import { workspaceService } from "@/services/workspaceService"
import type { WorkspaceTemplate } from "@/store/useWorkspaceStore"

/**
 * useWorkspace — central hook for the Multi-Chart Workspace.
 */
export function useWorkspace() {
  const store = useWorkspaceStore()

  const currentWorkspace = useMemo(
    () => store.workspaces.find((w) => w.id === store.activeWorkspaceId) ?? null,
    [store.workspaces, store.activeWorkspaceId],
  )

  const charts = currentWorkspace?.charts ?? []
  const dims = workspaceService.getGridDimensions(store.currentLayout)

  const createFromTemplate = useCallback((template: WorkspaceTemplate) => {
    const ws = workspaceService.createFromTemplate(template)
    store.addWorkspace(ws)
  }, [store])

  const syncToGroup = useCallback((groupId: string | null, key: string, value: unknown) => {
    workspaceService.syncToGroup(groupId, key, value)
  }, [])

  return {
    /* state */
    activeWorkspaceId: store.activeWorkspaceId,
    workspaces: store.workspaces,
    currentWorkspace,
    charts,
    currentLayout: store.currentLayout,
    templates: store.templates,
    syncState: store.syncState,
    fullscreenChart: store.fullscreenChart,
    monitorMode: store.monitorMode,
    floatingCharts: store.floatingCharts,
    showMiniMap: store.showMiniMap,
    showStatus: store.showStatus,
    gridCols: dims.cols,
    gridRows: dims.rows,

    /* actions */
    setActiveWorkspace: store.setActiveWorkspace,
    setLayout: store.setLayout,
    addWorkspace: store.addWorkspace,
    removeWorkspace: store.removeWorkspace,
    renameWorkspace: store.renameWorkspace,
    duplicateWorkspace: store.duplicateWorkspace,
    updateChart: store.updateChart,
    addChart: store.addChart,
    removeChart: store.removeChart,
    setSyncedGroup: store.setSyncedGroup,
    setFullscreenChart: store.setFullscreenChart,
    setMonitorMode: store.setMonitorMode,
    toggleFloatingChart: store.toggleFloatingChart,
    setSyncState: store.setSyncState,
    setShowMiniMap: store.setShowMiniMap,
    setShowStatus: store.setShowStatus,
    createFromTemplate,
    syncToGroup,
    exportWorkspace: workspaceService.exportWorkspace,
    importWorkspace: workspaceService.importWorkspace,
    getGridClass: workspaceService.getGridClass,
  }
}
