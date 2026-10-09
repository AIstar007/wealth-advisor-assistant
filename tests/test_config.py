from app.config import PROJECT_ROOT, Settings


def test_project_root_has_env_example():
    assert (PROJECT_ROOT / ".env.example").exists()


def test_azure_settings_validate_with_key_values(monkeypatch):
    monkeypatch.setenv("AZURE_OPENAI_ENDPOINT", "https://example.openai.azure.com/")
    monkeypatch.setenv("AZURE_OPENAI_API_KEY", "test-key")
    monkeypatch.setenv("AZURE_OPENAI_DEPLOYMENT", "test-deployment")
    monkeypatch.setenv("RUN_MODE", "azure_openai")

    settings = Settings(
        run_mode="azure_openai",
        azure_openai_endpoint="https://example.openai.azure.com/",
        azure_openai_api_key="test-key",
        azure_openai_deployment="test-deployment",
    )
    settings.validate_azure_openai()


def test_azure_base_url_is_valid_without_resource_endpoint():
    settings = Settings(
        run_mode="azure_openai",
        azure_openai_endpoint=None,
        azure_openai_base_url="https://example.openai.azure.com/openai/v1",
        azure_openai_api_key="test-key",
        azure_openai_deployment="test-deployment",
    )
    settings.validate_azure_openai()
