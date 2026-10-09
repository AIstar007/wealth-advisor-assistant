from __future__ import annotations

import json
from abc import ABC, abstractmethod
from typing import Any, TypeVar

from pydantic import BaseModel

from app.config import Settings
from app.models.domain import (
    AdvisoryOutput,
    AnalysisResult,
    AnalyzerNarrative,
    OrchestrationPlan,
)

T = TypeVar("T", bound=BaseModel)


class StructuredAgentAdapter(ABC):
    """Provider-neutral adapter around an Agent Framework agent."""

    name: str

    @abstractmethod
    async def run_structured(self, prompt: str, schema: type[T]) -> T:
        """Run the agent and return its response validated as a Pydantic model."""
        raise NotImplementedError


class MockAgentAdapter(StructuredAgentAdapter):
    """Deterministic local adapter for tests and demos without model credentials."""

    def __init__(self, name: str) -> None:
        self.name = name

    async def run_structured(self, prompt: str, schema: type[T]) -> T:
        payload = _extract_json(prompt)

        if schema is OrchestrationPlan:
            value: Any = {
                "objective": "Assess financial health, detect anomalies, and produce advisor-ready next actions.",
                "steps": ["fetch_context", "analyze", "advise", "review"],
                "analysis_focus": [
                    "cash flow",
                    "spending anomalies",
                    "liabilities",
                    "portfolio concentration",
                ],
                "human_review_min_risk": "HIGH",
                "rationale": "Fetch CRM context before deterministic analysis and review high-severity signals.",
            }
        elif schema is AnalyzerNarrative:
            analysis = AnalysisResult.model_validate(payload["analysis"])
            value = _mock_narrative(analysis)
        elif schema is AdvisoryOutput:
            analysis = AnalysisResult.model_validate(payload["analysis"])
            client_id = str(payload.get("client_id", "UNKNOWN"))
            value = _mock_advisory(client_id, analysis, payload.get("memory", []))
        else:
            raise ValueError(f"Unsupported mock schema: {schema.__name__}")

        return schema.model_validate(value)


class AzureOpenAIAgentAdapter(StructuredAgentAdapter):
    """Microsoft Agent Framework agent backed by Azure OpenAI."""

    def __init__(self, *, name: str, instructions: str, settings: Settings) -> None:
        settings.validate_azure_openai()
        self.name = name

        try:
            from agent_framework import Agent
            from agent_framework.openai import OpenAIChatClient
        except ImportError as exc:  # pragma: no cover
            raise RuntimeError(
                "Microsoft Agent Framework Azure OpenAI dependencies are missing. "
                "Install requirements.txt."
            ) from exc

        client_kwargs: dict[str, Any] = {
            "model": settings.azure_openai_deployment,
            "api_key": settings.azure_openai_api_key,
        }
        if settings.azure_openai_base_url:
            client_kwargs["base_url"] = settings.azure_openai_base_url
        else:
            client_kwargs["azure_endpoint"] = settings.azure_openai_endpoint

        if settings.azure_openai_api_version:
            client_kwargs["api_version"] = settings.azure_openai_api_version

        default_options: dict[str, Any] = {}
        if settings.agent_temperature is not None:
            # Keep temperature opt-in because some reasoning deployments do not
            # accept sampling controls. Set AGENT_TEMPERATURE only when desired.
            default_options["temperature"] = settings.agent_temperature

        self._agent = Agent(
            client=OpenAIChatClient(**client_kwargs),
            name=name,
            instructions=instructions,
            default_options=default_options or None,
        )

    async def run_structured(self, prompt: str, schema: type[T]) -> T:
        """Run the Azure OpenAI agent and validate its structured response."""
        return await _run_structured(self._agent, prompt, schema)


class FoundryAgentAdapter(StructuredAgentAdapter):
    """Microsoft Agent Framework agent backed by a Microsoft Foundry project."""

    def __init__(self, *, name: str, instructions: str, settings: Settings) -> None:
        settings.validate_foundry()
        self.name = name

        try:
            from agent_framework import Agent
            from agent_framework.foundry import FoundryChatClient
            from azure.identity import AzureCliCredential
        except ImportError as exc:  # pragma: no cover
            raise RuntimeError(
                "Microsoft Agent Framework Foundry dependencies are missing. "
                "Install requirements.txt."
            ) from exc

        default_options: dict[str, Any] = {}
        if settings.agent_temperature is not None:
            default_options["temperature"] = settings.agent_temperature

        self._agent = Agent(
            client=FoundryChatClient(
                project_endpoint=settings.foundry_project_endpoint,
                model=settings.foundry_model,
                credential=AzureCliCredential(),
            ),
            name=name,
            instructions=instructions,
            default_options=default_options or None,
        )

    async def run_structured(self, prompt: str, schema: type[T]) -> T:
        """Run the Foundry agent and validate its structured response."""
        return await _run_structured(self._agent, prompt, schema)


async def _run_structured(agent: Any, prompt: str, schema: type[T]) -> T:
    """Run an Agent Framework agent with a Pydantic response schema.

    Current Agent Framework Python agents accept a Pydantic model through
    options={"response_format": schema}; the parsed model is normally available
    on response.value. Text parsing is retained as a compatibility fallback.
    """
    response = await agent.run(
        prompt,
        options={"response_format": schema},
    )

    value = getattr(response, "value", None)
    if value is not None:
        if isinstance(value, schema):
            return value
        if isinstance(value, str):
            try:
                return schema.model_validate_json(value)
            except ValueError:
                # If value is a non-JSON string, try the response text below.
                pass
        else:
            return schema.model_validate(value)

    raw_text = getattr(response, "text", None)
    if raw_text:
        try:
            return schema.model_validate_json(raw_text)
        except ValueError as exc:
            raise RuntimeError(
                f"Agent response could not be parsed as {schema.__name__}."
            ) from exc

    raise RuntimeError(
        f"Agent returned no structured output for {schema.__name__}."
    )


def _extract_json(prompt: str) -> dict[str, Any]:
    marker = "PAYLOAD_JSON:\n"
    if marker not in prompt:
        return {}
    return json.loads(prompt.split(marker, 1)[1].strip())


def _mock_narrative(analysis: AnalysisResult) -> dict[str, Any]:
    severity_text = {
        "LOW": "The client profile appears broadly stable with no high-severity risk indicators.",
        "MEDIUM": "The profile contains moderate signals that should be addressed through advisor follow-up.",
        "HIGH": "The profile contains material risk signals requiring advisor review before client action.",
        "CRITICAL": "The profile contains critical signals that warrant prompt advisor intervention.",
    }[analysis.risk_level]
    return {
        "executive_summary": severity_text,
        "risk_rationale": " ".join(analysis.risk_signals[:4])
        or "No material risk signal detected.",
        "priority_focus": [a.description for a in analysis.anomalies[:3]],
        "confidence": max(0.70, 0.95 - 0.05 * len(analysis.data_quality.warnings)),
    }


def _mock_advisory(
    client_id: str,
    analysis: AnalysisResult,
    memory: list[dict[str, Any]],
) -> dict[str, Any]:
    recommendations: list[dict[str, Any]] = []
    for anomaly in analysis.anomalies:
        if anomaly.type == "transaction":
            recommendations.append(
                {
                    "recommendation_id": f"REC-{anomaly.anomaly_id}",
                    "priority": anomaly.severity,
                    "action": "Review the unusual transaction with the client and verify its purpose.",
                    "rationale": anomaly.description,
                    "evidence_ids": [anomaly.anomaly_id],
                    "advisor_only": True,
                }
            )
        elif anomaly.type == "spending_trend":
            recommendations.append(
                {
                    "recommendation_id": "REC-SPEND",
                    "priority": anomaly.severity,
                    "action": "Discuss the spending increase and confirm whether it is temporary or structural.",
                    "rationale": anomaly.description,
                    "evidence_ids": [anomaly.anomaly_id],
                    "advisor_only": False,
                }
            )
        elif anomaly.type == "cash_buffer":
            recommendations.append(
                {
                    "recommendation_id": "REC-CASH",
                    "priority": anomaly.severity,
                    "action": "Prioritize restoring a cash reserve toward the configured target buffer.",
                    "rationale": anomaly.description,
                    "evidence_ids": [anomaly.anomaly_id],
                    "advisor_only": False,
                }
            )
        elif anomaly.type == "debt":
            recommendations.append(
                {
                    "recommendation_id": "REC-DEBT",
                    "priority": anomaly.severity,
                    "action": "Review high-cost liabilities and repayment sequencing with the client.",
                    "rationale": anomaly.description,
                    "evidence_ids": [anomaly.anomaly_id],
                    "advisor_only": False,
                }
            )
        elif anomaly.type == "concentration":
            recommendations.append(
                {
                    "recommendation_id": "REC-CONC",
                    "priority": anomaly.severity,
                    "action": "Assess concentration risk and discuss diversification in line with the client's risk profile.",
                    "rationale": anomaly.description,
                    "evidence_ids": [anomaly.anomaly_id],
                    "advisor_only": False,
                }
            )
        elif anomaly.type == "data_quality":
            recommendations.append(
                {
                    "recommendation_id": "REC-DATA",
                    "priority": "MEDIUM",
                    "action": "Validate missing external context before taking client-facing action.",
                    "rationale": anomaly.description,
                    "evidence_ids": [anomaly.anomaly_id],
                    "advisor_only": True,
                }
            )

    if not recommendations:
        recommendations.append(
            {
                "recommendation_id": "REC-REVIEW",
                "priority": "LOW",
                "action": "Continue routine monitoring and review progress toward stated goals.",
                "rationale": "No material anomaly was detected by the current rule set.",
                "evidence_ids": [],
                "advisor_only": False,
            }
        )

    historical_note = (
        " Historical insights are available for trajectory comparison." if memory else ""
    )
    return {
        "client_id": client_id,
        "summary": f"Advisor decision support generated from deterministic analysis.{historical_note}",
        "recommendations": recommendations,
        "assumptions": [
            "Financial and CRM data are assumed to be representative of the review period.",
            "Anomalies are screening signals, not proof of fraud or financial misconduct.",
        ],
        "review_required": analysis.risk_level in {"HIGH", "CRITICAL"},
        "confidence": 0.91 if analysis.data_quality.status == "complete" else 0.78,
        "disclaimer": "Decision support for a human advisor; not individualized financial advice.",
    }


def create_agent(
    settings: Settings,
    *,
    name: str,
    instructions: str,
) -> StructuredAgentAdapter:
    if settings.run_mode in {"azure_openai", "azure"}:
        return AzureOpenAIAgentAdapter(
            name=name,
            instructions=instructions,
            settings=settings,
        )
    if settings.run_mode == "foundry":
        return FoundryAgentAdapter(
            name=name,
            instructions=instructions,
            settings=settings,
        )
    if settings.run_mode == "mock":
        return MockAgentAdapter(name)
    raise ValueError(
        f"Unsupported RUN_MODE={settings.run_mode!r}. Use mock, azure_openai, or foundry."
    )
