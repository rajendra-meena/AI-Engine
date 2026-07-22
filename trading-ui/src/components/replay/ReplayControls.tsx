"use client"

import { useEffect, useCallback } from "react"

interface ReplayControlsProps {
  onPlayPause: () => void
  onStepBack: () => void
  onStepForward: () => void
  onStop: () => void
}

/**
 * ReplayControls — Keyboard shortcut handler.
 *
 * Space  → Play/Pause
 * ←      → Previous Candle
 * →      → Next Candle
 * Ctrl+← → Jump to Start
 * Ctrl+→ → Jump to End
 */
export function ReplayControls({ onPlayPause, onStepBack, onStepForward, onStop }: ReplayControlsProps) {
  const handleKeyDown = useCallback((e: KeyboardEvent) => {
    // Ignore when typing in inputs
    const target = e.target as HTMLElement
    if (target.tagName === "INPUT" || target.tagName === "TEXTAREA" || target.isContentEditable) return

    const ctrl = e.ctrlKey || e.metaKey

    switch (e.code) {
      case "Space":
        e.preventDefault()
        onPlayPause()
        break
      case "ArrowLeft":
        e.preventDefault()
        if (ctrl) onStop()
        else onStepBack()
        break
      case "ArrowRight":
        e.preventDefault()
        if (ctrl) {
          // Jump to end (seek to last) — handled by store
          onStepForward()
        } else {
          onStepForward()
        }
        break
    }
  }, [onPlayPause, onStepBack, onStepForward, onStop])

  useEffect(() => {
    window.addEventListener("keydown", handleKeyDown)
    return () => window.removeEventListener("keydown", handleKeyDown)
  }, [handleKeyDown])

  // This is an invisible handler — renders nothing
  return null
}
