"use client"

import { cn } from "@/lib/utils"
import { Search, Filter, X } from "lucide-react"
import type { NotificationCategory, NotificationPriority } from "@/store/useNotificationStore"

interface NotificationFilterProps {
  filterCategory: NotificationCategory | null
  filterPriority: NotificationPriority | null
  searchQuery: string
  onCategoryChange: (cat: NotificationCategory | null) => void
  onPriorityChange: (pri: NotificationPriority | null) => void
  onSearchChange: (q: string) => void
  onClear: () => void
  className?: string
}

const CATEGORIES: { id: NotificationCategory; label: string }[] = [
  { id: "ai", label: "AI" },
  { id: "indicators", label: "Indicators" },
  { id: "structure", label: "Structure" },
  { id: "patterns", label: "Patterns" },
  { id: "sr", label: "S/R" },
  { id: "portfolio", label: "Portfolio" },
  { id: "replay", label: "Replay" },
  { id: "scanner", label: "Scanner" },
  { id: "orders", label: "Orders" },
  { id: "warnings", label: "Warnings" },
  { id: "errors", label: "Errors" },
  { id: "system", label: "System" },
]

const PRIORITIES: { id: NotificationPriority; label: string }[] = [
  { id: "INFO", label: "Info" },
  { id: "SUCCESS", label: "Success" },
  { id: "WARNING", label: "Warning" },
  { id: "CRITICAL", label: "Critical" },
]

export function NotificationFilter({
  filterCategory, filterPriority, searchQuery,
  onCategoryChange, onPriorityChange, onSearchChange, onClear, className,
}: NotificationFilterProps) {
  return (
    <div className={cn("space-y-1.5", className)}>
      {/* Search */}
      <div className="flex items-center gap-1 bg-muted/50 rounded border px-2">
        <Search className="w-3 h-3 text-muted-foreground shrink-0" />
        <input
          type="text"
          value={searchQuery}
          onChange={(e) => onSearchChange(e.target.value)}
          placeholder="Search notifications..."
          className="h-7 bg-transparent text-[10px] flex-1 focus:outline-none placeholder:text-muted-foreground/50"
        />
        {searchQuery && (
          <button onClick={() => onSearchChange("")} className="p-0.5 text-muted-foreground hover:text-foreground">
            <X className="w-2.5 h-2.5" />
          </button>
        )}
      </div>

      {/* Category chips */}
      <div className="flex flex-wrap gap-0.5">
        {CATEGORIES.map((cat) => (
          <button
            key={cat.id}
            onClick={() => onCategoryChange(filterCategory === cat.id ? null : cat.id)}
            className={cn(
              "px-1.5 py-0.5 rounded text-[8px] font-medium transition-colors",
              filterCategory === cat.id ? "bg-primary/20 text-primary" : "bg-muted/30 text-muted-foreground hover:bg-accent",
            )}
          >
            {cat.label}
          </button>
        ))}
      </div>

      {/* Priority chips */}
      <div className="flex items-center gap-1">
        <Filter className="w-2.5 h-2.5 text-muted-foreground" />
        {PRIORITIES.map((pri) => (
          <button
            key={pri.id}
            onClick={() => onPriorityChange(filterPriority === pri.id ? null : pri.id)}
            className={cn(
              "px-1.5 py-0.5 rounded text-[8px] font-medium transition-colors",
              filterPriority === pri.id ? "bg-primary/20 text-primary" : "bg-muted/30 text-muted-foreground hover:bg-accent",
            )}
          >
            {pri.label}
          </button>
        ))}

        {(filterCategory || filterPriority || searchQuery) && (
          <button onClick={onClear} className="ml-auto px-1.5 py-0.5 rounded text-[8px] text-muted-foreground hover:text-foreground hover:bg-accent">
            Clear
          </button>
        )}
      </div>
    </div>
  )
}
