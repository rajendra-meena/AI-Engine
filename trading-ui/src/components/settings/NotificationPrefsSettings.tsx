"use client"

import { SettingsSection } from "./SettingsSection"
import { ToggleCard } from "./ToggleCard"
import { SliderControl } from "./SliderControl"
import type { NotificationPrefs as NotifType } from "@/store/useSettingsStore"

interface Props {
  settings: NotifType
  onUpdate: (p: Partial<NotifType>) => void
}

export function NotificationPrefsPanel({ settings, onUpdate }: Props) {
  return (
    <SettingsSection title="Notifications" description="Notification preferences">
      <ToggleCard label="Desktop Notifications" description="Show system desktop notifications" checked={settings.desktop} onChange={(v) => onUpdate({ desktop: v })} />
      <ToggleCard label="Sound" description="Play sound for new notifications" checked={settings.sound} onChange={(v) => onUpdate({ sound: v })} />
      <ToggleCard label="Popup" description="Show in-app toast popups" checked={settings.popup} onChange={(v) => onUpdate({ popup: v })} />
      <ToggleCard label="Grouping" description="Group notifications by time" checked={settings.grouping} onChange={(v) => onUpdate({ grouping: v })} />
      <ToggleCard label="Auto Delete" description="Automatically delete old notifications" checked={settings.autoDelete} onChange={(v) => onUpdate({ autoDelete: v })} />
      <SliderControl label="History Limit" value={settings.historyLimit} min={50} max={2000} step={50} onChange={(v) => onUpdate({ historyLimit: v })} />
    </SettingsSection>
  )
}
