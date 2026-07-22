"use client"

import { useState, useCallback } from "react"
import { cn } from "@/lib/utils"

interface ShortcutEditorProps {
  id: string
  label: string
  keys: string
  category: string
  onChange: (id: string, keys: string) => void
  conflicts?: string[]
}

export function ShortcutEditor({ id, label, keys, category, onChange, conflicts }: ShortcutEditorProps) {
  const [editing, setEditing] = useState(false)
  const [tempKeys, setTempKeys] = useState("")

  const handleKeyDown = useCallback((e: React.KeyboardEvent) => {
    e.preventDefault()
    const parts: string[] = []
    if (e.ctrlKey || e.metaKey) parts.push("Ctrl")
    if (e.shiftKey) parts.push("Shift")
    if (e.altKey) parts.push("Alt")
    const key = e.key
    if (!["Control", "Shift", "Alt", "Meta"].includes(key)) {
      parts.push(key === " " ? "Space" : key)
      const combo = parts.join("+")
      setTempKeys(combo)
      onChange(id, combo)
      setEditing(false)
    }
  }, [id, onChange])

  return (
    <div className={cn("flex items-center gap-2 py-1", conflicts?.length ? "bg-red-500/5 rounded px-1" : "")}>
      <div className="flex-1 min-w-0">
        <div className="text-[9px] font-medium">{label}</div>
        <div className="text-[7px] text-muted-foreground uppercase">{category}</div>
      </div>
      {editing ? (
        <input
          autoFocus
          value={tempKeys}
          onKeyDown={handleKeyDown}
          onBlur={() => setEditing(false)}
          placeholder="Press keys..."
          className="h-6 w-24 rounded border bg-muted/50 px-1.5 text-[9px] font-mono text-center focus:outline-none focus:ring-1 focus:ring-primary"
        />
      ) : (
        <button
          onClick={() => { setTempKeys(keys); setEditing(true) }}
          className={cn(
            "h-6 rounded border bg-muted/30 px-2 text-[8px] font-mono hover:bg-accent transition-colors",
            conflicts?.length ? "border-red-500/50 text-red-500" : "",
          )}
        >
          {keys}
        </button>
      )}
      {conflicts && conflicts.length > 0 && (
        <div className="text-[7px] text-red-500 max-w-[120px] truncate" title={conflicts.join(", ")}>
          Conflict
        </div>
      )}
    </div>
  )
}
