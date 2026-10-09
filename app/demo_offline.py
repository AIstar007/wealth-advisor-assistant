from __future__ import annotations

import asyncio
import json
from pathlib import Path

from app.agents.runtime import MockAgentAdapter
from app.analysis.engine import analyze_finances
from app.config import settings
from app.models.domain import AnalyzerNarrative, ClientFinancialData, DataQuality, OrchestrationPlan


async def main() -> None:
    payload = json.loads(Path("data/client_cl001.json").read_text(encoding="utf-8"))
    client = ClientFinancialData.model_validate(payload)

    plan_agent = MockAgentAdapter("OrchestratorAgent")
    plan = await plan_agent.run_structured(
        "Create an execution plan.\nPAYLOAD_JSON:\n" + json.dumps({"client_id": client.client_id}),
        OrchestrationPlan,
    )

    analysis = analyze_finances(client, DataQuality(status="complete"), settings)
    narrative_agent = MockAgentAdapter("AnalyzerAgent")
    narrative = await narrative_agent.run_structured(
        "Summarize deterministic analysis.\nPAYLOAD_JSON:\n"
        + json.dumps({"analysis": analysis.model_dump(mode="json")}),
        AnalyzerNarrative,
    )

    result = {
        "orchestration_plan": plan.model_dump(mode="json"),
        "analysis": analysis.model_dump(mode="json"),
        "analyzer_narrative": narrative.model_dump(mode="json"),
    }
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    asyncio.run(main())
