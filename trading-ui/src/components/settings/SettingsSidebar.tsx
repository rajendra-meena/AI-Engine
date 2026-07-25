"use client"

import { cn } from "@/lib/utils"
import { Settings, Palette, BarChart3, Activity, Layers, ClipboardList, Shield, Repeat, Search, Bell, Briefcase, Keyboard, Layout, Download, Info, Wifi } from "lucide-react"
import { Search as SearchIcon } from "lucide-react"

interface SettingsSidebarProps {
  activeSection: string
  searchQuery: string
  onSectionChange: (section: string) => void
  onSearchChange: (q: string) => void
}

const SECTIONS = [
  { id: "general", label: "General", icon: Settings },
  { id: "appearance", label: "Appearance", icon: Palette },
  { id: "chart", label: "Chart", icon: BarChart3 },
  { id: "indicators", label: "Indicators", icon: Activity },
  { id: "overlays", label: "Overlays", icon: Layers },
  { id: "broker", label: "Broker", icon: Wifi },
  { id: "tradePlanner", label: "Trade Planner", icon: ClipboardList },
  { id: "risk", label: "Risk Management", icon: Shield },
  { id: "replay", label: "Replay", icon: Repeat },
  { id: "scanner", label: "Scanner", icon: Search },
  { id: "notifications", label: "Notifications", icon: Bell },
  { id: "portfolio", label: "Portfolio", icon: Briefcase },
  { id: "hotkeys", label: "Hotkeys", icon: Keyboard },
  { id: "workspace", label: "Workspace", icon: Layout },
  { id: "backup", label: "Backup & Restore", icon: Download },
  { id: "about", label: "About", icon: Info },
]

export function SettingsSidebar({ activeSection, searchQuery, onSectionChange, onSearchChange }: SettingsSidebarProps) {
  return (
    <aside className="w-52 shrink-0 border-r bg-card flex flex-col overflow-hidden">
      {/* Search */}
      <div className="p-2 border-b">
        <div className="flex items-center gap-1 bg-muted/50 rounded border px-2">
          <SearchIcon className="w-3 h-3 text-muted-foreground shrink-0" />
          <input
            type="text"
            value={searchQuery}
            onChange={(e) => onSearchChange(e.target.value)}
            placeholder="Search settings..."
            className="h-7 bg-transparent text-[10px] flex-1 focus:outline-none placeholder:text-muted-foreground/50"
          />
        </div>
      </div>

      {/* Sections */}
      <nav className="flex-1 overflow-y-auto p-1 space-y-0.5">
        {SECTIONS.map((section) => (
          <button
            key={section.id}
            onClick={() => onSectionChange(section.id)}
            className={cn(
              "flex items-center gap-2 w-full rounded px-2 py-1.5 text-[10px] font-medium transition-colors text-left",
              activeSection === section.id
                ? "bg-primary/20 text-primary"
                : "text-muted-foreground hover:bg-accent hover:text-foreground",
            )}
          >
            <section.icon className="w-3.5 h-3.5 shrink-0" />
            {section.label}
          </button>
        ))}
      </nav>
    </aside>
  )
}
