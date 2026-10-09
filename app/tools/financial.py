from __future__ import annotations

from app.models.domain import ClientFinancialData
from app.tools.base import Tool


class FinancialDataTool(Tool[ClientFinancialData]):
    name = "financial_data"

    async def execute(self, *, financial_data: ClientFinancialData) -> ClientFinancialData:
        # Validation is performed by Pydantic before the tool is called; this
        # tool exists to preserve the same abstraction boundary used by remote tools.
        return financial_data
