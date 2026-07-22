"use client"

import { cn } from "@/lib/utils"
import { Input } from "@/components/ui/input"
import type { PositionConfig } from "@/store/useTradePlannerStore"

interface PositionCardProps {
  position: PositionConfig
  capital: number
  riskPercent: number
  lotSize: number
  brokerChargesPercent: number
  slippagePoints: number
  onCapitalChange: (v: number) => void
  onRiskPercentChange: (v: number) => void
  onLotSizeChange: (v: number) => void
  onBrokerChargesChange: (v: number) => void
  onSlippageChange: (v: number) => void
}

function StatRow({ label, value, prefix, suffix, color }: {
  label: string
  value: string | number
  prefix?: string
  suffix?: string
  color?: string
}) {
  return (
    <div className="flex items-center justify-between py-0.5">
      <span className="text-[9px] text-muted-foreground">{label}</span>
      <span className={cn("text-[10px] font-mono font-medium", color)}>
        {prefix}{typeof value === "number" ? value.toLocaleString("en-IN", { maximumFractionDigits: 0 }) : value}{suffix}
      </span>
    </div>
  )
}

export function PositionCard({
  position, capital, riskPercent, lotSize, brokerChargesPercent, slippagePoints,
  onCapitalChange, onRiskPercentChange, onLotSizeChange, onBrokerChargesChange, onSlippageChange,
}: PositionCardProps) {
  return (
    <div className="rounded-md border bg-card p-2 space-y-2">
      <div className="text-[9px] font-medium text-muted-foreground uppercase tracking-wider">Position Sizing</div>

      {/* Editable inputs */}
      <div className="grid grid-cols-2 gap-1.5">
        <div>
          <label className="text-[8px] text-muted-foreground block mb-0.5">Capital (₹)</label>
          <Input
            type="number"
            value={capital}
            onChange={(e) => onCapitalChange(Number(e.target.value))}
            className="h-6 text-[10px]"
          />
        </div>
        <div>
          <label className="text-[8px] text-muted-foreground block mb-0.5">Risk %</label>
          <Input
            type="number"
            value={riskPercent}
            onChange={(e) => onRiskPercentChange(Number(e.target.value))}
            className="h-6 text-[10px]"
            step="0.1"
          />
        </div>
        <div>
          <label className="text-[8px] text-muted-foreground block mb-0.5">Lot Size</label>
          <Input
            type="number"
            value={lotSize}
            onChange={(e) => onLotSizeChange(Number(e.target.value))}
            className="h-6 text-[10px]"
          />
        </div>
        <div>
          <label className="text-[8px] text-muted-foreground block mb-0.5">Broker %</label>
          <Input
            type="number"
            value={brokerChargesPercent}
            onChange={(e) => onBrokerChargesChange(Number(e.target.value))}
            className="h-6 text-[10px]"
            step="0.01"
          />
        </div>
        <div>
          <label className="text-[8px] text-muted-foreground block mb-0.5">Slippage (pts)</label>
          <Input
            type="number"
            value={slippagePoints}
            onChange={(e) => onSlippageChange(Number(e.target.value))}
            className="h-6 text-[10px]"
            step="0.1"
          />
        </div>
      </div>

      <div className="border-t pt-1.5 space-y-0.5">
        <StatRow label="Max Loss" value={position.maxLoss} prefix="₹ " color="text-red-500" />
        <StatRow label="Quantity" value={position.quantity} />
        <StatRow label="Margin Required" value={position.marginRequired} prefix="₹ " />
        <StatRow label="Broker Charges" value={position.brokerCharges} prefix="₹ " />
        <StatRow label="Taxes (GST)" value={position.taxes} prefix="₹ " />
        <StatRow label="Slippage Cost" value={position.slippage} prefix="₹ " color="text-amber-500" />
      </div>
    </div>
  )
}
