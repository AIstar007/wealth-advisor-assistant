from __future__ import annotations

import argparse
import asyncio
import sys

from dotenv import load_dotenv

from app.config import ENV_FILE, Settings


def _mask(value: str | None) -> str:
    if not value:
        return "MISSING"
    if len(value) <= 8:
        return "SET"
    return f"SET ({value[:4]}…{value[-4:]})"


def check_configuration(settings: Settings) -> bool:
    print("=== Wealth Advisor configuration ===")
    print(f"Project root: {ENV_FILE.parent}")
    print(f".env exists: {ENV_FILE.exists()}")
    print(f"RUN_MODE: {settings.run_mode}")
    print(f"AZURE_OPENAI_ENDPOINT: {settings.azure_openai_endpoint or 'MISSING'}")
    print(f"AZURE_OPENAI_BASE_URL: {settings.azure_openai_base_url or 'MISSING'}")
    print(f"AZURE_OPENAI_DEPLOYMENT: {settings.azure_openai_deployment or 'MISSING'}")
    print(f"AZURE_OPENAI_API_KEY: {_mask(settings.azure_openai_api_key)}")

    if settings.run_mode in {"azure", "azure_openai"}:
        try:
            settings.validate_azure_openai()
        except RuntimeError as exc:
            print(f"CONFIGURATION ERROR: {exc}")
            return False
    elif settings.run_mode == "foundry":
        try:
            settings.validate_foundry()
        except RuntimeError as exc:
            print(f"CONFIGURATION ERROR: {exc}")
            return False
    elif settings.run_mode != "mock":
        print("CONFIGURATION ERROR: RUN_MODE must be mock, azure_openai, or foundry")
        return False

    try:
        import importlib

        importlib.import_module("agent_framework")
        print("Microsoft Agent Framework: import OK")
    except ImportError as exc:
        print(f"Microsoft Agent Framework: MISSING ({exc})")
        return False

    if settings.run_mode in {"azure", "azure_openai"}:
        try:
            importlib.import_module("agent_framework.openai")
            print("Agent Framework Azure OpenAI provider: import OK")
        except ImportError as exc:
            print(f"Agent Framework Azure OpenAI provider: MISSING ({exc})")
            return False

    return True


async def live_azure_smoke_test(settings: Settings) -> None:
    settings.validate_azure_openai()
    from agent_framework import Agent
    from agent_framework.openai import OpenAIChatClient

    client_kwargs: dict[str, object] = {
        "model": settings.azure_openai_deployment,
        "api_key": settings.azure_openai_api_key,
    }
    if settings.azure_openai_base_url:
        client_kwargs["base_url"] = settings.azure_openai_base_url
    else:
        client_kwargs["azure_endpoint"] = settings.azure_openai_endpoint
    if settings.azure_openai_api_version:
        client_kwargs["api_version"] = settings.azure_openai_api_version

    agent = Agent(
        client=OpenAIChatClient(**client_kwargs),
        name="AzureConnectionSmokeTest",
        instructions="Return exactly the word PONG. Do not add punctuation or explanation.",
    )
    response = await agent.run("PING")
    text = (response.text or "").strip()
    if not text:
        raise RuntimeError("Azure OpenAI returned an empty response")
    print(f"Azure OpenAI response: {text!r}")
    if text.upper() != "PONG":
        raise RuntimeError(f"Unexpected smoke-test response; expected PONG, received {text!r}")
    print("LIVE SMOKE TEST: PASS")


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate Wealth Advisor runtime configuration.")
    parser.add_argument(
        "--live",
        action="store_true",
        help="Make one real Azure OpenAI request. Never prints the API key.",
    )
    args = parser.parse_args()

    load_dotenv(dotenv_path=ENV_FILE, override=False)
    settings = Settings()
    if not check_configuration(settings):
        return 1

    if args.live:
        if settings.run_mode not in {"azure", "azure_openai"}:
            print("LIVE TEST ERROR: set RUN_MODE=azure_openai first")
            return 1
        try:
            asyncio.run(live_azure_smoke_test(settings))
        except Exception as exc:
            print(f"LIVE SMOKE TEST: FAIL — {type(exc).__name__}: {exc}")
            return 1

    print("CONFIGURATION CHECK: PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
