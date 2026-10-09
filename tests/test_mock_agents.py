import json

import pytest

from app.agents.runtime import MockAgentAdapter
from app.models.domain import AnalysisResult, AnalyzerNarrative, OrchestrationPlan


def sample_analysis() -> AnalysisResult:
    return AnalysisResult.model_validate(
        {
            "metrics": {
                "latest_month": "2026-09",
                "monthly_income": 180000,
                "monthly_expenses": 120000,
                "net_cash_flow": 60000,
                "savings_rate": 33.3,
                "expense_trend_pct": 40,
                "debt_to_income_pct": 19.3,
                "cash_buffer_months": 1.7,
                "portfolio_value": 1080000,
                "top_holding_concentration_pct": 57.4,
            },
            "anomalies": [],
            "risk_signals": ["Expenses rose materially."],
            "risk_level": "HIGH",
            "trend": "deteriorating",
            "data_quality": {"status": "complete"},
        }
    )


@pytest.mark.asyncio
async def test_mock_orchestrator_returns_plan():
    agent = MockAgentAdapter("OrchestratorAgent")
    plan = await agent.run_structured(
        "PAYLOAD_JSON:\n" + json.dumps({"client_id": "CL001"}), OrchestrationPlan
    )
    assert plan.steps[:3] == ["fetch_context", "analyze", "advise"]


@pytest.mark.asyncio
async def test_mock_analyzer_returns_narrative():
    agent = MockAgentAdapter("AnalyzerAgent")
    analysis = sample_analysis()
    narrative = await agent.run_structured(
        "PAYLOAD_JSON:\n" + json.dumps({"analysis": analysis.model_dump(mode="json")}),
        AnalyzerNarrative,
    )
    assert narrative.confidence > 0
    assert "material" in narrative.executive_summary.lower()


@pytest.mark.asyncio
async def test_mock_advisor_produces_structured_output():
    from app.models.domain import AdvisoryOutput

    agent = MockAgentAdapter("AdvisorAgent")
    client_id = "CL001"
    payload = json.dumps({
        "client_id": client_id,
        "analysis": {
            "metrics": {
                "latest_month": "2026-09",
                "monthly_income": 100000,
                "monthly_expenses": 60000,
                "net_cash_flow": 40000,
                "savings_rate": 0.4,
                "expense_trend_pct": 0.0,
                "debt_to_income_pct": 0.0,
                "cash_buffer_months": 6.0,
                "portfolio_value": 100000,
                "top_holding_concentration_pct": 0.5,
            },
            "anomalies": [],
            "risk_signals": [],
            "risk_level": "LOW",
            "trend": "stable",
            "data_quality": {"status": "complete"},
        },
        "memory": [],
    })
    result = await agent.run_structured("PAYLOAD_JSON:\n" + payload, AdvisoryOutput)
    assert result.client_id == client_id
