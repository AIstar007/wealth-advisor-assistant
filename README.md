# Wealth Advisor Assistant

An AI-powered wealth advisory workspace that combines a deterministic financial-analysis workflow with a conversational assistant, portfolio insights, and human-in-the-loop review.

> **Project status:** The REST analysis and human-review workflow have been exercised locally. The AG-UI backend endpoint is enabled and has produced A2UI tool-call operations in a direct streaming test. End-to-end rendering of those surfaces in the CopilotKit browser chat still needs verification in the local environment.

## Highlights

- **Financial profile workspace** — load the sample profile, edit profile JSON, or import a `.json` file.
- **Financial overview** — metric cards for monthly income, expenses, net cash flow, cash buffer, and portfolio value.
- **Cash-flow visualization** — compare monthly income and spending from the supplied history.
- **Risk and insight views** — surface workflow-provided anomalies, risk level, data-quality warnings, and evidence-linked discussion points.
- **Human-in-the-loop review** — approve or reject recommendations through explicit dashboard controls. Approval records a review decision; it does not execute trades or move money.
- **Conversational assistant** — ask questions about the current client profile through CopilotKit and AG-UI.
- **A2UI catalog** — custom read-only components for metric grids, insight lists, comparison bars, allocation breakdowns, trends, tables, goal progress, timelines, and callouts.
- **Azure OpenAI integration** — the AG-UI streaming path is configured for `RUN_MODE=azure_openai` / `azure`.

## Technology

- **Frontend:** Next.js, React, TypeScript, CopilotKit v2, AG-UI client, custom A2UI catalog
- **Backend:** Python, FastAPI, Microsoft Agent Framework, AG-UI adapter
- **Model provider:** Azure OpenAI
- **Analysis:** Existing Wealth Advisor service and validated domain models
- **Review workflow:** Explicit human approval/rejection controls

## Architecture

```text
Browser
  └── Next.js / React dashboard
      ├── Financial profile editor and dashboard
      ├── CopilotKit chat
      ├── Custom A2UI catalog and renderers
      └── /api/copilotkit runtime route
             │
             ▼
       AG-UI stream: /ag-ui
             │
             ▼
       FastAPI + Microsoft Agent Framework
          ├── Conversational agent
          ├── A2UI generation tool / surface operations
          └── analyze_financial_data tool
                    │
                    ▼
           WealthAdvisorService
                    │
                    ▼
        Validated analysis and review payload
```

The REST analysis flow remains the canonical application interface. The AG-UI endpoint provides a separate streaming interface for the conversational experience and exposes analysis results as shared agent state.

## Repository layout

The core files discussed during development are expected to follow this structure:

```text
wealthproj/
├── app/
│   ├── agui_integration.py      # AG-UI/A2UI bridge and agent setup
│   ├── config.py                # Backend settings
│   ├── models/                  # Validated domain models
│   └── services/                # Wealth advisor workflow/service
├── frontend/
│   ├── src/app/                 # Next.js app, API routes, providers
│   └── src/lib/
│       ├── a2ui-catalog.tsx     # Custom A2UI definitions and renderers
│       └── sample-financial-data.*
├── requirements.txt
└── README.md
```

Your local repository may contain additional modules or different filenames; retain the existing service and settings structure when applying integration changes.

## Prerequisites

- Python version compatible with the project's `requirements.txt`
- Node.js and npm compatible with the versions pinned by the frontend project
- An Azure OpenAI deployment and its endpoint/API credentials
- Windows PowerShell commands below assume the repository is at `D:\wealth-advisor-copilotkit-agui-a2ui\wealthproj`; adjust paths for your machine

## Setup

### 1. Clone the repository

```powershell
git clone <YOUR_GITHUB_REPOSITORY_URL>
cd wealthproj
```

Replace `<YOUR_GITHUB_REPOSITORY_URL>` with your repository URL. If you are already working in the project directory, skip cloning.

### 2. Create and activate the Python environment

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
```

If PowerShell blocks activation for the current terminal, use this temporary process-scoped setting and activate again:

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy RemoteSigned
.\.venv\Scripts\Activate.ps1
```

### 3. Configure backend environment variables

Create or update the backend `.env` file using the variable names expected by `app/config.py`. The Azure OpenAI settings used by the integration correspond to these fields:

```dotenv
RUN_MODE=azure_openai
AZURE_OPENAI_DEPLOYMENT=<your-deployment-name>
AZURE_OPENAI_API_KEY=<your-api-key>
AZURE_OPENAI_ENDPOINT=https://<your-resource-name>.openai.azure.com/
AZURE_OPENAI_API_VERSION=<your-supported-api-version>

# Optional if your configuration uses a custom base URL
# AZURE_OPENAI_BASE_URL=<your-base-url>
```

These are illustrative values, not real credentials. Confirm the exact environment-variable aliases and required fields in `app/config.py`; do not add duplicate variables if the project already defines them differently.

**Security:** Never commit `.env`, `.env.local`, access tokens, API keys, client data, or financial profiles containing private information. If a real key was ever shared in chat, logs, or a public repository, revoke/rotate it and replace it in your local environment.

### 4. Start the backend

Use the startup command already defined by your project. If the FastAPI entry point is `app.main:app`, the command is commonly:

```powershell
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

If your application uses another entry point, keep that existing command instead.

Check the health endpoint exposed by your app. A healthy response from the current local setup looked like:

```json
{
  "status": "ok",
  "mode": "azure_openai",
  "crm_mode": "memory",
  "ag_ui_enabled": true
}
```

The exact fields depend on your implementation. Confirm that `ag_ui_enabled` is `true` and that the backend logs report registration of `/ag-ui`.

### 5. Configure and start the frontend

In a second terminal:

```powershell
cd frontend
npm install
```

Create or update `frontend/.env.local`:

```dotenv
AGENT_URL=http://127.0.0.1:8000/ag-ui
```

Then run:

```powershell
npm run typecheck
npm run build
npm run dev
```

Open the local URL printed by Next.js. If port `3000` is already occupied, Next.js may choose `3001` or another available port.

## Using the workspace

1. Load the sample financial profile or import your own JSON profile.
2. Review the displayed currency and profile fields.
3. Choose **Analyze profile** to run the deterministic workflow.
4. Review the analysis summary, financial metrics, anomalies, and recommendations.
5. When the workflow returns `pending_review`, use the explicit dashboard controls to approve or reject the review request.
6. Ask the Wealth Advisor chat questions about the loaded profile.
7. For a visualization request, ask for a metric grid, chart, comparison, allocation breakdown, table, goal progress view, or timeline.

Use only data you are authorized to process. Financial outputs are decision support, not personalized investment instructions. Verify figures and assumptions before taking client-facing action.

## A2UI components

The custom catalog in `frontend/src/lib/a2ui-catalog.tsx` defines read-only component types including:

- `WealthMetric` and `WealthMetricGrid`
- `WealthInsightList`
- `WealthComparisonBars` and `WealthBreakdown`
- `WealthTrendLine` and `WealthMultiSeriesTrend`
- `WealthDataTable`
- `WealthProgressList` and `WealthTimeline`
- `WealthCallout`

The catalog uses the ID `wealth-advisor-catalog` and includes the basic A2UI catalog. The backend's configured catalog ID must match it exactly. A2UI output is useful only when the agent emits the surface, the runtime forwards/processes the A2UI operations, and the frontend renderer has compatible catalog definitions.

## Test and troubleshoot

### Verify backend health

Confirm the health endpoint returns successfully and `ag_ui_enabled` is `true`.

### Test the AG-UI stream directly

This test checks whether the backend emits tool calls and surface operations. It does **not** verify that the browser renders them, because it bypasses the Next.js/CopilotKit runtime route.

```powershell
$body = '{"messages":[{"role":"user","content":"Create a simple A2UI surface with a metric card labeled Connectivity Test and value 1. Call the render_a2ui tool instead of describing the card in text."}]}'

curl.exe -N -i http://127.0.0.1:8000/ag-ui `
  -H "Content-Type: application/json" `
  -H "Accept: text/event-stream" `
  --data-binary $body
```

In the previously tested setup, this returned HTTP 200 and the stream contained calls to `generate_a2ui` and `render_a2ui`, followed by A2UI operations for the connectivity test surface. That confirms backend generation on that test, but not frontend rendering.

### If chat displays only text

1. Use the chat inside the running Next.js application, not the direct `curl` request.
2. In browser DevTools, open **Network** and inspect `/api/copilotkit/agent/wealthAdvisor/run`.
3. Check the Python logs for `render_a2ui` calls and the browser request/response for A2UI surface activity or event-processing errors.
4. Confirm `frontend/src/app/api/copilotkit/[[...slug]]/route.ts` routes `wealthAdvisor` to `http://127.0.0.1:8000/ag-ui` (or the `AGENT_URL` value) and configures A2UI processing for that agent.
5. Confirm `frontend/src/app/providers.tsx` uses the installed CopilotKit v2 provider and passes `wealthAdvisorCatalog` to its A2UI configuration.
6. Confirm the catalog ID is exactly `wealth-advisor-catalog` on both sides.
7. Check installed package versions when APIs/types disagree:

   ```powershell
   npm ls @copilotkit/react-core @copilotkit/runtime @copilotkit/a2ui-renderer @copilotkitnext/react @ag-ui/client
   ```

8. Run `npm run typecheck` and `npm run build` after changes. Avoid mixing examples from `@copilotkitnext/react` and `@copilotkit/react-core/v2`; use documentation matching the actual installed versions.

### Alternative if A2UI event rendering remains incompatible

A practical fallback is a typed visualization tool that returns a validated display model (for example, a `metric_grid`, `comparison_bars`, `line_chart`, or `data_table`) and a frontend React renderer that maps those types to existing components. This preserves the conversational agent and deterministic financial service while avoiding dependence on A2UI event translation. Validate all numeric values against the current profile or analysis result; do not let the model invent financial figures.

## API overview

The following endpoints are referenced by the frontend and backend integration; confirm the exact route definitions in your local application:

| Endpoint | Purpose |
|---|---|
| `GET /health` | Local application health/configuration status, if enabled |
| `POST /ag-ui` | AG-UI streaming endpoint used by the CopilotKit runtime |
| `POST /api/wealth/analyze` | Frontend-facing route used to start financial analysis |
| `POST /api/wealth/runs/{run_id}/review` | Frontend-facing route used to submit the human-review decision |

The `/api/wealth/...` paths may be Next.js proxy routes rather than direct FastAPI endpoints in your setup.

## Development principles

- Keep calculations and validation in the deterministic backend workflow where possible.
- Treat the supplied client profile and workflow result as the source of truth.
- Preserve currency codes. Do not combine different currencies without an explicitly supplied exchange rate.
- Keep A2UI components read-only; approval/rejection remains in the application-owned review workflow.
- Never place secrets or real client data in committed examples, screenshots, tests, or logs.

## License

Add the license you intend to use before publishing the repository. Until a license is added, do not assume others have permission to reuse the project.
