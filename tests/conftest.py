import pytest


@pytest.fixture(autouse=True)
def _jwt_secret(monkeypatch: pytest.MonkeyPatch) -> None:
    """Offline tests use a throwaway signing secret (not a credential of any real system)."""
    monkeypatch.setenv("JWT_SECRET", "test-only-secret-" + "x" * 32)
