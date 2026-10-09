import pytest
from pydantic import ValidationError

from app.models.domain import ClientFinancialData


def test_invalid_transaction_amount_rejected():
    with pytest.raises(ValidationError):
        ClientFinancialData.model_validate(
            {
                "client_id": "CL001",
                "as_of_date": "2026-09-30",
                "risk_profile": "moderate",
                "annual_income": 100,
                "cash_balance": 100,
                "monthly_history": [
                    {"month": "2026-09", "income": 100, "expenses": 50, "investments": 0, "debt_balance": 0}
                ],
                "transactions": [
                    {"id": "T1", "date": "2026-09-01", "description": "bad", "category": "x", "amount": -1, "transaction_type": "debit"}
                ],
            }
        )
