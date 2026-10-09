import { HttpAgent } from "@ag-ui/client";
import {
  CopilotRuntime,
  createCopilotRuntimeHandler,
} from "@copilotkit/runtime/v2";

/**
 * Microsoft Agent Framework AG-UI backend.
 *
 * Set AGENT_URL in frontend/.env.local if your backend uses a
 * different hostname or port.
 */
const agentUrl =
  process.env.AGENT_URL?.trim() ||
  "http://127.0.0.1:8000/ag-ui";

const wealthAdvisorAgent = new HttpAgent({
  url: agentUrl,
});

/**
 * Configure the CopilotKit runtime.
 *
 * The A2UI middleware:
 * - Targets the wealthAdvisor agent.
 * - Enables the A2UI tool-injection flag in the forwarded request.
 * - Processes A2UI output from the Agent Framework endpoint.
 *
 * The Python backend already registers its A2UI endpoint and catalog ID.
 */
const runtime = new CopilotRuntime({
  agents: {
    wealthAdvisor: wealthAdvisorAgent,
  },

  a2ui: {
    injectA2UITool: true,
    agents: ["wealthAdvisor"],
  },
});

/**
 * Keep the default multi-route transport.
 *
 * The frontend provider must use the same transport mode.
 */
const handler = createCopilotRuntimeHandler({
  runtime,
  basePath: "/api/copilotkit",
});

export const GET = handler;
export const POST = handler;
export const PATCH = handler;
export const DELETE = handler;