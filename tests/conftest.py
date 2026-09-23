from collections.abc import Callable, Iterator

import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def client(tmp_path, monkeypatch) -> Iterator[TestClient]:
    db_file = tmp_path / "test.db"
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{db_file.as_posix()}")
    monkeypatch.setenv("SECRET_KEY", "test-secret-key-not-for-production")
    monkeypatch.setenv("PAYMENT_WEBHOOK_SECRET", "test-webhook-secret")
    monkeypatch.setenv("SEED_ON_STARTUP", "true")

    from app.config import get_settings
    from app.db import reset_db_state
    from app.services.cache import cache

    get_settings.cache_clear()
    reset_db_state()
    cache.clear()

    from app.main import app

    with TestClient(app) as test_client:
        yield test_client

    reset_db_state()
    get_settings.cache_clear()
    cache.clear()


@pytest.fixture
def login(client: TestClient) -> Callable[[str, str], dict[str, str]]:
    def _login(username: str, password: str) -> dict[str, str]:
        response = client.post("/auth/login", json={"username": username, "password": password})
        assert response.status_code == 200, response.text
        token = response.json()["access_token"]
        return {"Authorization": f"Bearer {token}"}

    return _login
