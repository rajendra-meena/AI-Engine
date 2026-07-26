"use client"

import { useState, useEffect, useCallback } from "react"
import {
  BrainCircuit, Shield, Award, GitBranch, Radio, Ban, FileText, Database,
  RefreshCw, CircleCheck, CircleX,
} from "lucide-react"
import { aiDecisionService } from "@/services/aiDecisionService"
import type {
  DetailedConfidenceResponse, TradeQualityResponse, MTFAgreementResponse,
  SignalValidationResponse, FalseSignalResponse, AIExplanationResponse, ApprovalResponse,
} from "@/services/aiDecisionService"
import { MetricCard } from "./MetricCard"
import { ConfidenceDetailPanel } from "./ConfidenceDetailPanel"
import { QualityGradePanel } from "./QualityGradePanel"
import { AgreementBreakdownPanel } from "./AgreementBreakdownPanel"
import { SignalValidationPanel } from "./SignalValidationPanel"
import { FalseSignalPanel } from "./FalseSignalPanel"
import { ExplanationPanel } from "./ExplanationPanel"
import { DatasetStatsPanel } from "./DatasetStatsPanel"

type TabId = "overview" | "confidence" | "quality" | "agreement" | "signals" | "rejections" | "explanation" | "dataset"

export function AIDecisionValidationDashboard() {
  const [activeTab, setActiveTab] = useState<TabId>("overview")
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const [confidence, setConfidence] = useState<DetailedConfidenceResponse | null>(null)
  const [quality, setQuality] = useState<TradeQualityResponse | null>(null)
  const [agreement, setAgreement] = useState<MTFAgreementResponse | null>(null)
  const [signals, setSignals] = useState<SignalValidationResponse | null>(null)
  const [rejections, setRejections] = useState<FalseSignalResponse | null>(null)
  const [explanation, setExplanation] = useState<AIExplanationResponse | null>(null)
  const [approval, setApproval] = useState<ApprovalResponse | null>(null)

  const symbol = "NIFTY 50"

  const fetchAll = useCallback(async () => {
    setError(null)
    try {
      const [c, q, a, rj, ex, ap, sv] = await Promise.all([
        aiDecisionService.getConfidence(symbol).catch(() => null),
        aiDecisionService.getQuality(symbol).catch(() => null),
        aiDecisionService.getAgreement(symbol).catch(() => null),
        aiDecisionService.getRejections(symbol).catch(() => null),
        aiDecisionService.getExplain(symbol).catch(() => null),
        aiDecisionService.getApproval(symbol).catch(() => null),
        aiDecisionService.validate(symbol).catch(() => null),
      ])
      if (c) setConfidence(c)
      if (q) setQuality(q)
      if (a) setAgreement(a)
      if (rj) setRejections(rj)
      if (ex) setExplanation(ex)
      if (ap) setApproval(ap)
      if (sv?.signal_validations) setSignals(sv.signal_validations)
      if (sv?.trade_quality) setQuality(sv.trade_quality)
      if (sv?.approval) setApproval(sv.approval)
    } catch {
      setError("Failed to load AI decision data")
    }
    setLoading(false)
  }, [symbol])

  useEffect(() => {
    const t = setTimeout(() => fetchAll(), 0)
    const interval = setInterval(fetchAll, 30000)
    return () => { clearTimeout(t); clearInterval(interval) }
  }, [fetchAll])

  const tabs: { id: TabId; label: string; icon: React.ReactNode }[] = [
    { id: "overview", label: "Overview", icon: <BrainCircuit className="w-3.5 h-3.5" /> },
    { id: "confidence", label: "Confidence", icon: <Shield className="w-3.5 h-3.5" /> },
    { id: "quality", label: "Quality", icon: <Award className="w-3.5 h-3.5" /> },
    { id: "agreement", label: "Agreement", icon: <GitBranch className="w-3.5 h-3.5" /> },
    { id: "signals", label: "Signals", icon: <Radio className="w-3.5 h-3.5" /> },
    { id: "rejections", label: "Rejections", icon: <Ban className="w-3.5 h-3.5" /> },
    { id: "explanation", label: "Explanation", icon: <FileText className="w-3.5 h-3.5" /> },
    { id: "dataset", label: "Dataset", icon: <Database className="w-3.5 h-3.5" /> },
  ]

  const isEligible = approval?.approved
  const allPassed = signals?.overall_status === "PASS"

  return (
    <div className="space-y-4">
      {/* Header */}
      <div className="flex items-center gap-2">
        <BrainCircuit className="w-5 h-5 text-primary" />
        <h1 className="text-lg font-bold">AI Decision Center</h1>
        {approval && (
          <span className={`ml-auto flex items-center gap-1 px-2 py-0.5 rounded text-[10px] font-bold border ${
            isEligible ? "bg-emerald-500/10 text-emerald-500 border-emerald-500/20" : "bg-red-500/10 text-red-500 border-red-500/20"
          }`}>
            {isEligible ? <><CircleCheck className="w-3 h-3" /> TRADE ELIGIBLE</> : <><CircleX className="w-3 h-3" /> NO TRADE</>}
          </span>
        )}
        <button onClick={fetchAll} className="p-1 rounded text-muted-foreground hover:text-foreground hover:bg-accent" disabled={loading}>
          <RefreshCw className={`w-3.5 h-3.5 ${loading ? "animate-spin" : ""}`} />
        </button>
      </div>

      {error && <div className="rounded border border-red-500/20 bg-red-500/5 p-2 text-[10px] text-red-600">{error}</div>}

      {/* Tabs */}
      <div className="flex gap-1 border-b overflow-x-auto">
        {tabs.map(tab => (
          <button key={tab.id} onClick={() => setActiveTab(tab.id)}
            className={`flex items-center gap-1 px-3 py-1.5 text-[10px] font-medium border-b-2 transition-colors shrink-0 ${
              activeTab === tab.id ? "border-primary text-foreground" : "border-transparent text-muted-foreground hover:text-foreground"
            }`}>
            {tab.icon} {tab.label}
          </button>
        ))}
      </div>

      <div className="min-h-[400px]">
        {/* Overview Tab */}
        {activeTab === "overview" && (
          <div className="space-y-4">
            <div className="grid grid-cols-4 gap-3">
              <MetricCard label="Confidence" value={`${confidence?.overall_confidence ?? 0}%`}
                color={(confidence?.overall_confidence ?? 0) >= 80 ? "text-emerald-500" : (confidence?.overall_confidence ?? 0) >= 60 ? "text-amber-500" : "text-red-500"} />
              <MetricCard label="Trade Quality" value={quality?.grade ?? "—"}
                color={quality?.grade && !["D", "REJECT"].includes(quality.grade) ? "text-emerald-500" : "text-red-500"} />
              <MetricCard label="MTF Agreement" value={`${agreement?.agreement_percent ?? 0}%`}
                color={(agreement?.agreement_percent ?? 0) >= 80 ? "text-emerald-500" : (agreement?.agreement_percent ?? 0) >= 60 ? "text-amber-500" : "text-red-500"} />
              <MetricCard label="Approval" value={isEligible ? "ELIGIBLE" : "BLOCKED"}
                color={isEligible ? "text-emerald-500" : "text-red-500"} />
            </div>

            {/* Signal Status Summary */}
            <div className="rounded-lg border bg-card p-3">
              <div className="text-[9px] text-muted-foreground uppercase mb-2">Signal Validations</div>
              <div className="grid grid-cols-3 gap-2 text-[10px]">
                <div className="flex items-center gap-1">
                  <CircleCheck className="w-3 h-3 text-emerald-500" />
                  <span>{signals?.pass_count ?? 0} Passed</span>
                </div>
                <div className="flex items-center gap-1">
                  <CircleX className="w-3 h-3 text-amber-500" />
                  <span>{signals?.warning_count ?? 0} Warnings</span>
                </div>
                <div className="flex items-center gap-1">
                  <CircleX className="w-3 h-3 text-red-500" />
                  <span>{signals?.block_count ?? 0} Blocked</span>
                </div>
              </div>
            </div>

            {/* Approval Gates */}
            {approval && (
              <div className="rounded-lg border bg-card p-3">
                <div className="text-[9px] text-muted-foreground uppercase mb-2">Approval Gates</div>
                <div className="space-y-1 text-[10px]">
                  {approval.gates.map((g) => (
                    <div key={g.name} className="flex items-center gap-2">
                      {g.passed
                        ? <CircleCheck className="w-3 h-3 text-emerald-500 shrink-0" />
                        : <CircleX className="w-3 h-3 text-red-500 shrink-0" />}
                      <span className="font-medium capitalize w-28">{g.name.replace(/_/g, " ")}</span>
                      <span className="text-muted-foreground flex-1">{g.detail}</span>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* False Signal Alert */}
            {rejections?.is_false_signal && (
              <div className="rounded-lg border border-red-500/20 bg-red-500/5 p-3 text-[10px] text-red-600">
                <strong>⚠ False Signal Detected:</strong> {rejections.reject_reasons.join("; ")}
              </div>
            )}
          </div>
        )}

        {activeTab === "confidence" && <ConfidenceDetailPanel data={confidence} />}
        {activeTab === "quality" && <QualityGradePanel data={quality} />}
        {activeTab === "agreement" && <AgreementBreakdownPanel data={agreement} />}
        {activeTab === "signals" && <SignalValidationPanel data={signals} />}
        {activeTab === "rejections" && <FalseSignalPanel data={rejections} />}
        {activeTab === "explanation" && <ExplanationPanel data={explanation} />}
        {activeTab === "dataset" && <DatasetStatsPanel />}
      </div>
    </div>
  )
}
