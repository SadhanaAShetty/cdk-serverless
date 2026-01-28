import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
from fastapi.testclient import TestClient
from unittest.mock import Mock, patch
from datetime import datetime, timezone, timedelta

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
    yield mock_current_user
    test_app.dependency_overrides.clear()


@pytest.fixture
def sample_home_data():
    future_date_from = datetime.now(timezone.utc).replace(microsecond=0) + timedelta(days=30)
    future_date_to = future_date_from + timedelta(days=7)
    
    return {
        "name": "Cozy Cottage",
        "location": "Rotterdam", 
        "room_count": 3,
        "home_type": "cottage",
        "amenities": ["wifi", "kitchen", "parking"],
        "house_rules": {
            "smoking_allowed": False,
            "pets_allowed": True,
            "max_guests": 4,
            "quiet_hours": "22:00-08:00"
        },
        "photos": ["photo1.jpg", "photo2.jpg"],
        "available_from": future_date_from.isoformat(),
        "available_to": future_date_to.isoformat()
    }


@pytest.fixture
def create_mock_home():
    def _create_mock_home(home_id=1, name="Test Home", location="Amsterdam", owner_id=1):
        mock_home = Mock()
        mock_home.id = home_id
        mock_home.name = name
        mock_home.location = location
        mock_home.room_count = 3
        mock_home.home_type = "apartment"
        mock_home.amenities = ["wifi", "kitchen"]
        mock_home.house_rules = {"pets_allowed": True}
        mock_home.photos = []
        mock_home.available_from = datetime.now(timezone.utc)
        mock_home.available_to = datetime.now(timezone.utc) + timedelta(days=7)
        mock_home.owner_id = owner_id
        return mock_home
    return _create_mock_home


@pytest.fixture
def create_mock_swap_bid():
    def _create_mock_swap_bid(bid_id=1, user_id=1, location="Paris", status="pending"):
        mock_bid = Mock()
        mock_bid.id = bid_id
        mock_bid.user_id = user_id
        mock_bid.desired_location = location
        mock_bid.start_date = datetime.now(timezone.utc) + timedelta(days=30)
        mock_bid.end_date = datetime.now(timezone.utc) + timedelta(days=37)
        mock_bid.status = status
        return mock_bid
    return _create_mock_swap_bid


@pytest.fixture
def create_mock_match():
    def _create_mock_match(match_id=1, bid_a_id=1, bid_b_id=2, status="proposed"):
        mock_match = Mock()
        mock_match.id = match_id
        mock_match.bid_a_id = bid_a_id
        mock_match.bid_b_id = bid_b_id
        mock_match.status = status
        mock_match.match_date = datetime.now(timezone.utc)
        return mock_match
    return _create_mock_match