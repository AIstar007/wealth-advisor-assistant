# CopilotKit + AG-UI + A2UI integration

This project uses the protocols for different jobs rather than choosing one as a replacement for the other:

- **AG-UI** (`/ag-ui`) is the bidirectional, streaming agent-to-application connection. CopilotKit uses it for chat, events, tool results and shared state. The protocol is actively evolving, so pin compatible package versions and re-check its release notes during upgrades.
- **A2UI** provides dynamic declarative UI inside the assistant response. Based on the user's request, the agent can compose registered components into a metric grid, trend chart, comparison, proportional breakdown, data table, goal-progress view, timeline, insight list, or callout. Basic catalog components can also be arranged into layouts. Its components are constrained to the frontend's registered catalog.
- **The dashboard is still application-owned.** Its primary metrics, anomalies and recommendations come from the existing FastAPI/Microsoft Agent Framework workflow. A2UI makes the agent's answer itself adaptive: a question can get a chart, table, card grid, timeline, combined visual, or ordinary text. It does not replace deterministic metrics or human-review controls.

The current implementation adds a CopilotKit-friendly frontend in `frontend/`, a backend AG-UI endpoint in `app/agui_integration.py`, and two same-origin Next.js proxy routes for analysis/review so the browser never needs the Azure API key or direct backend CORS access.

## Why both

AG-UI and A2UI are complementary protocols, not mutually exclusive alternatives. AG-UI is the integration boundary to expose a live agent; the protocol is still evolving and must be version-pinned. A2UI is useful when user requests call for a tailored presentation and is also evolving, so the main wealth dashboard stays a deterministic React view and only additional chat visuals are generated declaratively. The model can select a component composition, but it cannot send arbitrary HTML/JavaScript or execute financial actions through a generated surface.

## Backend setup (Windows PowerShell)

1. Open the project root and activate the existing environment:

   ```powershell
   cd D:\wealth-advisor-agent-submission-v2
   .\.venv\Scripts\Activate.ps1
   ```

2. Install the new AG-UI/A2UI dependency set along with the project's existing requirements:

   ```powershell
   python -m pip install --upgrade pip
   pip install -r requirements.txt
   ```

3. Keep the backend Azure settings in the root `.env`:

   ```env
   RUN_MODE=azure_openai
   AZURE_OPENAI_ENDPOINT=https://<your-resource>.openai.azure.com/
   AZURE_OPENAI_API_KEY=<your-rotated-key>
   AZURE_OPENAI_DEPLOYMENT=<your-chat-completion-deployment>
   ```

   `AZURE_OPENAI_API_VERSION` is optional in this project's config. Do not put the key in `frontend/.env.local`, `NEXT_PUBLIC_*` variables, or source control. This AG-UI path uses `OpenAIChatCompletionClient` because Microsoft's current Agent Framework A2UI guidance requires streamed tool-argument deltas for progressive A2UI rendering. The existing multi-agent analysis adapter remains unchanged apart from the separately shipped `run_structured` fix.

4. Start FastAPI:

   ```powershell
   uvicorn app.main:app --reload
   ```

5. Check that `/health` returns `"ag_ui_enabled": true`. If it returns `false`, inspect the startup log for AG-UI package/configuration errors; the existing REST routes still run, but CopilotKit cannot connect until the optional endpoint registers.

   - REST API docs: `http://127.0.0.1:8000/docs`
   - AG-UI stream endpoint: `http://127.0.0.1:8000/ag-ui` (used by the server-side proxy, not normally opened as a webpage)

The AG-UI tool calls the exact same `WealthAdvisorService` object used by `/v1/analyze`. A pending run therefore stays in the same process-local review map, and the dashboard's approve/reject buttons use the existing `/v1/runs/{run_id}/review` route to resume that workflow. This local arrangement requires one backend process; the in-memory pending-review map is not a distributed queue. The current `/ag-ui` + A2UI progressive-rendering path is enabled for `RUN_MODE=azure_openai` / `azure`; the existing REST workflow remains available in Foundry mode, but this specific streaming A2UI path is not registered there until client compatibility is validated.

## Frontend setup (second PowerShell terminal)

```powershell
cd D:\wealth-advisor-agent-submission-v2\frontend
Copy-Item .env.local.example .env.local
npm install
npm run dev
```

Open `http://localhost:3000`.

`.env.local` uses server-side variables only:

```env
AGENT_URL=http://127.0.0.1:8000/ag-ui
BACKEND_URL=http://127.0.0.1:8000
```

Do not prefix these with `NEXT_PUBLIC_`. The browser talks to same-origin Next.js route handlers; the handlers proxy to FastAPI. The browser receives no API credential.

To do a frontend compile check after dependencies install:

```powershell
npm run typecheck
npm run build
```

## Using it

1. Edit the client data in the JSON profile editor or import a `.json` file. The file can be the exact REST request wrapper (`{"financial_data": {...}}`) or the `ClientFinancialData` object itself.
2. Click **Analyze profile** to invoke the canonical REST analysis, or ask the CopilotKit chat to analyze the current profile. The chat agent receives the profile as AG-UI application context and calls `analyze_financial_data` when analysis is requested.
3. For HIGH/CRITICAL runs, review the generated summary and evidence-linked recommendations. Approve or reject through the dashboard. The action resumes the backend workflow; generated A2UI surfaces never approve a review or execute trades.
4. Ask for any view that fits the question—for example, “summarize my financial health as KPI cards”, “compare expenses across months in a line chart”, “show goal progress”, “turn risks into a table”, or “compare holdings as proportional bars”. The AG-UI endpoint injects A2UI generation and `frontend/src/lib/a2ui-catalog.tsx` defines the approved component grammar. The assistant response should render the chosen surface inline in chat, not merely describe a chart in prose. Ordinary questions can remain plain text.

## Response/state contract

The dashboard consumes one state key, `wealth_advisor`:

```json
{
  "run_id": "run-id",
  "status": "completed | pending_review | error",
  "client_id": "client-id",
  "result": "FinalAdvisory object or null",
  "review_request": "HumanReviewRequest object or null"
}
```

`status: pending_review` is not a failure: the deterministic workflow has reached a human checkpoint. `result` remains `null` until the existing review gateway resumes and emits a final output. While pending, the dashboard labels locally computed values as a profile snapshot instead of claiming they are final analysis output.

## Security / production notes

- AG-UI protocol thread IDs are correlation identifiers, not authorization credentials.
- The sample app is a local development integration. Before external deployment, add authentication/authorization to both REST and AG-UI endpoints, enforce client-level access checks, rate-limit requests, and use durable/distributed pending-run storage when scaling across processes.
- Keep A2UI components read-only by default. Application-owned controls perform explicitly authorized actions. Never let generated UI code call financial APIs, execute trades, or approve a review.
- Currency labels are treated as source data. The advisor prompt and tool response preserve the transaction currency codes; mixed currencies are surfaced as a limitation rather than silently summed or converted.
- The model produces explanatory language and view composition. Python's deterministic analysis remains authoritative for metrics, anomaly detection and risk level.
