"use client"

import { useState } from "react"
import { cn } from "@/lib/utils"
import { Download, FileJson, FileSpreadsheet, FileText } from "lucide-react"

interface ExportPanelProps {
  onExport: (format: "csv" | "json" | "pdf") => void
  className?: string
}

export function ExportPanel({ onExport, className }: ExportPanelProps) {
  const [open, setOpen] = useState(false)

  const EXPORT_FORMATS = [
    { id: "csv" as const, label: "CSV", icon: <FileSpreadsheet className="w-3 h-3" />, color: "text-emerald-500" },
    { id: "json" as const, label: "JSON", icon: <FileJson className="w-3 h-3" />, color: "text-amber-500" },
    { id: "pdf" as const, label: "PDF", icon: <FileText className="w-3 h-3" />, color: "text-red-500" },
  ]

  return (
    <div className={cn("relative", className)}>
      <button
        onClick={() => setOpen(!open)}
        className="flex items-center gap-1 rounded-md border bg-card px-2 py-1 text-[9px] font-medium text-muted-foreground hover:text-foreground hover:bg-accent transition-colors"
      >
        <Download className="w-3 h-3" />
        Export
      </button>

      {open && (
        <>
          <div className="fixed inset-0 z-40" onClick={() => setOpen(false)} />
          <div className="absolute right-0 top-full mt-1 z-50 rounded-lg border bg-card shadow-lg p-1 min-w-[120px]">
            {EXPORT_FORMATS.map((fmt) => (
              <button
                key={fmt.id}
                onClick={() => { onExport(fmt.id); setOpen(false) }}
                className={cn("flex items-center gap-2 w-full rounded px-2 py-1.5 text-[10px] font-medium text-muted-foreground hover:bg-accent hover:text-foreground transition-colors")}
              >
                <span className={fmt.color}>{fmt.icon}</span>
                {fmt.label}
              </button>
            ))}
          </div>
        </>
      )}
    </div>
  )
}
