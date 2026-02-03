import pytest
from unittest.mock import Mock, patch
from datetime import datetime, timezone, timedelta


@patch("app.api.routes.Home")
def test_create_home_success(mock_home_class, client, fake_db, override_db, override_auth, sample_home_data):
    available_from = datetime.fromisoformat(sample_home_data["available_from"].replace('Z', '+00:00'))
    available_to = datetime.fromisoformat(sample_home_data["available_to"].replace('Z', '+00:00'))
    
    mock_home_instance = Mock()
    mock_home_instance.id = 1
    mock_home_instance.name = "Cozy Cottage"
    mock_home_instance.location = "Rotterdam"
    mock_home_instance.room_count = 3
    mock_home_instance.home_type = "cottage"
    mock_home_instance.amenities = ["wifi", "kitchen", "parking"]
    mock_home_instance.house_rules = {
        "smoking_allowed": False,
        "pets_allowed": True,
        "max_guests": 4,
        "quiet_hours": "22:00-08:00"
    }
    mock_home_instance.photos = ["photo1.jpg", "photo2.jpg"]
    mock_home_instance.available_from = available_from
    mock_home_instance.available_to = available_to
    mock_home_instance.owner_id = 1

    mock_home_class.return_value = mock_home_instance

    response = client.post("/api/v1/homes", json=sample_home_data)

    assert response.status_code == 200

    body = response.json()
    assert body["name"] == "Cozy Cottage"
    assert body["location"] == "Rotterdam"
    assert body["room_count"] == 3
    assert body["home_type"] == "cottage"
    assert body["owner_id"] == 1
    
    fake_db.add.assert_called_once()
    fake_db.commit.assert_called_once()
    fake_db.refresh.assert_called_once()


def test_create_home_unauthorized(client, fake_db, override_db, sample_home_data):
    response = client.post("/api/v1/homes", json=sample_home_data)

    assert response.status_code == 401
    assert response.json()["detail"] == "Not authenticated"


def test_create_home_missing_fields(client, fake_db, override_db, override_auth):
    incomplete_home_data = {
        "name": "Cozy Cottage",
        "location": "Rotterdam", 
    }

    response = client.post("/api/v1/homes", json=incomplete_home_data)

    assert response.status_code == 422

    errors = response.json()["detail"]
    required_fields = ["room_count", "home_type", "available_from", "available_to"]
    for field in required_fields:
        assert any(err["loc"][-1] == field for err in errors)

    fake_db.add.assert_not_called()
    fake_db.commit.assert_not_called()
    fake_db.refresh.assert_not_called()


def test_create_home_invalid_dates(client, fake_db, override_db, override_auth):
    past_date = datetime.now(timezone.utc) - timedelta(days=1)
    future_date = datetime.now(timezone.utc) + timedelta(days=30)
    
 
    invalid_home_data = {
        "name": "Test Home",
        "location": "Amsterdam",
        "room_count": 2,
        "home_type": "apartment",
        "available_from": past_date.isoformat(),
        "available_to": future_date.isoformat()
    }
    
    response = client.post("/api/v1/homes", json=invalid_home_data)
    assert response.status_code == 400
    assert "must be in the future" in response.json()["detail"]
    

    invalid_home_data["available_from"] = future_date.isoformat()
    invalid_home_data["available_to"] = (future_date - timedelta(days=1)).isoformat()
    
    response = client.post("/api/v1/homes", json=invalid_home_data)
    assert response.status_code == 400
    assert "must be after" in response.json()["detail"]


def test_create_home_valid_dates(client, fake_db, override_db, override_auth, sample_home_data):
    with patch("app.api.routes.Home") as mock_home_class:
        mock_home_instance = Mock()
        mock_home_instance.id = 1
        mock_home_instance.name = sample_home_data["name"]
        mock_home_instance.location = sample_home_data["location"]
        mock_home_instance.room_count = sample_home_data["room_count"]
        mock_home_instance.home_type = sample_home_data["home_type"]
        mock_home_instance.amenities = sample_home_data["amenities"]
        mock_home_instance.house_rules = sample_home_data["house_rules"]
        mock_home_instance.photos = sample_home_data["photos"]
        mock_home_instance.available_from = datetime.fromisoformat(sample_home_data["available_from"])
        mock_home_instance.available_to = datetime.fromisoformat(sample_home_data["available_to"])
        mock_home_instance.owner_id = 1
        
        mock_home_class.return_value = mock_home_instance
        
        response = client.post("/api/v1/homes", json=sample_home_data)
        
        assert response.status_code == 200
        body = response.json()
        assert body["name"] == sample_home_data["name"]
        fake_db.add.assert_called_once()
        fake_db.commit.assert_called_once()


def test_get_home_success(client, fake_db, override_db, create_mock_home):
    mock_home = create_mock_home()
    fake_db.query.return_value.filter.return_value.first.return_value = mock_home
    
    with patch('app.api.routes.image_storage.generate_presigned_urls', return_value=[]):
        response = client.get("/api/v1/homes/1")
        
        assert response.status_code == 200
        body = response.json()
        assert body["id"] == 1
        assert body["name"] == "Test Home"


def test_get_home_not_found(client, fake_db, override_db):
    fake_db.query.return_value.filter.return_value.first.return_value = None
    
    response = client.get("/api/v1/homes/999")
    
    assert response.status_code == 404
    assert response.json()["detail"] == "Home not found"


def test_list_homes_success(client, fake_db, override_db, create_mock_home):
    mock_homes = [
        create_mock_home(1, "Home 1", "Amsterdam"),
        create_mock_home(2, "Home 2", "Rotterdam")
    ]
    fake_db.query.return_value.all.return_value = mock_homes
    
    with patch('app.api.routes.image_storage.generate_presigned_urls', return_value=[]):
        response = client.get("/api/v1/listings")
        
        assert response.status_code == 200
        homes = response.json()
        assert len(homes) == 2
        assert homes[0]["name"] == "Home 1"


def test_upload_home_photos_unauthorized(client, fake_db, override_db):
    response = client.post("/api/v1/homes/1/photos")
    
    assert response.status_code == 401
    assert response.json()["detail"] == "Not authenticated"


def test_upload_home_photos_home_not_found(client, fake_db, override_db, override_auth):
    fake_db.query.return_value.filter.return_value.first.return_value = None
    
    
    files = {"files": ("test.jpg", b"fake image data", "image/jpeg")}
    
    response = client.post("/api/v1/homes/999/photos", files=files)
    
    assert response.status_code == 404
    assert response.json()["detail"] == "Home not found"