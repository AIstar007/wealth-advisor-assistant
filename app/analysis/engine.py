from __future__ import annotations

from statistics import mean, median, pstdev
from typing import Iterable

from app.config import Settings
from app.models.domain import (
    AnalysisResult,
    Anomaly,
    ClientFinancialData,
    DataQuality,
    FinancialMetrics,
)


_RISK_ORDER = {"LOW": 0, "MEDIUM": 1, "HIGH": 2, "CRITICAL": 3}


def _safe_pct(numerator: float, denominator: float) -> float:
    return 0.0 if denominator == 0 else (numerator / denominator) * 100.0


def _risk_max(current: str, candidate: str) -> str:
    return candidate if _RISK_ORDER[candidate] > _RISK_ORDER[current] else current


def _robust_z(value: float, population: Iterable[float]) -> float:
    values = list(population)
    if len(values) < 3:
        return 0.0
    med = median(values)
    deviations = [abs(x - med) for x in values]
    mad = median(deviations)
    if mad == 0:
        stdev = pstdev(values)
        return abs(value - med) / stdev if stdev else 0.0
    # 0.6745 scales MAD to a normal-equivalent z-score.
    return abs(0.6745 * (value - med) / mad)


def _trend(current: float, prior: float) -> str:
    if prior == 0:
        return "stable"
    delta = (current - prior) / prior
    if delta <= -0.10:
        return "improving"
    if delta >= 0.10:
        return "deteriorating"
    return "stable"


def analyze_finances(
    data: ClientFinancialData,
    data_quality: DataQuality,
    settings: Settings,
) -> AnalysisResult:
    latest = data.monthly_history[-1]
    prior_months = data.monthly_history[:-1]
    prior_expenses = [m.expenses for m in prior_months[-4:]]
    expense_baseline = mean(prior_expenses) if prior_expenses else latest.expenses
    expense_trend_pct = _safe_pct(latest.expenses - expense_baseline, expense_baseline)

    total_debt = sum(liability.outstanding for liability in data.liabilities)
    latest_annualized_income = latest.income * 12 if latest.income else data.annual_income
    debt_to_income_pct = _safe_pct(total_debt, latest_annualized_income)
    cash_buffer_months = 0.0 if latest.expenses == 0 else data.cash_balance / latest.expenses

    portfolio_value = sum(holding.market_value for holding in data.holdings)
    top_holding = max((h.market_value for h in data.holdings), default=0.0)
    concentration_pct = _safe_pct(top_holding, portfolio_value)

    metrics = FinancialMetrics(
        latest_month=latest.month,
        monthly_income=latest.income,
        monthly_expenses=latest.expenses,
        net_cash_flow=latest.income - latest.expenses,
        savings_rate=max(0.0, min(100.0, _safe_pct(latest.income - latest.expenses, latest.income))),
        expense_trend_pct=expense_trend_pct,
        debt_to_income_pct=debt_to_income_pct,
        cash_buffer_months=cash_buffer_months,
        portfolio_value=portfolio_value,
        top_holding_concentration_pct=concentration_pct,
    )

    anomalies: list[Anomaly] = []
    risk_level = "LOW"
    risk_signals: list[str] = []

    debit_transactions = sorted(
        [t for t in data.transactions if t.transaction_type == "debit"],
        key=lambda t: t.date,
    )
    for idx, transaction in enumerate(debit_transactions):
        historical_debits = [t.amount for t in debit_transactions[:idx]]
        if len(historical_debits) < 3:
            continue
        z = _robust_z(transaction.amount, historical_debits)
        if z >= settings.anomaly_z_threshold:
            severity = "CRITICAL" if z >= 6 else "HIGH" if z >= 4 else "MEDIUM"
            anomaly = Anomaly(
                anomaly_id=f"TX-{transaction.id}",
                type="transaction",
                severity=severity,
                score=round(z, 2),
                description=(
                    f"Transaction {transaction.id} is unusually large relative to the client's "
                    "historical debit pattern."
                ),
                evidence={
                    "transaction_amount": transaction.amount,
                    "category": transaction.category,
                    "date": str(transaction.date),
                    "robust_z_score": round(z, 2),
                },
            )
            anomalies.append(anomaly)
            risk_signals.append(f"Unusual transaction detected: {transaction.description}.")
            risk_level = _risk_max(risk_level, severity)

    if expense_trend_pct >= settings.spending_spike_pct * 100:
        severity = "HIGH" if expense_trend_pct >= 50 else "MEDIUM"
        anomalies.append(
            Anomaly(
                anomaly_id="TREND-EXPENSE",
                type="spending_trend",
                severity=severity,
                score=round(expense_trend_pct / 100, 2),
                description="Latest monthly expenses are materially above the recent baseline.",
                evidence={
                    "latest_expenses": latest.expenses,
                    "baseline_expenses": round(expense_baseline, 2),
                    "change_pct": round(expense_trend_pct, 2),
                },
            )
        )
        risk_signals.append(f"Expenses increased {expense_trend_pct:.1f}% versus the recent baseline.")
        risk_level = _risk_max(risk_level, severity)

    if cash_buffer_months < settings.low_cash_buffer_months:
        severity = "CRITICAL" if cash_buffer_months < 1 else "HIGH"
        anomalies.append(
            Anomaly(
                anomaly_id="CASH-BUFFER",
                type="cash_buffer",
                severity=severity,
                score=round(max(0.0, settings.low_cash_buffer_months - cash_buffer_months), 2),
                description="Liquid cash reserves are below the configured buffer target.",
                evidence={
                    "cash_balance": data.cash_balance,
                    "monthly_expenses": latest.expenses,
                    "buffer_months": round(cash_buffer_months, 2),
                    "target_months": settings.low_cash_buffer_months,
                },
            )
        )
        risk_signals.append(f"Cash reserve covers only {cash_buffer_months:.1f} months of expenses.")
        risk_level = _risk_max(risk_level, severity)

    if total_debt > 0 and debt_to_income_pct >= 50:
        severity = "HIGH" if debt_to_income_pct >= 70 else "MEDIUM"
        anomalies.append(
            Anomaly(
                anomaly_id="DEBT-RATIO",
                type="debt",
                severity=severity,
                score=round(debt_to_income_pct, 2),
                description="Outstanding liabilities are high relative to annualized income.",
                evidence={"debt_to_income_pct": round(debt_to_income_pct, 2)},
            )
        )
        risk_signals.append(f"Debt-to-income ratio is {debt_to_income_pct:.1f}%.")
        risk_level = _risk_max(risk_level, severity)

    if portfolio_value > 0 and concentration_pct >= settings.concentration_threshold * 100:
        severity = "HIGH" if concentration_pct >= 75 else "MEDIUM"
        anomalies.append(
            Anomaly(
                anomaly_id="PORT-CONC",
                type="concentration",
                severity=severity,
                score=round(concentration_pct / 100, 2),
                description="Portfolio value is materially concentrated in a single holding.",
                evidence={"top_holding_concentration_pct": round(concentration_pct, 2)},
            )
        )
        risk_signals.append(f"Top holding represents {concentration_pct:.1f}% of portfolio value.")
        risk_level = _risk_max(risk_level, severity)

    if data_quality.status != "complete":
        anomalies.append(
            Anomaly(
                anomaly_id="DATA-QUALITY",
                type="data_quality",
                severity="MEDIUM",
                score=1.0,
                description="Analysis completed with incomplete external context.",
                evidence={
                    "missing_sources": data_quality.missing_sources,
                    "warnings": data_quality.warnings,
                },
            )
        )
        risk_signals.append("External context is incomplete; recommendations should be validated by the advisor.")
        risk_level = _risk_max(risk_level, "MEDIUM")

    trend = _trend(latest.expenses, expense_baseline)
    if risk_level in {"HIGH", "CRITICAL"}:
        trend = "deteriorating"

    return AnalysisResult(
        metrics=metrics,
        anomalies=anomalies,
        risk_signals=risk_signals,
        risk_level=risk_level,
        trend=trend,
        data_quality=data_quality,
    )
