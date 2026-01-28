import pytest
from unittest.mock import Mock, patch
from datetime import datetime, timezone, timedelta


@patch("app.api.routes.SwapBid")
def test_create_swap_bid_success(mock_swap_bid_class, client, fake_db, override_db, override_auth):
    mock_home = Mock()
    fake_db.query.return_value.filter.return_value.all.return_value = [mock_home]
    
    mock_bid_instance = Mock()
    mock_bid_instance.id = 1
    mock_bid_instance.user_id = 1
    mock_bid_instance.desired_location = "Paris"
    mock_bid_instance.status = "pending"
    mock_bid_instance.start_date = datetime.now(timezone.utc) + timedelta(days=30)
    mock_bid_instance.end_date = datetime.now(timezone.utc) + timedelta(days=37)
    
    mock_swap_bid_class.return_value = mock_bid_instance
    
    future_start = datetime.now(timezone.utc) + timedelta(days=30)
    future_end = future_start + timedelta(days=7)
    
    bid_data = {
        "desired_location": "Paris",
        "start_date": future_start.isoformat(),
        "end_date": future_end.isoformat()
    }
    
    with patch('app.api.routes.create_swap_match'):
        response = client.post("/api/v1/swap_bids", json=bid_data)
    
    assert response.status_code == 200
    fake_db.add.assert_called_once()
    fake_db.commit.assert_called_once()


def test_create_swap_bid_no_homes(client, fake_db, override_db, override_auth):
    fake_db.query.return_value.filter.return_value.all.return_value = []
    
    future_start = datetime.now(timezone.utc) + timedelta(days=30)
    future_end = future_start + timedelta(days=7)
    
    bid_data = {
        "desired_location": "Paris",
        "start_date": future_start.isoformat(),
        "end_date": future_end.isoformat()
    }
    
    response = client.post("/api/v1/swap_bids", json=bid_data)
    
    assert response.status_code == 400
    assert "must have at least one home" in response.json()["detail"]


def test_create_swap_bid_invalid_dates(client, fake_db, override_db, override_auth):
    mock_home = Mock()
    fake_db.query.return_value.filter.return_value.all.return_value = [mock_home]
    
    past_date = datetime.now(timezone.utc) - timedelta(days=1)
    future_date = datetime.now(timezone.utc) + timedelta(days=30)
    

    bid_data = {
        "desired_location": "Paris",
        "start_date": past_date.isoformat(),
        "end_date": future_date.isoformat()
    }
    
    response = client.post("/api/v1/swap_bids", json=bid_data)
    assert response.status_code == 400
    assert "must be in the future" in response.json()["detail"]
    
   
    bid_data["start_date"] = future_date.isoformat()
    bid_data["end_date"] = (future_date - timedelta(days=1)).isoformat()
    
    response = client.post("/api/v1/swap_bids", json=bid_data)
    assert response.status_code == 400
    assert "must be after" in response.json()["detail"]


def test_create_swap_bid_unauthorized(client, fake_db, override_db):
    future_start = datetime.now(timezone.utc) + timedelta(days=30)
    future_end = future_start + timedelta(days=7)
    
    bid_data = {
        "desired_location": "Paris",
        "start_date": future_start.isoformat(),
        "end_date": future_end.isoformat()
    }
    
    response = client.post("/api/v1/swap_bids", json=bid_data)
    
    assert response.status_code == 401
    assert response.json()["detail"] == "Not authenticated"


def test_list_my_swap_bids_success(client, fake_db, override_db, override_auth, create_mock_swap_bid):
    mock_bids = [
        create_mock_swap_bid(1, 1, "Paris"),
        create_mock_swap_bid(2, 1, "London")
    ]
    fake_db.query.return_value.filter.return_value.all.return_value = mock_bids
    
    response = client.get("/api/v1/swap_bids")
    
    assert response.status_code == 200
    bids = response.json()
    assert len(bids) == 2
    assert bids[0]["desired_location"] == "Paris"


def test_list_my_swap_bids_unauthorized(client, fake_db, override_db):
    response = client.get("/api/v1/swap_bids")
    
    assert response.status_code == 401
    assert response.json()["detail"] == "Not authenticated"


def test_get_swap_bid_success(client, fake_db, override_db, create_mock_swap_bid):
    mock_bid = create_mock_swap_bid()
    fake_db.query.return_value.filter.return_value.first.return_value = mock_bid
    
    response = client.get("/api/v1/swap_bids/1")
    
    assert response.status_code == 200
    body = response.json()
    assert body["id"] == 1
    assert body["desired_location"] == "Paris"


def test_get_swap_bid_not_found(client, fake_db, override_db):
    fake_db.query.return_value.filter.return_value.first.return_value = None
    
    response = client.get("/api/v1/swap_bids/999")
    
    assert response.status_code == 404
    assert response.json()["detail"] == "Swap bid not found"