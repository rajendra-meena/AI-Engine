"use client"

import { cn } from "@/lib/utils"

interface TargetCardProps {
  number: number
  price: number | null
  probability?: number
  hit?: boolean
}

export function TargetCard({ number, price, probability, hit }: TargetCardProps) {
  if (!price) return null

  return (
    <div className={cn(
      "rounded-md border p-2 text-center transition-colors",
      hit ? "border-emerald-500/30 bg-emerald-500/10" : "border-border bg-muted/20"
    )}>
      <div className="text-[9px] font-medium text-muted-foreground uppercase tracking-wider">T{number}</div>
      <div className="text-[13px] font-bold font-mono">{price.toFixed(2)}</div>
      {probability != null && (
        <div className="text-[9px] text-muted-foreground">{(probability * 100).toFixed(0)}% prob</div>
      )}
    </div>
  )
}
