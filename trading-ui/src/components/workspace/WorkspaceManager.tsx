"use client"

import { useState } from "react"
import { cn } from "@/lib/utils"
import { Plus, Trash2, Copy, Check, FileDown, FileUp } from "lucide-react"
import type { WorkspaceLayout, WorkspaceTemplate } from "@/store/useWorkspaceStore"

interface WorkspaceManagerProps {
  workspaces: WorkspaceLayout[]
  activeId: string | null
  templates: WorkspaceTemplate[]
  onSelect: (id: string) => void
  onAddTemplate: (template: WorkspaceTemplate) => void
  onDuplicate: (id: string) => void
  onRemove: (id: string) => void
  onRename: (id: string, name: string) => void
  onExport: (id: string) => void
  onImport: () => void
  className?: string
}

export function WorkspaceManager({ workspaces, activeId, templates, onSelect, onAddTemplate, onDuplicate, onRemove, onRename, onExport, onImport, className }: WorkspaceManagerProps) {
  const [renaming, setRenaming] = useState<string | null>(null)
  const [name, setName] = useState("")

  return (
    <div className={cn("rounded-lg border bg-card p-2 min-w-[200px]", className)}>
      <div className="text-[9px] font-medium text-muted-foreground uppercase tracking-wider mb-1 flex items-center justify-between">
        <span>Workspaces</span>
        <button onClick={onImport} className="rounded p-0.5 text-muted-foreground hover:text-foreground transition-colors" title="Import">
          <FileUp className="w-3 h-3" />
        </button>
      </div>

      {/* Existing workspaces */}
      <div className="space-y-0.5 mb-2">
        {workspaces.map((ws) => (
          <div key={ws.id} className={cn("group flex items-center gap-1 px-1.5 py-1 rounded text-[10px] cursor-pointer transition-colors", activeId === ws.id ? "bg-primary/20 text-primary" : "hover:bg-muted/20")}>
            {renaming === ws.id ? (
              <input
                autoFocus
                value={name}
                onChange={(e) => setName(e.target.value)}
                onBlur={() => { onRename(ws.id, name); setRenaming(null) }}
                onKeyDown={(e) => e.key === "Enter" && (onRename(ws.id, name), setRenaming(null))}
                className="flex-1 h-5 rounded bg-muted/50 px-1 text-[9px] focus:outline-none"
              />
            ) : (
              <span onClick={() => onSelect(ws.id)} className="flex-1 truncate">{ws.name}</span>
            )}
            <button onClick={() => { setRenaming(ws.id); setName(ws.name) }} className="p-0.5 opacity-0 group-hover:opacity-100 text-muted-foreground hover:text-foreground"><Check className="w-2.5 h-2.5" /></button>
            <button onClick={() => onDuplicate(ws.id)} className="p-0.5 opacity-0 group-hover:opacity-100 text-muted-foreground hover:text-foreground"><Copy className="w-2.5 h-2.5" /></button>
            <button onClick={() => onExport(ws.id)} className="p-0.5 opacity-0 group-hover:opacity-100 text-muted-foreground hover:text-foreground"><FileDown className="w-2.5 h-2.5" /></button>
            <button onClick={() => onRemove(ws.id)} className="p-0.5 opacity-0 group-hover:opacity-100 text-muted-foreground hover:text-red-500"><Trash2 className="w-2.5 h-2.5" /></button>
          </div>
        ))}
      </div>

      {/* Templates */}
      {templates.length > 0 && (
        <>
          <div className="text-[8px] text-muted-foreground uppercase tracking-wider mb-0.5">Templates</div>
          <div className="space-y-0.5">
            {templates.map((tpl) => (
              <button key={tpl.id} onClick={() => onAddTemplate(tpl)}
                className="flex items-center gap-1 w-full px-1.5 py-1 rounded text-[9px] text-muted-foreground hover:bg-accent hover:text-foreground transition-colors">
                <Plus className="w-2.5 h-2.5" />
                {tpl.name}
                <span className="ml-auto text-[7px]">{tpl.layout}</span>
              </button>
            ))}
          </div>
        </>
      )}
    </div>
  )
}
