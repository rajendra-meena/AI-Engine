"use client"

import { cn } from "@/lib/utils"
import { Star } from "lucide-react"

interface ScannerRankingProps {
  rank: number
  size?: "sm" | "md"
}

export function ScannerRanking({ rank, size = "sm" }: ScannerRankingProps) {
  const full = Math.floor(rank)
  const hasHalf = rank - full >= 0.5

  return (
    <span className={cn("inline-flex items-center gap-0.5", size === "md" ? "text-[10px]" : "text-[8px]")}>
      {[1, 2, 3, 4, 5].map((star) => {
        const filled = star <= full
        const half = !filled && star === full + 1 && hasHalf
        return (
          <Star
            key={star}
            className={cn(
              size === "md" ? "w-3 h-3" : "w-2.5 h-2.5",
              filled ? "text-amber-500 fill-amber-500" : half ? "text-amber-500/50 fill-amber-500/50" : "text-muted-foreground/20",
            )}
          />
        )
      })}
    </span>
  )
}
