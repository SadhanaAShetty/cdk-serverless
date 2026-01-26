import pytest
from fastapi.testclient import TestClient
from unittest.mock import Mock, patch
from fastapi import HTTPException

from app.main import app
from app.db import get_db
from app.services.auth import get_current_user


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


@pytest.fixture
def mock_current_user():
    mock_user = Mock()
    mock_user.id = 1
    mock_user.name = "Test User"
    mock_user.email = "test@example.com"
    mock_user.verified = 1
    mock_user.profile_complete = 1
    mock_user.preferences = None
    mock_user.notification_settings = None
    return mock_user


@pytest.fixture
def override_auth(test_app, mock_current_user):
    def _get_current_user():
        return mock_current_user
    
    test_app.dependency_overrides[get_current_user] = _get_current_user
    yield
    test_app.dependency_overrides.clear()


fake_user = {
    "name": "Test User",
    "email": "example@example.com",
    "password": "password123"
}

fake_login_data = {
    "email": "test@example.com",
    "password": "password123"
}

fake_token_response = {
    "access_token": "fake_jwt_token_12345",
    "token_type": "bearer"
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



@patch('app.api.routes.login_user')
def test_login_user_success(mock_login_user, client, fake_db, override_db):
    mock_login_user.return_value = {
        "access_token": "fake_jwt_token_12345", 
        "token_type": "bearer"
    }
    login_data = {"email": "test@example.com", "password": "password123"}

    response = client.post("/api/v1/auth/login", json=login_data)

    assert response.status_code == 200
    body = response.json()
    assert body["access_token"] == "fake_jwt_token_12345"
    assert body["token_type"] == "bearer"

    mock_login_user.assert_called_once_with(fake_db, "test@example.com", "password123")


@patch('app.api.routes.login_user')
def test_login_user_invalid_credentials(mock_login_user, client, fake_db, override_db):
    mock_login_user.side_effect = HTTPException(status_code=401, detail="Invalid email or password")
    login_data = {"email": "test@example.com", "password": "wrongpassword"}

    response = client.post("/api/v1/auth/login", json=login_data)

    assert response.status_code == 401
    assert response.json()["detail"] == "Invalid email or password"
    mock_login_user.assert_called_once_with(fake_db, "test@example.com", "wrongpassword")



@pytest.mark.parametrize(
    "login_data, missing_field",
    [
        ({"email": "test@example.com"}, "password"),
        ({"password": "password123"}, "email"),
        ({}, "email"),  
    ]
)
def test_login_user_missing_fields(client, login_data, fake_db, missing_field, override_db):
    response = client.post("/api/v1/auth/login", json=login_data)

    assert response.status_code == 422

    errors = response.json()["detail"]
    assert any(err["loc"][-1] == missing_field for err in errors)


def test_protected_route_unauthorized(client, fake_db, override_db):
    response = client.get("/api/v1/auth/me")

    assert response.status_code == 401
    assert response.json()["detail"] == "Not authenticated"

def test_protected_route_invalid_token(client, fake_db, override_db):
    headers = {"Authorization": "Bearer invalid_token_123"}
    response = client.get("/api/v1/auth/me", headers=headers) 
    assert response.status_code == 401

def test_protected_route_valid_token(client, fake_db, override_db, override_auth):
    headers = {"Authorization": "Bearer valid_token_123"}
    response = client.get("/api/v1/auth/me", headers=headers)
    
    assert response.status_code == 200
    body = response.json()
    assert body["email"] == "test@example.com"
    assert body["name"] == "Test User"
    assert body["id"] == 1
    assert body["verified"] == 1
    assert body["profile_complete"] == 1


