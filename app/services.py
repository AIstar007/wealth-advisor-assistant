from __future__ import annotations

import logging
import uuid
from dataclasses import dataclass
from typing import Any

from app.config import Settings
from app.memory.store import MemoryStore
from app.models.domain import (
    ClientFinancialData,
    CRMContext,
    FinalAdvisory,
    HumanReviewRequest,
    RunInput,
)
from app.tools.base import Tool
from app.tools.crm import HTTPCRMTool, InMemoryCRMTool
from app.utils.errors import normalize_review_decision
from app.workflows.builder import build_workflow

logger = logging.getLogger(__name__)


@dataclass
class PendingRun:
    workflow: Any
    request_id: str
    request: HumanReviewRequest


class WealthAdvisorService:
    def __init__(self, settings: Settings, crm_tool: Tool[CRMContext], memory_store: MemoryStore) -> None:
        self.settings = settings
        self.crm_tool = crm_tool
        self.memory_store = memory_store
        self._pending: dict[str, PendingRun] = {}

    async def start(self, financial_data: ClientFinancialData) -> tuple[str, FinalAdvisory | None, HumanReviewRequest | None]:
        run_id = uuid.uuid4().hex[:12]
        workflow = build_workflow(self.settings, self.memory_store, self.crm_tool)
        initial = RunInput(run_id=run_id, financial_data=financial_data)
        logger.info("service.start run_id=%s client_id=%s mode=%s", run_id, financial_data.client_id, self.settings.run_mode)

        stream = workflow.run(message=initial, stream=True)
        async for event in stream:
            if event.type == "output":
                result = FinalAdvisory.model_validate(event.data)
                logger.info("service.completed run_id=%s", run_id)
                return run_id, result, None
            if event.type == "request_info":
                request = _request_from_event(event)
                self._pending[run_id] = PendingRun(workflow, event.request_id, request)
                logger.info("service.pending_review run_id=%s request_id=%s", run_id, event.request_id)
                return run_id, None, request

        raise RuntimeError("Workflow stopped without output or human-review request")

    async def review(self, run_id: str, decision: str) -> tuple[str, FinalAdvisory | None, HumanReviewRequest | None]:
        pending = self._pending.get(run_id)
        if pending is None:
            raise KeyError(f"No pending human review for run_id={run_id}")

        normalized = normalize_review_decision(decision)

        logger.info("service.review run_id=%s decision=%s", run_id, normalized[:80])
        stream = pending.workflow.run(responses={pending.request_id: normalized}, stream=True)
        async for event in stream:
            if event.type == "output":
                result = FinalAdvisory.model_validate(event.data)
                self._pending.pop(run_id, None)
                return run_id, result, None
            if event.type == "request_info":
                request = _request_from_event(event)
                self._pending[run_id] = PendingRun(pending.workflow, event.request_id, request)
                return run_id, None, request

        raise RuntimeError("Workflow stopped after review without output")

    def pending_request(self, run_id: str) -> HumanReviewRequest | None:
        pending = self._pending.get(run_id)
        return pending.request if pending else None


def _request_from_event(event: Any) -> HumanReviewRequest:
    data = event.data
    # NativeHumanReviewRequest has to_domain(); keep the conversion isolated from the service.
    return data.to_domain()

