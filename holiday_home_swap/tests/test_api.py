import pytest
from fastapi.testclient import TestClient
from unittest.mock import Mock, patch

from app.main import app
from app.db import get_db


@pytest.fixture
def test_app():
    return app


@pytest.fixture
def client(test_app):
    return TestClient(test_app)


@pytest.fixture
def fake_db():
    db = Mock()
    return db

@pytest.fixture
def override_db(test_app, fake_db):
    def fake_get_db():
        yield fake_db

    test_app.dependency_overrides[get_db] = fake_get_db
    yield
    test_app.dependency_overrides.clear()


fake_user = {
    "name": "Test User",
    "email": "example@example.com",
    "password": "password123"
}


@patch('app.api.routes.User')
def test_create_user_success(mock_user_class, client, fake_db, override_db):
    fake_db.query.return_value.filter.return_value.first.return_value = None
    
    # Mock the User class constructor
    mock_user_instance = Mock()
    mock_user_instance.id = 1
    mock_user_instance.name = fake_user["name"]
    mock_user_instance.email = fake_user["email"]
    mock_user_instance.verified = 0
    mock_user_instance.profile_complete = 0
    mock_user_instance.preferences = None
    mock_user_instance.notification_settings = None
    
    mock_user_class.return_value = mock_user_instance

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



@pytest.mark.parametrize(
    "bad_user, missing_field",
    [
        ({"name": "Test User", "email": "example@example.com"}, "password"),
        ({"name": "Test User", "password": "password123"}, "email"),
        ({"email": "example@example.com", "password": "password123"}, "name"),
    ]
)
def test_create_user_missing_fields(client, fake_db, override_db, bad_user, missing_field):
    response = client.post("/api/v1/users/", json=bad_user)

    
    assert response.status_code == 422

    errors = response.json()["detail"]

    
    assert any(err["loc"][-1] == missing_field for err in errors)

    
    fake_db.query.assert_not_called()
    fake_db.add.assert_not_called()
    fake_db.commit.assert_not_called()
    fake_db.refresh.assert_not_called()

@pytest.mark.parametrize(
    "weak_password",
    [
        {
            "name": "Test User",
            "email": "example@example.com",
            "password": "123"
        }
    ]
)
def test_create_user_very_short_password(client, fake_db, override_db,weak_password):
    response = client.post("/api/v1/users/", json= weak_password)

    assert response.status_code == 422
    errors = response.json()["detail"]

    fields = [err["loc"][-1] for err in errors]
    assert "password" in fields
    fake_db.query.assert_not_called()
    fake_db.add.assert_not_called()
    fake_db.commit.assert_not_called()
    fake_db.refresh.assert_not_called()



@pytest.mark.parametrize(
    "invalid_password, expected_error",
    [
        ("", "too_short"),  
        ("1234567", "too_short"),   
        ("short", "too_short"),      
        ("a" * 17, "too_long"),     
        ("a" * 25, "too_long"),     
        ("   ", "too_short"),        
        ("abc def", "too_short"),    
    ]
)
def test_invalid_password_format(client, fake_db, override_db, invalid_password, expected_error):
    invalid_user = {
        "name": "Test User",
        "email": "test@example.com",
        "password": invalid_password
    }
    
    response = client.post("/api/v1/users/", json=invalid_user)
    
    assert response.status_code == 422
    
    errors = response.json()["detail"]
    password_errors = [err for err in errors if err["loc"][-1] == "password"]
    
    assert len(password_errors) > 0, "Password field should have validation error"
    
    # Check specific error type
    error_msg = password_errors[0]["msg"].lower()
    if expected_error == "too_short":
        assert "at least 8 characters" in error_msg or "too short" in error_msg
    elif expected_error == "too_long":
        assert "at most 16 characters" in error_msg or "too long" in error_msg
    
    
    fake_db.query.assert_not_called()
    fake_db.add.assert_not_called()
    fake_db.commit.assert_not_called()
    fake_db.refresh.assert_not_called()




