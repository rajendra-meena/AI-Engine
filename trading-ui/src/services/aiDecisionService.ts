/* eslint-disable @typescript-eslint/no-explicit-any */
"use client"

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"

export interface FactorScore {
  name: string
  score: number
  weight: number
  detail: string
}

export interface DetailedConfidenceResponse {
  overall_confidence: number
  grade: string
  factor_breakdown: FactorScore[]
  reasoning: string[]
}

export interface TradeQualityResponse {
  total_score: number
  grade: string
  factor_scores: FactorScore[]
  reasoning: string[]
  warnings: string[]
}

export interface MTFBreakdown {
  timeframe: string
  bias: string
  agrees: boolean
  weight: number
}

export interface MTFAgreementResponse {
  agreement_percent: number
  weighted_agreement: number
  breakdown: MTFBreakdown[]
  conflicts_found: { type: string; timeframe: string; bias: string; severity: string }[]
  status: string
}

export interface SignalValidation {
  signal: string
  status: string
  reason: string
  severity: string
}

export interface SignalValidationResponse {
  validations: SignalValidation[]
  overall_status: string
  pass_count: number
  warning_count: number
  block_count: number
}

export interface FalseSignalDetection {
  type: string
  detected: boolean
  confidence: number
  reason: string
}

export interface FalseSignalResponse {
  is_false_signal: boolean
  detections: FalseSignalDetection[]
  reject_reasons: string[]
}

export interface AIExplanationResponse {
  decision_explanation: {
    primary_reason: string
    supporting_factors: { factor: string; impact: string; detail: string }[]
    blocking_factors: { factor: string; impact: string; detail: string }[]
  }
  why_buy: string
  why_sell: string
  why_no_trade: string
}

export interface ApprovalGate {
  name: string
  passed: boolean
  value: any
  threshold: any
  detail: string
}

export interface ApprovalResponse {
  approved: boolean
  decision: string
  gates: ApprovalGate[]
  blocking_reasons: string[]
}

export interface ValidationResponse {
  signal_validations: SignalValidationResponse
  trade_quality: TradeQualityResponse
  approval: ApprovalResponse
}

export interface EnrichedDecisionResponse {
  decision: string
  score: number
  confidence: number
  signal_validations: SignalValidationResponse
  trade_quality: TradeQualityResponse
  mtf_agreement: MTFAgreementResponse
  false_signal_check: FalseSignalResponse
  detailed_confidence: DetailedConfidenceResponse
  confidence_adjustment: any
  adjusted_confidence: number
  ai_explanation: AIExplanationResponse
  approval: ApprovalResponse
  is_trade_eligible: boolean
}

export interface DatasetStats {
  total_records: number
  by_decision: Record<string, number>
  by_grade: Record<string, number>
  by_outcome: Record<string, number>
  latest_timestamp: string | null
}

class AIDecisionService {
  private base = API_BASE

  async getConfidence(symbol = "NIFTY 50"): Promise<DetailedConfidenceResponse> {
    const res = await fetch(`${this.base}/api/ai/confidence?symbol=${encodeURIComponent(symbol)}`)
    if (!res.ok) throw new Error("Failed to fetch confidence")
    return res.json()
  }

  async getDecision(symbol = "NIFTY 50"): Promise<EnrichedDecisionResponse> {
    const res = await fetch(`${this.base}/api/ai/decision?symbol=${encodeURIComponent(symbol)}`)
    if (!res.ok) throw new Error("Failed to fetch enriched decision")
    return res.json()
  }

  async getQuality(symbol = "NIFTY 50"): Promise<TradeQualityResponse> {
    const res = await fetch(`${this.base}/api/ai/quality?symbol=${encodeURIComponent(symbol)}`)
    if (!res.ok) throw new Error("Failed to fetch quality")
    return res.json()
  }

  async getExplain(symbol = "NIFTY 50"): Promise<AIExplanationResponse> {
    const res = await fetch(`${this.base}/api/ai/explain?symbol=${encodeURIComponent(symbol)}`)
    if (!res.ok) throw new Error("Failed to fetch explanation")
    return res.json()
  }

  async getAgreement(symbol = "NIFTY 50"): Promise<MTFAgreementResponse> {
    const res = await fetch(`${this.base}/api/ai/agreement?symbol=${encodeURIComponent(symbol)}`)
    if (!res.ok) throw new Error("Failed to fetch agreement")
    return res.json()
  }

  async getRejections(symbol = "NIFTY 50"): Promise<FalseSignalResponse> {
    const res = await fetch(`${this.base}/api/ai/rejections?symbol=${encodeURIComponent(symbol)}`)
    if (!res.ok) throw new Error("Failed to fetch rejections")
    return res.json()
  }

  async getApproval(symbol = "NIFTY 50"): Promise<ApprovalResponse> {
    const res = await fetch(`${this.base}/api/ai/approval?symbol=${encodeURIComponent(symbol)}`)
    if (!res.ok) throw new Error("Failed to fetch approval")
    return res.json()
  }

  async validate(symbol = "NIFTY 50"): Promise<ValidationResponse> {
    const res = await fetch(`${this.base}/api/ai/validate?symbol=${encodeURIComponent(symbol)}`, {
      method: "POST",
    })
    if (!res.ok) throw new Error("Validation failed")
    return res.json()
  }

  async getDatasetStats(): Promise<DatasetStats> {
    const res = await fetch(`${this.base}/api/ai/dataset/stats`)
    if (!res.ok) throw new Error("Failed to fetch dataset stats")
    return res.json()
  }
}

export const aiDecisionService = new AIDecisionService()
