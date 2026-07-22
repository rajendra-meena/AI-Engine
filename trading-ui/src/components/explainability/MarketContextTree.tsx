"use client"

import { useState } from "react"
import { cn } from "@/lib/utils"
import { ChevronRight, ChevronDown } from "lucide-react"
import type { ContextNode } from "@/services/explainabilityService"

interface MarketContextTreeProps {
  nodes: ContextNode[]
}

function TreeNode({ node, depth = 0 }: { node: ContextNode; depth?: number }) {
  const [open, setOpen] = useState(depth < 1)
  const hasChildren = node.children && node.children.length > 0

  return (
    <div>
      <div
        className={cn("flex items-center gap-1.5 py-1 cursor-pointer hover:bg-muted/20 rounded px-1", depth > 0 && "ml-4")}
        onClick={() => hasChildren && setOpen(!open)}
      >
        {hasChildren ? (
          open ? <ChevronDown className="w-3 h-3 text-muted-foreground shrink-0" /> : <ChevronRight className="w-3 h-3 text-muted-foreground shrink-0" />
        ) : <div className="w-3 shrink-0" />}
        <span className="text-[9px] text-muted-foreground min-w-[80px]">{node.label}</span>
        <span className="text-[10px] font-medium" style={node.color ? { color: node.color } : undefined}>{node.value}</span>
      </div>
      {hasChildren && open && node.children!.map((child, i) => <TreeNode key={i} node={child} depth={depth + 1} />)}
    </div>
  )
}

export function MarketContextTree({ nodes }: MarketContextTreeProps) {
  return (
    <div className="rounded-lg border bg-card p-3 space-y-1">
      <div className="text-[9px] font-medium text-muted-foreground uppercase tracking-wider">Market Context</div>
      {nodes.map((node, i) => <TreeNode key={i} node={node} />)}
    </div>
  )
}
