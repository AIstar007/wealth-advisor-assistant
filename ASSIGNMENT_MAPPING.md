# Assignment → Implementation Map

| Assignment requirement | Implementation | Evidence |
|---|---|---|
| Ingest client financial JSON | `ClientFinancialData` | `app/models/domain.py` |
| Orchestrator Agent | `OrchestratorExecutor` + `OrchestratorAgent` | `app/agents/executors.py` |
| Data Fetcher specialist | `DataFetcherExecutor` | `app/agents/executors.py` |
| Analyzer specialist | `AnalyzerExecutor` + `AnalyzerAgent` | `app/agents/executors.py` |
| Additional advisory specialist | `AdvisorExecutor` + `AdvisorAgent` | `app/agents/executors.py` |
| Agent framework workflow | `WorkflowBuilder` | `app/workflows/builder.py` |
| Tool abstraction | `Tool[T]`, `CRMTool`, `HTTPCRMTool`, `InMemoryCRMTool` | `app/tools/` |
| External API interaction | HTTP CRM adapter + mock CRM endpoint | `app/tools/crm.py`, `app/api.py` |
| Financial analysis | metrics engine | `app/analysis/engine.py` |
| Anomaly detection | transaction, trend, cash, debt, concentration, data quality rules | `app/analysis/engine.py` |
| Structured output | Pydantic schemas passed as Agent Framework response formats | `app/agents/runtime.py` |
| Error handling / fallback | retry CRM, partial context, isolated agent failures | `app/tools/crm.py`, `app/agents/executors.py` |
| Logging | console + rotating file logger | `app/utils/logging.py` |
| Short-term memory | typed workflow envelopes | `app/models/domain.py` |
| Long-term memory | SQLite insight store | `app/memory/store.py` |
| Human-in-the-loop | native `request_info` + response handler | `ReviewGateway` |
| Checkpointing | `FileCheckpointStorage` + executor state hooks | `app/workflows/builder.py`, `app/agents/executors.py` |
| API | FastAPI endpoints | `app/api.py` |
| Sample input | `data/client_cl001.json`, `request.example.json` | `data/`, root |
| Sample output | `data/sample_output.json` | `data/sample_output.json` |
| Automated tests | pytest suite | `tests/` |
| Containerization | Dockerfile | `Dockerfile` |
| Setup documentation | setup, architecture, trade-offs, assumptions | `README.md` |
