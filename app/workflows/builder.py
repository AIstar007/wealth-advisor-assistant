from __future__ import annotations

from agent_framework import FileCheckpointStorage, Workflow, WorkflowBuilder

from app.agents.executors import (
    AdvisorExecutor,
    AnalyzerExecutor,
    DataFetcherExecutor,
    NativeHumanReviewRequest,
    OrchestratorExecutor,
    ReviewGateway,
)
from app.config import Settings
from app.memory.store import MemoryStore
from app.models.domain import CRMContext
from app.tools.base import Tool


def build_workflow(
    settings: Settings,
    memory_store: MemoryStore,
    crm_tool: Tool[CRMContext],
) -> Workflow:
    """Build a per-run workflow graph using Microsoft Agent Framework."""

    checkpoint_path = settings.resolved_database_path.parent / "checkpoints"
    request_type = f"{NativeHumanReviewRequest.__module__}:{NativeHumanReviewRequest.__qualname__}"
    checkpoint_path.mkdir(parents=True, exist_ok=True)
    storage = FileCheckpointStorage(
        storage_path=checkpoint_path,
        allowed_checkpoint_types=[request_type],
    )

    orchestrator = OrchestratorExecutor(settings)
    data_fetcher = DataFetcherExecutor(settings, crm_tool)
    analyzer = AnalyzerExecutor(settings)
    advisor = AdvisorExecutor(settings, memory_store)
    review = ReviewGateway(settings, memory_store)

    return (
        WorkflowBuilder(
            name="WealthAdvisorWorkflow",
            description="Client data -> context -> deterministic analysis -> advisor decision support -> human review.",
            start_executor=orchestrator,
            max_iterations=8,
            checkpoint_storage=storage,
            output_from=[review],
        )
        .add_edge(orchestrator, data_fetcher)
        .add_edge(data_fetcher, analyzer)
        .add_edge(analyzer, advisor)
        .add_edge(advisor, review)
        .build()
    )
