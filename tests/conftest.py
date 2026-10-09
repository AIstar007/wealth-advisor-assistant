import sys
import types

# Allow analysis/memory/unit tests to run in a minimal environment where
# Microsoft Agent Framework is not installed. Integration/runtime execution
# still imports the real package from requirements.txt.
if "agent_framework" not in sys.modules:
    agent_framework = types.ModuleType("agent_framework")
    agent_framework.Executor = type("Executor", (), {"__init__": lambda self, id=None: setattr(self, "id", id)})
    agent_framework.WorkflowContext = object
    agent_framework.handler = lambda fn: fn
    agent_framework.response_handler = lambda fn: fn
    sys.modules["agent_framework"] = agent_framework
