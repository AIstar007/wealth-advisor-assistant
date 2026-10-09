from pathlib import Path
import json

from app.analysis.engine import analyze_finances
from app.config import settings
from app.models.domain import ClientFinancialData, DataQuality


DATA = Path("data/client_cl001.json")


def load_client() -> ClientFinancialData:
    return ClientFinancialData.model_validate(json.loads(DATA.read_text()))


def test_detects_spending_spike_and_high_risk():
    client = load_client()
    result = analyze_finances(client, DataQuality(status="complete"), settings)

    assert result.metrics.latest_month == "2026-09"
    assert result.metrics.expense_trend_pct > 25
    assert any(a.type == "spending_trend" for a in result.anomalies)
    assert result.risk_level in {"HIGH", "CRITICAL"}


def test_partial_context_is_flagged():
    client = load_client()
    quality = DataQuality(
        status="partial",
        missing_sources=["crm"],
        warnings=["CRM unavailable"],
        fallback_used=True,
    )
    result = analyze_finances(client, quality, settings)

    assert any(a.type == "data_quality" for a in result.anomalies)
    assert result.data_quality.fallback_used is True
