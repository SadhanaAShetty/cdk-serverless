import pytest
from fastapi.testclient import TestClient
from unittest.mock import Mock

from holiday_home_swap.api import create_app
from holiday_home_swap.app.db import get_db


@pytest.fixture
def app():
    return create_app()


@pytest.fixture
def client(app):
    return TestClient(app)


@pytest.fixture
def fake_db():
    db = Mock()
    return db


@pytest.fixture
def override_db(app, fake_db):
    def _get_db():
        yield fake_db

    app.dependency_overrides[get_db] = _get_db
    yield
    app.dependency_overrides.clear()


fake_user = {
    "name": "Test User",
    "email": "example@example.com",
    "password": "password123"
}

def test_create_user_success(client, fake_db, override_db):
    fake_db.query.return_value.filter.return_value.first.return_value = None

    response = client.post("/api/v1/users/", json=fake_user)

    assert response.status_code == 201

    body = response.json()
    assert body["email"] == fake_user["email"]
    assert body["name"] == fake_user["name"]
    assert "password_hash" not in body

    fake_db.query.assert_called_once()
    fake_db.add.assert_called_once()
    fake_db.commit.assert_called_once()
    fake_db.refresh.assert_called_once()


def test_user_already_exists(client, fake_db, override_db):
    fake_existing = Mock()
    fake_db.query.return_value.filter.return_value.first.return_value = fake_existing

    response = client.post("/api/v1/users/", json=fake_user)

    assert response.status_code == 400
    assert response.json()["detail"] == "User with this email already exists"

    fake_db.query.assert_called_once()
    fake_db.add.assert_not_called()
    fake_db.commit.assert_not_called()
    fake_db.refresh.assert_not_called()

