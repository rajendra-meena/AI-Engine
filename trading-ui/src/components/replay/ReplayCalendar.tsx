"use client"

import { cn } from "@/lib/utils"
import { CalendarDays, Calendar, LayoutGrid, List } from "lucide-react"
import type { CalendarMode } from "@/store/useReplayStore"

interface ReplayCalendarProps {
  mode: CalendarMode
  selectedDate: string | null
  onModeChange: (mode: CalendarMode) => void
  onDateChange: (date: string | null) => void
}

const MODES: { id: CalendarMode; icon: React.ReactNode; label: string }[] = [
  { id: "date", icon: <CalendarDays className="w-3 h-3" />, label: "Date" },
  { id: "week", icon: <List className="w-3 h-3" />, label: "Week" },
  { id: "month", icon: <Calendar className="w-3 h-3" />, label: "Month" },
  { id: "session", icon: <LayoutGrid className="w-3 h-3" />, label: "Session" },
]

export function ReplayCalendar({ mode, selectedDate, onModeChange, onDateChange }: ReplayCalendarProps) {
  const today = new Date().toISOString().split("T")[0]
  const displayDate = selectedDate || today

  return (
    <div className="rounded-md border bg-card p-2 space-y-2">
      <div className="text-[9px] font-medium text-muted-foreground uppercase tracking-wider">Calendar</div>

      {/* Mode tabs */}
      <div className="flex gap-0.5">
        {MODES.map((m) => (
          <button
            key={m.id}
            onClick={() => onModeChange(m.id)}
            className={cn(
              "flex items-center gap-1 px-1.5 py-1 rounded text-[9px] font-medium transition-colors",
              mode === m.id
                ? "bg-primary/20 text-primary"
                : "text-muted-foreground hover:bg-accent"
            )}
          >
            {m.icon}
            {m.label}
          </button>
        ))}
      </div>

      {/* Date input */}
      <input
        type="date"
        value={displayDate}
        onChange={(e) => onDateChange(e.target.value || null)}
        className="w-full h-7 rounded border bg-muted/50 px-2 text-[10px] font-mono focus:outline-none focus:ring-1 focus:ring-primary"
        max={today}
      />
    </div>
  )
}
