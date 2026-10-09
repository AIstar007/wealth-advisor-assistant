"""CopilotKit/AG-UI bridge for the Wealth Advisor Assistant.

The REST API remains the canonical interface for existing clients. This module
adds a separate AG-UI streaming endpoint that reuses the same service/workflow
and emits the completed or pending-review payload as shared agent state.
"""

from __future__ import annotations

import json
import logging
from typing import Any

from agent_framework import Agent, Content, tool
from fastapi import FastAPI

from app.config import Settings
from app.models.domain import ClientFinancialData
from app.services import WealthAdvisorService

logger = logging.getLogger(__name__)

MAX_PROFILE_JSON_CHARS = 200_000
A2UI_CATALOG_ID = "wealth-advisor-catalog"

A2UI_GUIDELINES = """
Compose one read-only, responsive A2UI surface from the catalog supplied by the client.

For visual requests, the conversational agent must call the injected
`render_a2ui` tool. Use the catalog's exact component names and property
schemas. Do not substitute a plain-text description of a chart or raw JSON
in ordinary assistant prose.

Use the catalog's exact component names and property schemas:
- Use WealthMetricGrid for a financial profile snapshot.
- Use WealthTrendLine for one numeric series.
- Use WealthMultiSeriesTrend for multiple numeric series sharing labels.
- Use WealthBreakdown for same-unit allocation.
- Use WealthComparisonBars for comparable quantities.
- Use WealthDataTable for row-wise information.
- Use WealthProgressList or WealthTimeline for goals.
- Use WealthInsightList for findings.
- Use WealthCallout for caveats.

Combine components when that makes the answer clearer. A valid surface must
match the supplied catalog and contain values grounded in the supplied context.

Ground every number in CURRENT_FINANCIAL_DATA_JSON or the deterministic
wealth_advisor state, or compute it transparently from supplied data.

Preserve source currency codes: INR is INR/₹, never RMB/CNY.
Never invent financial values, convert currencies, infer missing data as facts,
or mix incomparable currencies.

Do not create controls that approve or reject reviews, transfer money, execute
trades, or mutate financial data. The canonical dashboard and human-review
controls are application-owned.

If source data is missing, label it as unavailable rather than fabricating a value.
""".strip()


def _make_analyze_tool(service: WealthAdvisorService) -> Any:
    """Create a provider-neutral function tool that calls the existing service."""

    try:
        from agent_framework.ag_ui import state_update
    except ImportError:
        # Compatibility path for older Agent Framework package layouts.
        from agent_framework_ag_ui import state_update  # type: ignore[no-redef]

    @tool
    async def analyze_financial_data(financial_data_json: str) -> Content:
        """Analyze a client profile using the existing validated workflow.

        Args:
            financial_data_json: JSON containing ClientFinancialData, either
                as the object itself or wrapped in {"financial_data": ...}.
        """
        if (
            not isinstance(financial_data_json, str)
            or not financial_data_json.strip()
        ):
            return _state_update(
                state_update,
                "Please provide the current client financial data as JSON "
                "in the profile editor.",
                {
                    "status": "error",
                    "error": "Missing financial_data_json",
                },
            )

        if len(financial_data_json) > MAX_PROFILE_JSON_CHARS:
            return _state_update(
                state_update,
                "The profile JSON is too large. Please reduce it to "
                "200,000 characters or fewer.",
                {
                    "status": "error",
                    "error": "Profile JSON exceeded size limit",
                },
            )

        try:
            incoming = json.loads(financial_data_json)

            if isinstance(incoming, dict) and "financial_data" in incoming:
                incoming = incoming["financial_data"]

            financial_data = ClientFinancialData.model_validate(incoming)

        except (json.JSONDecodeError, TypeError, ValueError) as exc:
            detail = str(exc).replace("\n", " ")[:900]

            payload = {
                "status": "error",
                "error": "The client profile is not valid for analysis.",
                "details": detail,
            }

            return _state_update(
                state_update,
                f"The client profile could not be validated: {detail}",
                payload,
            )

        try:
            run_id, result, review_request = await service.start(
                financial_data
            )

        except (ValueError, RuntimeError) as exc:
            logger.warning(
                "agui.analysis_rejected client_id=%s error=%s",
                financial_data.client_id,
                exc,
            )

            payload = {
                "status": "error",
                "error": "The analysis workflow could not be started.",
                "details": str(exc)[:900],
                "client_id": financial_data.client_id,
            }

            return _state_update(
                state_update,
                payload["error"] + " " + payload["details"],
                payload,
            )

        except Exception:
            logger.exception(
                "agui.analysis_failed client_id=%s",
                financial_data.client_id,
            )

            payload = {
                "status": "error",
                "error": (
                    "An unexpected error occurred while running "
                    "the analysis."
                ),
                "client_id": financial_data.client_id,
            }

            return _state_update(
                state_update,
                payload["error"],
                payload,
            )

        payload: dict[str, Any] = {
            "run_id": run_id,
            "status": (
                "completed" if result is not None else "pending_review"
            ),
            "result": (
                result.model_dump(mode="json")
                if result is not None
                else None
            ),
            "review_request": (
                review_request.model_dump(mode="json")
                if review_request is not None
                else None
            ),
            "client_id": financial_data.client_id,
            "currency_codes": sorted(
                {
                    transaction.currency.upper()
                    for transaction in financial_data.transactions
                }
            ),
        }

        if result is not None:
            text = (
                f"Analysis completed for client {financial_data.client_id}. "
                f"Risk level: {result.analysis.risk_level}. "
                "The dashboard has been updated with deterministic metrics, "
                "anomalies, recommendations, data quality, and review status."
            )
        else:
            text = (
                f"Analysis for client {financial_data.client_id} requires "
                "human review. The dashboard now displays the pending review "
                "request and its recommendations. Use the dashboard's review "
                "controls to approve or reject it."
            )

        logger.info(
            "agui.analysis_result run_id=%s status=%s",
            run_id,
            payload["status"],
        )

        return _state_update(state_update, text, payload)

    return analyze_financial_data


def _state_update(
    state_update_fn: Any,
    text: str,
    payload: dict[str, Any],
) -> Content:
    """Attach a user-readable tool result and canonical dashboard state."""

    return state_update_fn(
        text=text,
        tool_result={
            "type": "wealth_advisor_result",
            "payload": payload,
        },
        state={"wealth_advisor": payload},
    )


def _create_agui_client(settings: Settings) -> Any:
    """Create a streaming-capable client for AG-UI/A2UI tool argument deltas."""

    if settings.run_mode in {"azure_openai", "azure"}:
        try:
            from agent_framework.openai import OpenAIChatCompletionClient
        except ImportError as exc:
            raise RuntimeError(
                "This Agent Framework installation lacks "
                "OpenAIChatCompletionClient. Update the Microsoft Agent "
                "Framework packages in requirements.txt."
            ) from exc

        settings.validate_azure_openai()

        kwargs: dict[str, Any] = {
            "model": settings.azure_openai_deployment,
            "api_key": settings.azure_openai_api_key,
        }

        if settings.azure_openai_base_url:
            kwargs["base_url"] = settings.azure_openai_base_url
        else:
            kwargs["azure_endpoint"] = settings.azure_openai_endpoint

        if settings.azure_openai_api_version:
            kwargs["api_version"] = settings.azure_openai_api_version

        return OpenAIChatCompletionClient(**kwargs)

    if settings.run_mode == "foundry":
        from agent_framework.foundry import FoundryChatClient
        from azure.identity import AzureCliCredential

        settings.validate_foundry()

        return FoundryChatClient(
            project_endpoint=settings.foundry_project_endpoint,
            model=settings.foundry_model,
            credential=AzureCliCredential(),
        )

    raise RuntimeError(
        "AG-UI requires RUN_MODE=azure_openai (recommended) or RUN_MODE=foundry."
    )


def register_agui_endpoint(
    app: FastAPI,
    service: WealthAdvisorService,
    settings: Settings,
) -> bool:
    """Register `/ag-ui` if supported; leave the REST API alive on setup errors."""

    # The streaming A2UI path is enabled for Azure OpenAI mode.
    # The REST workflow remains available in other modes.
    if settings.run_mode not in {"azure_openai", "azure"}:
        logger.info(
            "AG-UI/A2UI endpoint disabled in RUN_MODE=%s; use "
            "RUN_MODE=azure_openai for this streaming integration",
            settings.run_mode,
        )
        return False

    try:
        try:
            from agent_framework.ag_ui import (
                add_agent_framework_fastapi_endpoint,
            )
        except ImportError:
            from agent_framework_ag_ui import (
                add_agent_framework_fastapi_endpoint,
            )  # type: ignore[no-redef]

        analyze_tool = _sync_tool_factory(service)

        agent = Agent(
            name="WealthAdvisorCopilot",
            client=_create_agui_client(settings),
            instructions=(
                "You are the conversational interface for a Wealth Advisor "
                "Assistant. Answer general questions conversationally; use UI "
                "surfaces only when they improve the answer. The app may provide "
                "a context item named CURRENT_FINANCIAL_DATA_JSON. Its value is "
                "JSON, sometimes string-encoded by the protocol. For a request "
                "to analyze or review the current client profile, pass that "
                "exact profile as the financial_data_json argument to "
                "analyze_financial_data. If there is no valid profile context, "
                "ask the user to paste or load JSON in the profile editor. "
                "Do not claim that analysis ran unless the tool returned a "
                "result. The deterministic metrics and validated response are "
                "the source of truth. Preserve source currency codes exactly: "
                "INR is INR/₹, never RMB/CNY. Never invent currency conversions "
                "or numerical facts. "

                "For follow-up questions, use the latest wealth_advisor result "
                "state and explain relevant facts. Use A2UI for useful "
                "additional views such as comparisons, timelines, trends, "
                "or categorized breakdowns, and only from data already present "
                "in context or tool results. "

                "For any user request to visualize, compare, break down, "
                "summarize a profile, show goal progress, show trends, build "
                "a timeline, create a table, or present multiple related facts, "
                "you MUST call the injected `render_a2ui` tool to create an "
                "A2UI surface rather than writing a UI specification as text. "
                "This endpoint injects the native Agent Framework AG-UI A2UI "
                "tool. Do not try to call `generate_a2ui` unless that distinct "
                "tool is explicitly registered by the active runtime. "

                "After `render_a2ui` succeeds, give only a short confirmation "
                "and do not repeat the surface data as text. Do not emit raw "
                "A2UI JSON, pseudo-JSON, XML, or an A2UI code block in the "
                "assistant message. "

                "Choose the most helpful layout from the supplied catalog: "
                "WealthMetricGrid for snapshots, WealthTrendLine for one "
                "numeric series, WealthMultiSeriesTrend for multiple series "
                "with shared labels, WealthComparisonBars for comparable "
                "quantities, WealthBreakdown for same-unit allocation, "
                "WealthDataTable for row-wise comparisons, WealthProgressList "
                "for goals, WealthTimeline for dated events, WealthInsightList "
                "for findings, and WealthCallout for caveats. Combine "
                "components when useful. A simple conversational question "
                "may remain plain text. Treat an A2UI surface as a presentation "
                "of facts already supplied in context or returned by "
                "analyze_financial_data, not as a source of new facts. "

                "If the A2UI tool is not actually available, say visual "
                "rendering is unavailable rather than pretending that JSON "
                "is a rendered chart. Never mix currencies in a single chart "
                "or total unless an explicit conversion with a supplied rate "
                "was requested. Never approve or reject a human review on the "
                "user's behalf. Human-review controls in the dashboard are "
                "the only approval control. Do not provide individualized "
                "investment instructions or promise investment returns; this "
                "is advisor decision support."
            ),
            tools=[analyze_tool],
        )

        add_agent_framework_fastapi_endpoint(
            app,
            agent,
            path="/ag-ui",
            # The Python Agent Framework endpoint owns native AG-UI A2UI tool
            # injection (render_a2ui). CopilotKit's runtime applies the event
            # middleware so streamed tool arguments become A2UI surface events.
            # The provider sends the custom catalog schema with the request.
            a2ui_config={
                "inject_a2ui_tool": True,
                "default_catalog_id": A2UI_CATALOG_ID,
                "guidelines": {
                    "composition_guide": A2UI_GUIDELINES,
                },
            },
        )

        logger.info("Registered CopilotKit AG-UI endpoint at /ag-ui")
        return True

    except Exception as exc:
        # Keep existing REST consumers available if AG-UI setup fails.
        logger.exception(
            "Could not register AG-UI endpoint: %s",
            exc,
        )
        return False


def _sync_tool_factory(service: WealthAdvisorService) -> Any:
    """Create the tool during application startup, sharing the existing service."""

    return _make_analyze_tool(service)