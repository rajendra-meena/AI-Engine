import { create } from "zustand"
import { persist } from "zustand/middleware"

/* ─── Position Sizing ─── */

export interface PositionConfig {
  capital: number
  riskPercent: number
  maxLoss: number
  quantity: number
  lotSize: number
  marginRequired: number
  brokerCharges: number
  taxes: number
  slippage: number
}

export type TradeStatus = "WAIT" | "READY" | "HIGH_CONVICTION" | "LOW_CONVICTION" | "NO_TRADE"

export type ChecklistStatus = "PASS" | "FAIL" | "WARNING"

export interface ChecklistItemData {
  id: string
  label: string
  status: ChecklistStatus
  detail?: string
}

export interface TimelineEvent {
  id: string
  label: string
  timestamp: string | null
  completed: boolean
  active: boolean
}

export interface RiskConfig {
  level: "LOW" | "MEDIUM" | "HIGH" | "EXTREME"
  score: number
  maxRiskPercent: number
}

export interface RewardConfig {
  expectedRR: number
  profitTargets: { target: number; probability: number }[]
  netRR: number
}

export interface ExecutionConfig {
  status: TradeStatus
  entryPrice: number | null
  entryConfirmed: boolean
  stoploss: number | null
  riskPoints: number | null
  direction: "LONG" | "SHORT" | "NONE"
  executionTimeframe: string
  institutionalBias: string
  marketCondition: string
  tradingPermission: string
}

interface TradePlannerState {
  /* ── Position sizing config (user-editable, persisted) ── */
  capital: number
  riskPercent: number
  lotSize: number
  brokerChargesPercent: number
  slippagePoints: number

  /* ── Derived / computed (set by service) ── */
  position: PositionConfig
  risk: RiskConfig
  reward: RewardConfig
  execution: ExecutionConfig
  checklist: ChecklistItemData[]
  timeline: TimelineEvent[]
  reasoning: string[]
  warnings: string[]

  /* ── Actions ── */
  setCapital: (capital: number) => void
  setRiskPercent: (percent: number) => void
  setLotSize: (size: number) => void
  setBrokerChargesPercent: (percent: number) => void
  setSlippagePoints: (points: number) => void
  setPosition: (config: Partial<PositionConfig>) => void
  setRisk: (risk: RiskConfig) => void
  setReward: (reward: RewardConfig) => void
  setExecution: (exec: Partial<ExecutionConfig>) => void
  setChecklist: (items: ChecklistItemData[]) => void
  setTimeline: (events: TimelineEvent[]) => void
  setReasoning: (lines: string[]) => void
  setWarnings: (warnings: string[]) => void
  reset: () => void
}

const defaultPosition = (capital: number): PositionConfig => ({
  capital,
  riskPercent: 2,
  maxLoss: capital * 0.02,
  quantity: 1,
  lotSize: 1,
  marginRequired: 0,
  brokerCharges: 0,
  taxes: 0,
  slippage: 0,
})

const defaultExecution: ExecutionConfig = {
  status: "WAIT",
  entryPrice: null,
  entryConfirmed: false,
  stoploss: null,
  riskPoints: null,
  direction: "NONE",
  executionTimeframe: "",
  institutionalBias: "NEUTRAL",
  marketCondition: "NORMAL",
  tradingPermission: "NONE",
}

const defaultChecklist: ChecklistItemData[] = [
  { id: "htf", label: "HTF Alignment", status: "WARNING", detail: "Awaiting data" },
  { id: "trend", label: "Trend Confirmation", status: "WARNING", detail: "Awaiting data" },
  { id: "structure", label: "Structure Valid", status: "WARNING", detail: "Awaiting data" },
  { id: "indicators", label: "Indicator Confirmation", status: "WARNING", detail: "Awaiting data" },
  { id: "patterns", label: "Pattern Confirmation", status: "WARNING", detail: "Awaiting data" },
  { id: "sr", label: "Support & Resistance", status: "WARNING", detail: "Awaiting data" },
  { id: "liquidity", label: "Liquidity Check", status: "WARNING", detail: "Awaiting data" },
  { id: "risk", label: "Risk Check", status: "WARNING", detail: "Awaiting data" },
]

export const useTradePlannerStore = create<TradePlannerState>()(
  persist(
    (set) => ({
      /* ── User-configurable ── */
      capital: 100000,
      riskPercent: 2,
      lotSize: 1,
      brokerChargesPercent: 0.05,
      slippagePoints: 1,

      /* ── Derived ── */
      position: defaultPosition(100000),
      risk: { level: "LOW", score: 0, maxRiskPercent: 2 },
      reward: { expectedRR: 0, profitTargets: [], netRR: 0 },
      execution: { ...defaultExecution },
      checklist: [...defaultChecklist],
      timeline: [],
      reasoning: [],
      warnings: [],

      /* ── Actions ── */
      setCapital: (capital) =>
        set((s) => ({
          capital,
          position: { ...s.position, capital, maxLoss: capital * (s.riskPercent / 100) },
        })),

      setRiskPercent: (riskPercent) =>
        set((s) => ({
          riskPercent,
          position: { ...s.position, riskPercent, maxLoss: s.capital * (riskPercent / 100) },
        })),

      setLotSize: (lotSize) =>
        set((s) => ({
          lotSize,
          position: { ...s.position, lotSize },
        })),

      setBrokerChargesPercent: (brokerChargesPercent) =>
        set((s) => ({
          brokerChargesPercent,
          position: { ...s.position, brokerCharges: (s.position.quantity * s.position.marginRequired) * (brokerChargesPercent / 100) },
        })),

      setSlippagePoints: (slippagePoints) => set({ slippagePoints }),

      setPosition: (config) =>
        set((s) => ({
          position: { ...s.position, ...config },
        })),

      setRisk: (risk) => set({ risk }),
      setReward: (reward) => set({ reward }),

      setExecution: (exec) =>
        set((s) => ({
          execution: { ...s.execution, ...exec },
        })),

      setChecklist: (checklist) => set({ checklist }),
      setTimeline: (timeline) => set({ timeline }),
      setReasoning: (reasoning) => set({ reasoning }),
      setWarnings: (warnings) => set({ warnings }),

      reset: () =>
        set({
          position: defaultPosition(100000),
          risk: { level: "LOW", score: 0, maxRiskPercent: 2 },
          reward: { expectedRR: 0, profitTargets: [], netRR: 0 },
          execution: { ...defaultExecution },
          checklist: [...defaultChecklist],
          timeline: [],
          reasoning: [],
          warnings: [],
        }),
    }),
    { name: "marketmind-trade-planner", partialize: (state) => ({ capital: state.capital, riskPercent: state.riskPercent, lotSize: state.lotSize, brokerChargesPercent: state.brokerChargesPercent, slippagePoints: state.slippagePoints }) }
  )
)
