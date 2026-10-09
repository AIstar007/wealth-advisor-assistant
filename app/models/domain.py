from __future__ import annotations

from datetime import date
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

RiskLevel = Literal["LOW", "MEDIUM", "HIGH", "CRITICAL"]
Priority = Literal["LOW", "MEDIUM", "HIGH", "CRITICAL"]


class Transaction(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str
    date: date
    description: str
    category: str
    amount: float = Field(gt=0)
    transaction_type: Literal["debit", "credit"]
    currency: str = "INR"
    merchant: str | None = None


class MonthlySnapshot(BaseModel):
    month: str = Field(pattern=r"^\d{4}-\d{2}$")
    income: float = Field(ge=0)
    expenses: float = Field(ge=0)
    savings: float = 0
    investments: float = Field(ge=0)
    debt_balance: float = Field(ge=0)


class Holding(BaseModel):
    symbol: str
    asset_class: str
    market_value: float = Field(ge=0)
    cost_basis: float = Field(ge=0)


class Liability(BaseModel):
    name: str
    outstanding: float = Field(ge=0)
    interest_rate: float | None = Field(default=None, ge=0)
    monthly_payment: float = Field(default=0, ge=0)


class FinancialGoal(BaseModel):
    name: str
    target_amount: float = Field(gt=0)
    target_date: date | None = None
    priority: Priority = "MEDIUM"


class ClientFinancialData(BaseModel):
    model_config = ConfigDict(extra="ignore")
    client_id: str = Field(min_length=1)
    as_of_date: date
    risk_profile: Literal["conservative", "moderate", "aggressive"]
    annual_income: float = Field(ge=0)
    cash_balance: float = Field(ge=0)
    monthly_history: list[MonthlySnapshot] = Field(min_length=1)
    transactions: list[Transaction] = Field(default_factory=list)
    holdings: list[Holding] = Field(default_factory=list)
    liabilities: list[Liability] = Field(default_factory=list)
    goals: list[FinancialGoal] = Field(default_factory=list)

    @field_validator("monthly_history")
    @classmethod
    def sort_months(cls, value: list[MonthlySnapshot]) -> list[MonthlySnapshot]:
        return sorted(value, key=lambda x: x.month)


class CRMContext(BaseModel):
    client_id: str
    advisor_notes: str = ""
    life_events: list[str] = Field(default_factory=list)
    stated_goals: list[str] = Field(default_factory=list)
    last_contact_date: date | None = None


class DataQuality(BaseModel):
    status: Literal["complete", "partial", "degraded"]
    missing_sources: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    fallback_used: bool = False


class OrchestrationPlan(BaseModel):
    objective: str
    steps: list[Literal["fetch_context", "analyze", "advise", "review"]]
    analysis_focus: list[str]
    human_review_min_risk: RiskLevel
    rationale: str


class Anomaly(BaseModel):
    anomaly_id: str
    type: Literal[
        "transaction",
        "spending_trend",
        "cash_buffer",
        "debt",
        "concentration",
        "data_quality",
    ]
    severity: RiskLevel
    score: float = Field(ge=0)
    description: str
    evidence: dict[str, Any] = Field(default_factory=dict)


class FinancialMetrics(BaseModel):
    latest_month: str
    monthly_income: float
    monthly_expenses: float
    net_cash_flow: float
    savings_rate: float
    expense_trend_pct: float
    debt_to_income_pct: float
    cash_buffer_months: float
    portfolio_value: float
    top_holding_concentration_pct: float


class AnalysisResult(BaseModel):
    metrics: FinancialMetrics
    anomalies: list[Anomaly]
    risk_signals: list[str]
    risk_level: RiskLevel
    trend: Literal["improving", "stable", "deteriorating"]
    data_quality: DataQuality


class AnalyzerNarrative(BaseModel):
    executive_summary: str
    risk_rationale: str
    priority_focus: list[str]
    confidence: float = Field(ge=0, le=1)


class AdvisoryRecommendation(BaseModel):
    recommendation_id: str
    priority: Priority
    action: str
    rationale: str
    evidence_ids: list[str] = Field(default_factory=list)
    advisor_only: bool = False


class AdvisoryOutput(BaseModel):
    client_id: str
    summary: str
    recommendations: list[AdvisoryRecommendation]
    assumptions: list[str] = Field(default_factory=list)
    review_required: bool
    confidence: float = Field(ge=0, le=1)
    disclaimer: str = "Decision support for a human advisor; not individualized financial advice."


class RunInput(BaseModel):
    run_id: str
    financial_data: ClientFinancialData


class FetchedEnvelope(BaseModel):
    run_id: str
    plan: OrchestrationPlan
    financial_data: ClientFinancialData
    crm_context: CRMContext | None = None
    data_quality: DataQuality


class AnalysisInputEnvelope(BaseModel):
    run_id: str
    plan: OrchestrationPlan
    financial_data: ClientFinancialData
    crm_context: CRMContext | None = None
    data_quality: DataQuality


class AdvisorEnvelope(BaseModel):
    run_id: str
    plan: OrchestrationPlan
    financial_data: ClientFinancialData
    crm_context: CRMContext | None = None
    data_quality: DataQuality
    analysis: AnalysisResult
    analyzer_narrative: AnalyzerNarrative
    advisory: AdvisoryOutput | None = None
    memory_written: bool = False


class HumanReviewRequest(BaseModel):
    run_id: str
    client_id: str
    risk_level: RiskLevel
    summary: str
    recommendations: list[AdvisoryRecommendation]
    prompt: str


class ReviewMetadata(BaseModel):
    status: Literal["not_required", "pending", "approved", "overridden", "rejected"]
    reviewer_comment: str | None = None
    reviewed_at: str | None = None


class FinalAdvisory(BaseModel):
    client_id: str
    run_id: str
    plan: OrchestrationPlan
    data_quality: DataQuality
    analysis: AnalysisResult
    analyzer_narrative: AnalyzerNarrative
    advisory: AdvisoryOutput
    review: ReviewMetadata
    memory_written: bool


class ClientAnalysisRequest(BaseModel):
    financial_data: ClientFinancialData


class ReviewSubmission(BaseModel):
    decision: str = Field(min_length=1, max_length=2000)


class RunAcceptedResponse(BaseModel):
    run_id: str
    status: Literal["completed", "pending_review"]
    result: FinalAdvisory | None = None
    review_request: HumanReviewRequest | None = None
