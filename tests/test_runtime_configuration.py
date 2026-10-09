import pytest

from app.agents.runtime import create_agent
from app.config import Settings


@pytest.mark.asyncio
async def test_mock_runtime_creates_structured_agent():
    settings = Settings(run_mode="mock")
    agent = create_agent(settings, name="TestAgent", instructions="test")
    assert agent.name == "TestAgent"



def test_invalid_review_decision_is_rejected():
    from app.utils.errors import normalize_review_decision

    import pytest

    with pytest.raises(ValueError, match="Decision must be"):
        normalize_review_decision("MAYBE")

    assert normalize_review_decision(" OVERRIDE: Reviewed with client ") == "OVERRIDE: Reviewed with client"
