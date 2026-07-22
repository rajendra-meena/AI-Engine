"use client"

import { Plus } from "lucide-react"
import { StrategyCondition } from "./StrategyCondition"
import type { StrategyCondition as SC, StrategyEntryRule, RuleOperator } from "@/store/useStrategyStore"

interface StrategyRuleBuilderProps {
  rule: StrategyEntryRule
  onUpdate: (rule: StrategyEntryRule) => void
  onDelete: () => void
}

export function StrategyRuleBuilder({ rule, onUpdate, onDelete }: StrategyRuleBuilderProps) {
  const handleConditionChange = (index: number, update: Partial<SC>) => {
    const updated = [...rule.conditions]
    updated[index] = { ...updated[index], ...update }
    onUpdate({ ...rule, conditions: updated })
  }

  const handleRemoveCondition = (index: number) => {
    onUpdate({ ...rule, conditions: rule.conditions.filter((_, i) => i !== index) })
  }

  const handleAddCondition = () => {
    const newCond: SC = {
      id: `cond_${Date.now()}`,
      type: "ema_cross",
      operator: ">",
      value: 50,
      label: "",
    }
    onUpdate({ ...rule, conditions: [...rule.conditions, newCond] })
  }

  return (
    <div className="rounded-lg border bg-card p-3 space-y-1.5">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <input
            type="text"
            value={rule.label}
            onChange={(e) => onUpdate({ ...rule, label: e.target.value })}
            className="h-6 rounded border-0 bg-transparent px-1 text-[10px] font-medium focus:outline-none focus:ring-1 focus:ring-primary"
            placeholder="Rule name..."
          />
          <select
            value={rule.operator}
            onChange={(e) => onUpdate({ ...rule, operator: e.target.value as RuleOperator })}
            className="h-6 rounded border bg-muted/30 px-1 text-[8px] font-mono focus:outline-none"
          >
            <option value="AND">ALL (AND)</option>
            <option value="OR">ANY (OR)</option>
            <option value="NOT">NONE (NOT)</option>
          </select>
        </div>
        <div className="flex items-center gap-1">
          <span className="text-[8px] text-muted-foreground">Priority: {rule.priority}</span>
          <button onClick={onDelete} className="rounded p-0.5 text-muted-foreground hover:text-red-500 transition-colors text-[9px]">Delete</button>
        </div>
      </div>

      <div className="space-y-0">
        {rule.conditions.map((cond, i) => (
          <StrategyCondition key={cond.id} condition={cond} index={i} onChange={handleConditionChange} onRemove={handleRemoveCondition} />
        ))}
      </div>

      <button onClick={handleAddCondition} className="flex items-center gap-1 text-[9px] text-muted-foreground hover:text-primary transition-colors">
        <Plus className="w-3 h-3" /> Add Condition
      </button>
    </div>
  )
}
