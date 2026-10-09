# Research Notes — Microsoft Agent Framework

Research date: 2026-10-09.

## Findings used in the implementation

1. Microsoft Agent Framework provides Python Agent and workflow abstractions. The current Python documentation exposes `Agent` and `WorkflowBuilder`, with workflow graphs coordinating executors and message routing.

2. Azure OpenAI in current Python Agent Framework uses the provider package `agent-framework-openai` and the generic `agent_framework.openai.OpenAIChatClient`. Microsoft documents `OpenAIChatClient` as the Responses API path and supports Azure routing via explicit `azure_endpoint`, `api_key`, and optional `api_version`. Microsoft Foundry project inference separately uses `agent_framework.foundry.FoundryChatClient`.

3. Structured outputs are supported by passing a Pydantic model as the `response_format` option when invoking an Agent. The project uses this for `OrchestrationPlan`, `AnalyzerNarrative`, and `AdvisoryOutput`.

4. Microsoft Agent Framework supports human-in-the-loop using workflow request/response handling. A workflow executor can call `ctx.request_info(...)`; after a response is supplied, a `@response_handler` resumes execution. Pending requests can be captured by workflow checkpoints.

5. The framework also exposes `FileCheckpointStorage`, and current workflow documentation describes checkpointing of executor state, pending messages, requests and shared state.

6. The current PyPI release history observed during research showed `agent-framework-core==1.21.0` released 2026-10-08, `agent-framework-openai==1.16.0` released 2026-10-08, and `agent-framework-foundry==1.14.1` released 2026-10-08. The OpenAI provider is a separate package because the core package intentionally has slim provider dependencies.

7. The framework's current samples use `Agent` rather than the older `ChatAgent` name and construct Foundry-backed Agents explicitly. The project follows this current naming/API style.

## Engineering conclusions

- Use Microsoft Agent Framework for agent construction and workflow orchestration.
- Use deterministic Python for money/risk calculations and anomaly decisions.
- Use Pydantic structured output schemas at agent boundaries.
- Use a provider-neutral application `Tool` interface so the agents/workflow do not depend on raw CRM implementation details.
- Keep an offline mock adapter so reviewers can run the deterministic system without Azure credentials.
- Put a human checkpoint before treating HIGH/CRITICAL recommendations as approved decision support.

## Official sources

- https://learn.microsoft.com/en-us/agent-framework/
- https://learn.microsoft.com/en-us/agent-framework/agents/providers/openai
- https://learn.microsoft.com/en-us/agent-framework/agents/providers/microsoft-foundry
- https://learn.microsoft.com/en-us/agent-framework/agents/structured-outputs
- https://learn.microsoft.com/en-us/agent-framework/concepts/workflows/builder-and-execution?pivots=programming-language-python
- https://learn.microsoft.com/en-us/agent-framework/workflows/human-in-the-loop
- https://learn.microsoft.com/en-us/agent-framework/workflows/checkpoints
- https://github.com/microsoft/agent-framework
- https://pypi.org/project/agent-framework-core/
- https://pypi.org/project/agent-framework-openai/
- https://pypi.org/project/agent-framework-foundry/
