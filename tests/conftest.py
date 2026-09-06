import pytest


@pytest.fixture(autouse=True)
def isolate_espdocs_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    for name in (
        "ESP_HARDWARE_KNOWLEDGE_ROOT",
        "ESPDOCS_DATA_ROOT",
        "ESPDOCS_DEVICE",
        "ESPDOCS_REPO_ROOT",
        "ESPDOCS_SOURCE_BASE",
    ):
        monkeypatch.delenv(name, raising=False)
