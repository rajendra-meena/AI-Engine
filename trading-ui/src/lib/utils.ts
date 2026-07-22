import { type ClassValue, clsx } from "clsx"
import { twMerge } from "tailwind-merge"

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs))
}

export function formatNumber(value: number | null | undefined, decimals = 2): string {
  if (value == null) return "--"
  return value.toLocaleString("en-IN", { minimumFractionDigits: decimals, maximumFractionDigits: decimals })
}

export function formatPercent(value: number | null | undefined): string {
  if (value == null) return "--"
  const sign = value >= 0 ? "+" : ""
  return `${sign}${value.toFixed(2)}%`
}

export function formatDate(dateStr: string | null | undefined): string {
  if (!dateStr) return "--"
  return new Date(dateStr).toLocaleDateString("en-IN", { day: "2-digit", month: "short", year: "numeric" })
}

export function formatTime(dateStr: string | null | undefined): string {
  if (!dateStr) return "--"
  return new Date(dateStr).toLocaleTimeString("en-IN", { hour: "2-digit", minute: "2-digit" })
}
