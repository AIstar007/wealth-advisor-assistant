from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Literal, cast

from agent_framework import Executor, WorkflowContext, handler, response_handler

from app.agents.runtime import create_agent
from app.analysis.engine import analyze_finances
from app.config import Settings
from app.memory.store import MemoryStore
from app.models.domain import (
    AdvisoryOutput,
    AdvisorEnvelope,
    AnalysisInputEnvelope,
    AnalyzerNarrative,
    FetchedEnvelope,
    FinalAdvisory,
    HumanReviewRequest,
    OrchestrationPlan,
    CRMContext,
    ReviewMetadata,
    RunInput,
)
from app.tools.base import Tool

logger = logging.getLogger(__name__)


@dataclass
class NativeHumanReviewRequest:
    """Serializable request emitted by the Agent Framework workflow."""

    run_id: str = ""
    client_id: str = ""
    risk_level: str = "HIGH"
    summary: str = ""
    recommendations_json: str = "[]"
    prompt: str = ""

    def to_domain(self) -> HumanReviewRequest:
        return HumanReviewRequest(
            run_id=self.run_id,
            client_id=self.client_id,
            risk_level=self.risk_level,  # type: ignore[arg-type]
            summary=self.summary,
            recommendations=json.loads(self.recommendations_json),
            prompt=self.prompt,
        )


class OrchestratorExecutor(Executor):
    """Planning brain: creates a small structured execution plan."""

    def __init__(self, settings: Settings, id: str = "orchestrator") -> None:
        super().__init__(id=id)
        self.agent = create_agent(
            settings,
            name="OrchestratorAgent",
            instructions=(
                "You are the central coordinator for a wealth advisor assistant. "
                "Return a minimal structured plan. Never invent financial facts. "
                "Always fetch available CRM context, run deterministic financial analysis, "
                "generate advisor recommendations, and require human review for HIGH or CRITICAL risk."
            ),
        )

    @handler
    async def handle(self, payload: RunInput, ctx: WorkflowContext[FetchedEnvelope]) -> None:
        logger.info("orchestrator.start run_id=%s client_id=%s", payload.run_id, payload.financial_data.client_id)
        prompt = (
            "Create an execution plan for this wealth-advisor request.\n"
            "PAYLOAD_JSON:\n"
            + json.dumps(
                {
                    "client_id": payload.financial_data.client_id,
                    "risk_profile": payload.financial_data.risk_profile,
                    "has_transactions": bool(payload.financial_data.transactions),
                    "has_holdings": bool(payload.financial_data.holdings),
                    "has_goals": bool(payload.financial_data.goals),
                }
            )
        )
        plan = await self.agent.run_structured(prompt, OrchestrationPlan)
        logger.info("orchestrator.plan run_id=%s steps=%s", payload.run_id, plan.steps)
        # The plan is passed downstream by DataFetcherExecutor; this executor only needs
        # to emit the next-stage payload, so the data fetcher does the actual external call.
        await ctx.send_message(
            FetchedEnvelope(
                run_id=payload.run_id,
                plan=plan,
                financial_data=payload.financial_data,
                data_quality={"status": "complete"},
            )
        )


class DataFetcherExecutor(Executor):
    """Retrieves CRM context behind a provider-neutral tool abstraction."""

    def __init__(
        self,
        settings: Settings,
        crm_tool: Tool[CRMContext],
        id: str = "data_fetcher",
    ) -> None:
        super().__init__(id=id)
        self.settings = settings
        self.crm_tool = crm_tool

    @handler
    async def handle(
        self, payload: FetchedEnvelope, ctx: WorkflowContext[AnalysisInputEnvelope]
    ) -> None:
        logger.info("data_fetcher.start run_id=%s", payload.run_id)
        warnings: list[str] = []
        missing_sources: list[str] = []
        fallback_used = False

        try:
            crm = await self.crm_tool.execute(client_id=payload.financial_data.client_id)
            logger.info("data_fetcher.crm_ok run_id=%s", payload.run_id)
            data_quality = payload.data_quality.model_copy(update={"status": "complete"})
        except Exception as exc:
            logger.warning("data_fetcher.crm_failed run_id=%s error=%s", payload.run_id, exc)
            crm = None
            missing_sources.append("crm")
            fallback_used = True
            warnings.append("CRM context could not be retrieved; analysis used client-provided financial data.")
            data_quality = payload.data_quality.model_copy(
                update={
                    "status": "partial",
                    "missing_sources": missing_sources,
                    "warnings": warnings,
                    "fallback_used": fallback_used,
                }
            )

        await ctx.send_message(
            AnalysisInputEnvelope(
                run_id=payload.run_id,
                plan=payload.plan,
                financial_data=payload.financial_data,
                crm_context=crm,
                data_quality=data_quality,
            )
        )


class AnalyzerExecutor(Executor):
    """Runs deterministic analysis, then lets an Agent Framework agent narrate it."""

    def __init__(self, settings: Settings, id: str = "analyzer") -> None:
        super().__init__(id=id)
        self.settings = settings
        self.agent = create_agent(
            settings,
            name="AnalyzerAgent",
            instructions=(
                "You are a financial-analysis specialist. Deterministic metrics and anomaly results are "
                "authoritative. Summarize them without inventing values. Distinguish screening signals from facts."
            ),
        )

    @handler
    async def handle(
        self, payload: AnalysisInputEnvelope, ctx: WorkflowContext[AdvisorEnvelope]
    ) -> None:
        logger.info("analyzer.start run_id=%s", payload.run_id)
        analysis = analyze_finances(payload.financial_data, payload.data_quality, self.settings)
        narrative_prompt = (
            "Summarize this deterministic financial analysis. Do not recalculate or change numbers.\n"
            "PAYLOAD_JSON:\n"
            + json.dumps({"analysis": analysis.model_dump(mode="json")})
        )
        narrative = await self.agent.run_structured(narrative_prompt, AnalyzerNarrative)
        logger.info(
            "analyzer.complete run_id=%s risk=%s anomalies=%s",
            payload.run_id,
            analysis.risk_level,
            len(analysis.anomalies),
        )
        await ctx.send_message(
            AdvisorEnvelope(
                run_id=payload.run_id,
                plan=payload.plan,
                financial_data=payload.financial_data,
                crm_context=payload.crm_context,
                data_quality=payload.data_quality,
                analysis=analysis,
                analyzer_narrative=narrative,
            )
        )


class AdvisorExecutor(Executor):
    """Converts analysis + memory into advisor-ready structured recommendations."""

    def __init__(self, settings: Settings, memory_store: MemoryStore, id: str = "advisor") -> None:
        super().__init__(id=id)
        self.memory_store = memory_store
        self.agent = create_agent(
            settings,
            name="AdvisorAgent",
            instructions=(
                "You are an advisor decision-support specialist. Produce practical, evidence-linked "
                "recommendations for a human wealth advisor. Never promise returns or invent facts. "
                "Preserve the currency given in the source data exactly: if transaction currencies are INR, "
                "use INR/₹ and never label amounts as RMB/CNY. If currencies are mixed or unspecified, "
                "state the currency limitation instead of converting or guessing. Never describe a currency "
                "conversion unless an explicit exchange rate and conversion request were provided. "
                "Do not present this output as individualized financial advice."
            ),
        )

    @handler
    async def handle(
        self, payload: AdvisorEnvelope, ctx: WorkflowContext[AdvisorEnvelope]
    ) -> None:
        logger.info("advisor.start run_id=%s", payload.run_id)
        memory = self.memory_store.recent_insights(payload.financial_data.client_id, limit=5)
        prompt = (
            "Generate structured advisor decision support from deterministic analysis and historical memory. "
            "All quantitative claims must be grounded in the supplied input or deterministic analysis. "
            "The currency_codes field is authoritative: preserve those codes and do not substitute a different "
            "currency. Do not recalculate metrics when deterministic analysis already provides them.\n"
            "PAYLOAD_JSON:\n"
            + json.dumps(
                {
                    "client_id": payload.financial_data.client_id,
                    "risk_profile": payload.financial_data.risk_profile,
                    "currency_codes": sorted({t.currency.upper() for t in payload.financial_data.transactions}),
                    "goals": [g.model_dump(mode="json") for g in payload.financial_data.goals],
                    "analysis": payload.analysis.model_dump(mode="json"),
                    "memory": memory,
                    "crm_context": payload.crm_context.model_dump(mode="json") if payload.crm_context else None,
                }
            )
        )
        advisory = await self.agent.run_structured(prompt, AdvisoryOutput)
        advisory = advisory.model_copy(update={"client_id": payload.financial_data.client_id})
        review_required = advisory.review_required or payload.analysis.risk_level in {"HIGH", "CRITICAL"}
        advisory = advisory.model_copy(update={"review_required": review_required})

        envelope = AdvisorEnvelope(
            **payload.model_dump(exclude={"advisory", "memory_written"}),
            advisory=advisory,
            memory_written=False,
        )
        # The final review gateway is a separate executor, so send the envelope onward.
        await ctx.send_message(envelope)


class ReviewGateway(Executor):
    """Native Agent Framework human-in-the-loop checkpoint."""

    def __init__(self, settings: Settings, memory_store: MemoryStore, id: str = "review_gateway") -> None:
        super().__init__(id=id)
        self._settings = settings
        self._memory_store = memory_store
        self._current: AdvisorEnvelope | None = None

    @handler
    async def handle(
        self, payload: AdvisorEnvelope, ctx: WorkflowContext[Any, FinalAdvisory]
    ) -> None:
        if payload.advisory is None:
            raise RuntimeError("Review gateway received an incomplete advisor payload")

        if not payload.advisory.review_required:
            logger.info("review.skip run_id=%s reason=not_required", payload.run_id)
            final = _finalize(payload, ReviewMetadata(status="not_required"))
            await ctx.yield_output(_persist_memory(final, self._memory_store, logger))
            return

        if self._settings.auto_approve:
            logger.warning("review.auto_approved run_id=%s", payload.run_id)
            final = _finalize(
                payload,
                ReviewMetadata(
                    status="approved",
                    reviewer_comment="Auto-approved by development configuration.",
                    reviewed_at=datetime.now(timezone.utc).isoformat(),
                ),
            )
            await ctx.yield_output(_persist_memory(final, self._memory_store, logger))
            return

        self._current = payload
        request = NativeHumanReviewRequest(
            run_id=payload.run_id,
            client_id=payload.financial_data.client_id,
            risk_level=payload.analysis.risk_level,
            summary=payload.advisory.summary,
            recommendations_json=json.dumps(
                [r.model_dump(mode="json") for r in payload.advisory.recommendations]
            ),
            prompt=(
                "Review the proposed decision support. Reply APPROVE to accept, "
                "REJECT to block it, or OVERRIDE: <comment> to record an explicit human override."
            ),
        )
        logger.info("review.requested run_id=%s risk=%s", payload.run_id, payload.analysis.risk_level)
        await ctx.request_info(request_data=request, response_type=str)

    @response_handler
    async def on_human_feedback(
        self,
        original_request: NativeHumanReviewRequest,
        feedback: str,
        ctx: WorkflowContext[Any, FinalAdvisory],
    ) -> None:
        if self._current is None or self._current.run_id != original_request.run_id:
            raise RuntimeError("Review gateway lost its pending workflow payload")

        decision = feedback.strip()
        now = datetime.now(timezone.utc).isoformat()
        if decision.upper() == "APPROVE":
            status = "approved"
            comment = "Approved by human reviewer."
        elif decision.upper() == "REJECT":
            status = "rejected"
            comment = "Rejected by human reviewer."
        elif decision.upper().startswith("OVERRIDE:"):
            status = "overridden"
            comment = decision[len("OVERRIDE:") :].strip() or "Human override recorded."
        else:
            raise ValueError(
                "Invalid review decision. Use APPROVE, REJECT, or OVERRIDE: <comment>."
            )

        review = ReviewMetadata(
            status=cast(Literal["approved", "rejected", "overridden"], status),
            reviewer_comment=comment,
            reviewed_at=now,
        )
        if status == "rejected":
            rejected = self._current.advisory.model_copy(
                update={
                    "recommendations": [],
                    "summary": self._current.advisory.summary + " Human reviewer rejected the proposed decision support.",
                    "review_required": True,
                }
            )
            self._current = self._current.model_copy(update={"advisory": rejected})
        final = _finalize(self._current, review)
        final = _persist_memory(final, self._memory_store, logger)
        logger.info("review.completed run_id=%s status=%s", original_request.run_id, status)
        await ctx.yield_output(final)

    async def on_checkpoint_save(self) -> dict[str, Any]:
        return {"current": self._current.model_dump(mode="json") if self._current else None}

    async def on_checkpoint_restore(self, state: dict[str, Any]) -> None:
        current = state.get("current")
        self._current = AdvisorEnvelope.model_validate(current) if current else None


def _persist_memory(final: FinalAdvisory, memory_store: MemoryStore, logger: logging.Logger) -> FinalAdvisory:
    try:
        memory_store.save_insight(
            final.client_id,
            final.analysis.risk_level,
            final.advisory.summary,
            {
                "run_id": final.run_id,
                "risk_level": final.analysis.risk_level,
                "review_status": final.review.status,
                "anomaly_ids": [a.anomaly_id for a in final.analysis.anomalies],
            },
        )
        return final.model_copy(update={"memory_written": True})
    except Exception as exc:
        logger.exception("memory.write_failed run_id=%s error=%s", final.run_id, exc)
        return final.model_copy(update={"memory_written": False})


def _finalize(payload: AdvisorEnvelope, review: ReviewMetadata) -> FinalAdvisory:
    advisory = payload.advisory
    if review.status == "overridden" and review.reviewer_comment:
        advisory = advisory.model_copy(
            update={
                "summary": advisory.summary + f" Human reviewer override: {review.reviewer_comment}",
                "review_required": False,
            }
        )
    return FinalAdvisory(
        client_id=payload.financial_data.client_id,
        run_id=payload.run_id,
        plan=payload.plan,
        data_quality=payload.data_quality,
        analysis=payload.analysis,
        analyzer_narrative=payload.analyzer_narrative,
        advisory=advisory,
        review=review,
        memory_written=payload.memory_written,
    )
