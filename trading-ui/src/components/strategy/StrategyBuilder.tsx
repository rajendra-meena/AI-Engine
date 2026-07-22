"use client"

import { Plus, Save, Play, Trash2, BrainCircuit } from "lucide-react"
import { StrategyRuleBuilder } from "./StrategyRuleBuilder"
import type { Strategy, StrategyEntryRule, StrategyExitRule } from "@/store/useStrategyStore"

interface StrategyBuilderProps {
  strategy: Strategy
  onUpdate: (update: Partial<Strategy>) => void
  onSave: () => void
  onValidate: () => void
  onExplain: () => void
}

export function StrategyBuilder({ strategy, onUpdate, onSave, onValidate, onExplain }: StrategyBuilderProps) {
  const addEntryRule = () => {
    const rule: StrategyEntryRule = { id: `er_${Date.now()}`, label: "New Entry Rule", operator: "AND", conditions: [], priority: strategy.entryRules.length + 1 }
    onUpdate({ entryRules: [...strategy.entryRules, rule] })
  }

  const addExitRule = () => {
    const rule: StrategyExitRule = { id: `ex_${Date.now()}`, label: "New Exit Rule", operator: "AND", conditions: [], priority: strategy.exitRules.length + 1 }
    onUpdate({ exitRules: [...strategy.exitRules, rule] })
  }

  return (
    <div className="space-y-3">
      {/* Header */}
      <div className="flex items-center gap-2">
        <input
          type="text"
          value={strategy.name}
          onChange={(e) => onUpdate({ name: e.target.value })}
          className="flex-1 h-8 rounded border bg-card px-2 text-sm font-bold focus:outline-none focus:ring-1 focus:ring-primary"
          placeholder="Strategy Name"
        />
        <button onClick={onSave} className="flex items-center gap-1 rounded-md bg-primary/20 text-primary px-3 py-1.5 text-[10px] font-medium hover:bg-primary/30 transition-colors"><Save className="w-3 h-3" /> Save</button>
        <button onClick={onValidate} className="rounded-md border px-3 py-1.5 text-[10px] font-medium text-muted-foreground hover:bg-accent transition-colors"><Play className="w-3 h-3" /> Validate</button>
        <button onClick={onExplain} className="rounded-md border px-3 py-1.5 text-[10px] font-medium text-muted-foreground hover:bg-accent transition-colors"><BrainCircuit className="w-3 h-3" /> AI Explain</button>
      </div>

      <textarea
        value={strategy.description}
        onChange={(e) => onUpdate({ description: e.target.value })}
        className="w-full h-14 rounded border bg-card px-2 py-1 text-[10px] focus:outline-none focus:ring-1 focus:ring-primary resize-none"
        placeholder="Strategy description..."
      />

      {/* Entry Rules */}
      <div>
        <div className="flex items-center justify-between mb-1">
          <span className="text-[9px] font-medium text-muted-foreground uppercase tracking-wider">Entry Rules</span>
          <button onClick={addEntryRule} className="flex items-center gap-1 text-[9px] text-primary hover:text-primary/80 transition-colors"><Plus className="w-3 h-3" /> Add Rule</button>
        </div>
        <div className="space-y-1.5">
          {strategy.entryRules.map((rule, i) => (
            <StrategyRuleBuilder
              key={rule.id}
              rule={rule}
              onUpdate={(updated) => {
                const rules = [...strategy.entryRules]
                rules[i] = updated
                onUpdate({ entryRules: rules })
              }}
              onDelete={() => onUpdate({ entryRules: strategy.entryRules.filter((_, j) => j !== i) })}
            />
          ))}
          {strategy.entryRules.length === 0 && (
            <div className="rounded-lg border border-dashed p-4 text-center text-[10px] text-muted-foreground">
              No entry rules. Click Add Rule to start building.
            </div>
          )}
        </div>
      </div>

      {/* Exit Rules */}
      <div>
        <div className="flex items-center justify-between mb-1">
          <span className="text-[9px] font-medium text-muted-foreground uppercase tracking-wider">Exit Rules</span>
          <button onClick={addExitRule} className="flex items-center gap-1 text-[9px] text-primary hover:text-primary/80 transition-colors"><Plus className="w-3 h-3" /> Add Rule</button>
        </div>
        <div className="space-y-1.5">
          {strategy.exitRules.map((rule, i) => (
            <StrategyRuleBuilder
              key={rule.id}
              rule={rule}
              onUpdate={(updated) => {
                const rules = [...strategy.exitRules]
                rules[i] = updated
                onUpdate({ exitRules: rules })
              }}
              onDelete={() => onUpdate({ exitRules: strategy.exitRules.filter((_, j) => j !== i) })}
            />
          ))}
          {strategy.exitRules.length === 0 && (
            <div className="rounded-lg border border-dashed p-4 text-center text-[10px] text-muted-foreground">
              No exit rules. Add rules to define when to exit positions.
            </div>
          )}
        </div>
      </div>

      {/* Tags */}
      <div>
        <div className="text-[9px] font-medium text-muted-foreground uppercase tracking-wider mb-1">Tags</div>
        <div className="flex flex-wrap gap-1">
          {strategy.tags.map((tag, i) => (
            <span key={i} className="inline-flex items-center gap-1 rounded bg-muted/30 px-1.5 py-0.5 text-[8px] font-medium">
              {tag}
              <button onClick={() => onUpdate({ tags: strategy.tags.filter((_, j) => j !== i) })} className="text-muted-foreground hover:text-red-500"><Trash2 className="w-2 h-2" /></button>
            </span>
          ))}
          <input
            type="text"
            placeholder="Add tag..."
            className="h-5 rounded border-0 bg-transparent px-1 text-[8px] focus:outline-none w-20"
            onKeyDown={(e) => {
              if (e.key === "Enter" && e.currentTarget.value) {
                onUpdate({ tags: [...strategy.tags, e.currentTarget.value] })
                e.currentTarget.value = ""
              }
            }}
          />
        </div>
      </div>
    </div>
  )
}
