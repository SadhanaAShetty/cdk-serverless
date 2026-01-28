import pytest
from unittest.mock import Mock, patch
from datetime import datetime, timezone, timedelta


def test_get_my_matches_success(client, fake_db, override_db, override_auth, mock_current_user, create_mock_match):
    mock_current_user.bids = [Mock(id=1), Mock(id=2)]
    mock_matches = [
        create_mock_match(1, 1, 2),
        create_mock_match(2, 3, 1)
    ]
    fake_db.query.return_value.filter.return_value.all.return_value = mock_matches
    
    response = client.get("/api/v1/matches")
    
    assert response.status_code == 200
    matches = response.json()
    assert len(matches) == 2
    assert matches[0]["status"] == "proposed"


def test_get_my_matches_unauthorized(client, fake_db, override_db):
    response = client.get("/api/v1/matches")
    
    assert response.status_code == 401
    assert response.json()["detail"] == "Not authenticated"


def test_get_match_details_not_found(client, fake_db, override_db, override_auth):
    fake_db.query.return_value.filter.return_value.first.return_value = None
    
    response = client.get("/api/v1/matches/999")
    
    assert response.status_code == 404
    assert response.json()["detail"] == "Match not found"


def test_accept_match_success(client, fake_db, override_db, override_auth):
    mock_match = Mock()
    mock_match.id = 1
    mock_match.status = "proposed"
    mock_match.bid_a_id = 1
    mock_match.bid_b_id = 2
    
    mock_bid_a = Mock()
    mock_bid_a.user_id = 1  
    mock_bid_b = Mock()
    mock_bid_b.user_id = 2
    
    fake_db.query.return_value.filter.return_value.first.side_effect = [
        mock_match, mock_bid_a, mock_bid_b
    ]
    
    response = client.put("/api/v1/matches/1/accept")
    
    assert response.status_code == 200
    assert response.json()["message"] == "Match accepted successfully"
    assert mock_match.status == "accepted"
    assert mock_bid_a.status == "accepted"
    assert mock_bid_b.status == "accepted"


def test_accept_match_not_found(client, fake_db, override_db, override_auth):
    fake_db.query.return_value.filter.return_value.first.return_value = None
    
    response = client.put("/api/v1/matches/999/accept")
    
    assert response.status_code == 404
    assert response.json()["detail"] == "Match not found"


def test_accept_match_unauthorized(client, fake_db, override_db, override_auth):
    mock_match = Mock()
    mock_match.id = 1
    mock_match.bid_a_id = 1
    mock_match.bid_b_id = 2
    
    mock_bid_a = Mock()
    mock_bid_a.user_id = 3 
    mock_bid_b = Mock()
    mock_bid_b.user_id = 4  
    
    fake_db.query.return_value.filter.return_value.first.side_effect = [
        mock_match, mock_bid_a, mock_bid_b
    ]
    
    response = client.put("/api/v1/matches/1/accept")
    
    assert response.status_code == 403
    assert response.json()["detail"] == "Not authorized to change this match"


def test_accept_match_wrong_status(client, fake_db, override_db, override_auth):
    mock_match = Mock()
    mock_match.id = 1
    mock_match.status = "accepted"  
    mock_match.bid_a_id = 1
    mock_match.bid_b_id = 2
    
    mock_bid_a = Mock()
    mock_bid_a.user_id = 1 
    mock_bid_b = Mock()
    mock_bid_b.user_id = 2
    
    fake_db.query.return_value.filter.return_value.first.side_effect = [
        mock_match, mock_bid_a, mock_bid_b
    ]
    
    response = client.put("/api/v1/matches/1/accept")
    
    assert response.status_code == 400
    assert response.json()["detail"] == "Match is not in a proposed state"


def test_reject_match_success(client, fake_db, override_db, override_auth):
    mock_match = Mock()
    mock_match.id = 1
    mock_match.status = "proposed"
    mock_match.bid_a_id = 1
    mock_match.bid_b_id = 2
    
    mock_bid_a = Mock()
    mock_bid_a.user_id = 1 
    mock_bid_b = Mock()
    mock_bid_b.user_id = 2
    
    fake_db.query.return_value.filter.return_value.first.side_effect = [
        mock_match, mock_bid_a, mock_bid_b
    ]
    
    response = client.put("/api/v1/matches/1/reject")
    
    assert response.status_code == 200
    assert response.json()["message"] == "Match rejected successfully"
    assert mock_match.status == "rejected"
    assert mock_bid_a.status == "pending"
    assert mock_bid_b.status == "pending"


def test_reject_match_not_found(client, fake_db, override_db, override_auth):
    fake_db.query.return_value.filter.return_value.first.return_value = None
    
    response = client.put("/api/v1/matches/999/reject")
    
    assert response.status_code == 404
    assert response.json()["detail"] == "Match not found"


def test_debug_test_email_success(client, fake_db, override_db, override_auth):
    with patch('app.services.notification.email_service.send_match_notification') as mock_send:
        mock_send.return_value = True
        
        response = client.post("/api/v1/debug/test-email?user_email=test@example.com")
        
        assert response.status_code == 200
        body = response.json()
        assert body["success"] is True
        assert body["message"] == "Email sent successfully"


def test_debug_test_email_failure(client, fake_db, override_db, override_auth):
    with patch('app.services.notification.email_service.send_match_notification') as mock_send:
        mock_send.return_value = False
        
        response = client.post("/api/v1/debug/test-email?user_email=test@example.com")
        
        assert response.status_code == 200
        body = response.json()
        assert body["success"] is False
        assert body["message"] == "Email failed to send"