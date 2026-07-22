"use client"

import { useState } from "react"
import { cn } from "@/lib/utils"
import type { OrderSide, OrderType } from "@/store/usePortfolioStore"

interface OrderEntryProps {
  onPlaceOrder: (request: {
    symbol: string; side: OrderSide; type: OrderType;
    quantity: number; price?: number; stopPrice?: number;
    stopLoss?: number; takeProfit?: number;
  }) => void
  disabled?: boolean
  className?: string
}

const SCAN_SYMBOLS = ["NIFTY 50", "BANK NIFTY", "SENSEX", "FIN NIFTY", "MIDCP NIFTY"]

export function OrderEntry({ onPlaceOrder, disabled, className }: OrderEntryProps) {
  const [symbol, setSymbol] = useState("NIFTY 50")
  const [side, setSide] = useState<OrderSide>("buy")
  const [type, setType] = useState<OrderType>("market")
  const [quantity, setQuantity] = useState(1)
  const [price, setPrice] = useState("")
  const [stopPrice, setStopPrice] = useState("")
  const [stopLoss, setStopLoss] = useState("")
  const [takeProfit, setTakeProfit] = useState("")

  const handleSubmit = () => {
    onPlaceOrder({
      symbol,
      side,
      type,
      quantity,
      price: price ? Number(price) : undefined,
      stopPrice: stopPrice ? Number(stopPrice) : undefined,
      stopLoss: stopLoss ? Number(stopLoss) : undefined,
      takeProfit: takeProfit ? Number(takeProfit) : undefined,
    })
  }

  return (
    <div className={cn("rounded-lg border bg-card p-3 space-y-2", className)}>
      <div className="text-[9px] font-medium text-muted-foreground uppercase tracking-wider">Order Entry</div>

      <div className="grid grid-cols-2 gap-1.5">
        {/* Symbol */}
        <div>
          <label className="text-[8px] text-muted-foreground block mb-0.5">Symbol</label>
          <select value={symbol} onChange={(e) => setSymbol(e.target.value)}
            className="w-full h-7 rounded border bg-muted/50 px-1.5 text-[10px] focus:outline-none">
            {SCAN_SYMBOLS.map((s) => <option key={s} value={s}>{s}</option>)}
          </select>
        </div>

        {/* Side */}
        <div>
          <label className="text-[8px] text-muted-foreground block mb-0.5">Side</label>
          <div className="flex gap-1">
            <button
              onClick={() => setSide("buy")}
              className={cn("flex-1 h-7 rounded text-[10px] font-medium transition-colors", side === "buy" ? "bg-emerald-500/20 text-emerald-500" : "bg-muted/30 text-muted-foreground hover:bg-accent")}
            >
              Buy
            </button>
            <button
              onClick={() => setSide("sell")}
              className={cn("flex-1 h-7 rounded text-[10px] font-medium transition-colors", side === "sell" ? "bg-red-500/20 text-red-500" : "bg-muted/30 text-muted-foreground hover:bg-accent")}
            >
              Sell
            </button>
          </div>
        </div>

        {/* Order Type */}
        <div>
          <label className="text-[8px] text-muted-foreground block mb-0.5">Type</label>
          <select value={type} onChange={(e) => setType(e.target.value as OrderType)}
            className="w-full h-7 rounded border bg-muted/50 px-1.5 text-[10px] focus:outline-none">
            <option value="market">Market</option>
            <option value="limit">Limit</option>
            <option value="stop">Stop</option>
            <option value="stop_limit">Stop Limit</option>
          </select>
        </div>

        {/* Quantity */}
        <div>
          <label className="text-[8px] text-muted-foreground block mb-0.5">Qty</label>
          <input type="number" value={quantity} onChange={(e) => setQuantity(Number(e.target.value))}
            className="w-full h-7 rounded border bg-muted/50 px-1.5 text-[10px] font-mono focus:outline-none" min={1} />
        </div>

        {/* Price (limit/stop) */}
        {type !== "market" && (
          <div>
            <label className="text-[8px] text-muted-foreground block mb-0.5">Price</label>
            <input type="number" value={price} onChange={(e) => setPrice(e.target.value)}
              className="w-full h-7 rounded border bg-muted/50 px-1.5 text-[10px] font-mono focus:outline-none" step={0.05} />
          </div>
        )}

        {/* Stop Price */}
        {(type === "stop" || type === "stop_limit") && (
          <div>
            <label className="text-[8px] text-muted-foreground block mb-0.5">Stop Price</label>
            <input type="number" value={stopPrice} onChange={(e) => setStopPrice(e.target.value)}
              className="w-full h-7 rounded border bg-muted/50 px-1.5 text-[10px] font-mono focus:outline-none" step={0.05} />
          </div>
        )}

        {/* SL */}
        <div>
          <label className="text-[8px] text-muted-foreground block mb-0.5">Stop Loss</label>
          <input type="number" value={stopLoss} onChange={(e) => setStopLoss(e.target.value)}
            className="w-full h-7 rounded border bg-muted/50 px-1.5 text-[10px] font-mono focus:outline-none" step={0.05} />
        </div>

        {/* TP */}
        <div>
          <label className="text-[8px] text-muted-foreground block mb-0.5">Take Profit</label>
          <input type="number" value={takeProfit} onChange={(e) => setTakeProfit(e.target.value)}
            className="w-full h-7 rounded border bg-muted/50 px-1.5 text-[10px] font-mono focus:outline-none" step={0.05} />
        </div>
      </div>

      <button
        onClick={handleSubmit}
        disabled={disabled}
        className={cn(
          "w-full h-8 rounded text-[10px] font-bold transition-colors",
          side === "buy"
            ? "bg-emerald-500/20 text-emerald-500 hover:bg-emerald-500/30"
            : "bg-red-500/20 text-red-500 hover:bg-red-500/30",
          disabled && "opacity-50 pointer-events-none",
        )}
      >
        {side === "buy" ? "BUY" : "SELL"} {symbol}
      </button>
    </div>
  )
}
