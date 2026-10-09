from __future__ import annotations

import asyncio
import logging
from typing import Any

import httpx

from app.models.domain import CRMContext
from app.tools.base import Tool
from app.utils.errors import ToolError

logger = logging.getLogger(__name__)


class InMemoryCRMTool(Tool[CRMContext]):
    name = "crm_lookup"

    def __init__(self, records: dict[str, dict[str, Any]]) -> None:
        self.records = records

    async def execute(self, *, client_id: str) -> CRMContext:
        record = self.records.get(client_id)
        if record is None:
            raise ToolError(f"CRM client not found: {client_id}")
        return CRMContext(client_id=client_id, **record)


class HTTPCRMTool(Tool[CRMContext]):
    name = "crm_lookup"

    def __init__(self, base_url: str, retries: int = 2, timeout: float = 4.0) -> None:
        self.base_url = base_url.rstrip("/")
        self.retries = retries
        self.timeout = timeout

    async def execute(self, *, client_id: str) -> CRMContext:
        last_error: Exception | None = None
        for attempt in range(1, self.retries + 2):
            try:
                async with httpx.AsyncClient(timeout=self.timeout) as client:
                    response = await client.get(f"{self.base_url}/clients/{client_id}")
                    response.raise_for_status()
                    payload = response.json()
                    return CRMContext(client_id=client_id, **payload)
            except (httpx.HTTPError, ValueError) as exc:
                last_error = exc
                logger.warning(
                    "CRM lookup failed attempt=%s client_id=%s error=%s",
                    attempt,
                    client_id,
                    exc,
                )
                if attempt <= self.retries:
                    await asyncio.sleep(0.15 * attempt)

        raise ToolError(f"CRM lookup failed for {client_id}: {last_error}") from last_error
