"use client"

import { motion } from "framer-motion"
import { cn } from "@/lib/utils"
import { ArrowDown } from "lucide-react"

interface DecisionFlowProps {
  score: number
  confidence: number
  hasTradePlan: boolean
  decision: string
}

const STAGES = [
  { label: "Score Engine", value: "score", color: "border-l-violet-500" },
  { label: "Confidence Engine", value: "confidence", color: "border-l-blue-500" },
  { label: "Risk Engine", value: "risk", color: "border-l-amber-500" },
  { label: "Trade Planner", value: "plan", color: "border-l-emerald-500" },
  { label: "Decision Snapshot", value: "decision", color: "border-l-primary" },
]

export function DecisionFlow({ score, confidence, hasTradePlan, decision }: DecisionFlowProps) {
  return (
    <div className="rounded-lg border bg-card p-3 space-y-2">
      <div className="text-[9px] font-medium text-muted-foreground uppercase tracking-wider">Decision Flow</div>
      <div className="flex items-center justify-between gap-0">
        {STAGES.map((stage, i) => (
          <div key={stage.value} className="flex items-center flex-1">
            <motion.div
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: i * 0.15 }}
              className={cn("flex-1 rounded-md border border-l-4 p-2 text-center bg-muted/10", stage.color)}
            >
              <div className="text-[7px] text-muted-foreground uppercase">{stage.label}</div>
              <div className="text-[10px] font-bold font-mono mt-0.5">
                {stage.value === "score" ? score : stage.value === "confidence" ? `${confidence}%` : stage.value === "plan" ? (hasTradePlan ? "✓" : "—") : decision.replace(/_/g, " ")}
              </div>
            </motion.div>
            {i < STAGES.length - 1 && <ArrowDown className="w-3 h-3 text-muted-foreground mx-1 shrink-0 rotate-0 md:rotate-0" />}
          </div>
        ))}
      </div>
    </div>
  )
}
