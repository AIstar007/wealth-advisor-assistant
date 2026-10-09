class WealthAdvisorError(Exception):
    """Base error for expected application failures."""


class ToolError(WealthAdvisorError):
    """A tool failed or returned unusable data."""


class WorkflowPaused(WealthAdvisorError):
    """The workflow is intentionally waiting for human input."""


def normalize_review_decision(decision: str) -> str:
    """Normalize and validate a human review command before it reaches the workflow."""
    normalized = decision.strip()
    upper = normalized.upper()
    if upper not in {"APPROVE", "REJECT"} and not upper.startswith("OVERRIDE:"):
        raise ValueError("Decision must be APPROVE, REJECT, or OVERRIDE: <comment>")
    return normalized
