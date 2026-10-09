from __future__ import annotations

from fastapi import FastAPI, HTTPException

from app.agui_integration import register_agui_endpoint

from app.config import settings
from app.memory.store import MemoryStore
from app.models.domain import ClientAnalysisRequest, ReviewSubmission, RunAcceptedResponse
from app.services import WealthAdvisorService
from app.tools.crm import HTTPCRMTool, InMemoryCRMTool
from app.utils.logging import configure_logging

configure_logging(settings.log_level)

MOCK_CRM_DATA = {
    "CL001": {
        "advisor_notes": "Client is a senior software engineer planning a home purchase within 24 months.",
        "life_events": ["Potential home purchase", "Expected role change in the next 6 months"],
        "stated_goals": ["Build home down-payment reserve", "Maintain emergency liquidity"],
        "last_contact_date": "2026-09-12",
    }
}



def create_service() -> WealthAdvisorService:
    memory = MemoryStore(settings.database_path)
    if settings.crm_mode == "http":
        crm = HTTPCRMTool(settings.mock_crm_url)
    else:
        crm = InMemoryCRMTool(MOCK_CRM_DATA)
    return WealthAdvisorService(settings, crm, memory)


service = create_service()
app = FastAPI(
    title="Wealth Advisor Assistant",
    version="1.1.0",
    description=(
        "Multi-agent wealth decision-support service built with Microsoft Agent Framework, "
        "with optional AG-UI streaming for CopilotKit and A2UI generative surfaces."
    ),
)

# The original REST routes stay supported. AG-UI is registered alongside them and
# shares this same `service` instance, so dashboard review buttons resume the same run.
ag_ui_enabled = register_agui_endpoint(app, service, settings)


@app.get("/health")
async def health() -> dict[str, str | bool]:
    return {
        "status": "ok",
        "mode": settings.run_mode,
        "crm_mode": settings.crm_mode,
        "ag_ui_enabled": ag_ui_enabled,
    }


@app.get("/mock/crm/clients/{client_id}")
async def mock_crm_client(client_id: str) -> dict:
    record = MOCK_CRM_DATA.get(client_id)
    if record is None:
        raise HTTPException(status_code=404, detail="Client not found")
    return record


@app.post("/v1/analyze", response_model=RunAcceptedResponse)
async def analyze(request: ClientAnalysisRequest) -> RunAcceptedResponse:
    try:
        run_id, result, review_request = await service.start(request.financial_data)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    if result is not None:
        return RunAcceptedResponse(run_id=run_id, status="completed", result=result)
    return RunAcceptedResponse(run_id=run_id, status="pending_review", review_request=review_request)


@app.get("/v1/runs/{run_id}/review", response_model=RunAcceptedResponse)
async def get_pending_review(run_id: str) -> RunAcceptedResponse:
    request = service.pending_request(run_id)
    if request is None:
        raise HTTPException(status_code=404, detail="No pending review for this run")
    return RunAcceptedResponse(run_id=run_id, status="pending_review", review_request=request)


@app.post("/v1/runs/{run_id}/review", response_model=RunAcceptedResponse)
async def submit_review(run_id: str, body: ReviewSubmission) -> RunAcceptedResponse:
    decision = body.decision.strip()
    try:
        _, result, review_request = await service.review(run_id, decision)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    if result is not None:
        return RunAcceptedResponse(run_id=run_id, status="completed", result=result)
    return RunAcceptedResponse(run_id=run_id, status="pending_review", review_request=review_request)
