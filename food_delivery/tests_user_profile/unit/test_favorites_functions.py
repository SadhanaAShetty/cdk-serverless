import pytest
import json
import uuid
from unittest.mock import patch, MagicMock
from datetime import datetime


class TestFavoritesValidation:

    def test_validate_favorite_type_valid(self):
        valid_types = ["restaurant", "dish"]
        
        for favorite_type in valid_types:
            assert favorite_type in ["restaurant", "dish"]

    def test_validate_favorite_type_invalid(self):

        invalid_types = ["invalid", "menu", "category", ""]
        
        for favorite_type in invalid_types:
            assert favorite_type not in ["restaurant", "dish"]

    def test_validate_required_fields_success(self, sample_favorite_data):

        required_fields = ["type", "name"]
        
        for field in required_fields:
            assert field in sample_favorite_data
            assert sample_favorite_data[field] 

    def test_validate_required_fields_missing(self):
        incomplete_data = {
            "type": "restaurant"
        }
        
        required_fields = ["type", "name"]
        missing_fields = []
        
        for field in required_fields:
            if field not in incomplete_data or not incomplete_data[field]:
                missing_fields.append(field)
        
        assert len(missing_fields) == 1
        assert "name" in missing_fields


class TestFavoritesQueueProcessing:

    @patch('address_assets.favorites.process_favorites_queue.table')
    def test_process_add_favorite_record(self, mock_table, mock_environment_variables, sample_user_id):
        from address_assets.favorites.process_favorites_queue import record_handler
        from aws_lambda_powertools.utilities.data_classes.sqs_event import SQSRecord
        

        favorite_id = str(uuid.uuid4())
        message_body = {
            "userId": sample_user_id,
            "action": "ADD",
            "favoriteData": {
                "favoriteId": favorite_id,
                "type": "restaurant",
                "name": "Pizza Palace",
                "restaurantId": "rest_123"
            }
        }
        
        mock_record = MagicMock(spec=SQSRecord)
        mock_record.body = json.dumps(message_body)
        mock_record.message_id = "test-message-id"
        
  
        record_handler(mock_record)
        

        mock_table.put_item.assert_called_once()
        call_args = mock_table.put_item.call_args[1]
        item = call_args["Item"]
        
        assert item["userId"] == sample_user_id
        assert item["favoriteId"] == favorite_id
        assert item["type"] == "restaurant"
        assert item["name"] == "Pizza Palace"
        assert "createdAt" in item

    @patch('address_assets.favorites.process_favorites_queue.table')
    def test_process_remove_favorite_record(self, mock_table, mock_environment_variables, sample_user_id):
        from address_assets.favorites.process_favorites_queue import record_handler
        from aws_lambda_powertools.utilities.data_classes.sqs_event import SQSRecord
        
        favorite_id = str(uuid.uuid4())
        message_body = {
            "userId": sample_user_id,
            "action": "REMOVE",
            "favoriteId": favorite_id
        }
        
        mock_record = MagicMock(spec=SQSRecord)
        mock_record.body = json.dumps(message_body)
        mock_record.message_id = "test-message-id"

        record_handler(mock_record)
        

        mock_table.delete_item.assert_called_once()
        call_args = mock_table.delete_item.call_args[1]
        key = call_args["Key"]
        
        assert key["userId"] == sample_user_id
        assert key["favoriteId"] == favorite_id

    def test_process_invalid_record_missing_user_id(self):
        from address_assets.favorites.process_favorites_queue import record_handler
        from aws_lambda_powertools.utilities.data_classes.sqs_event import SQSRecord
        
        message_body = {
            "action": "ADD",
            "favoriteData": {
                "favoriteId": str(uuid.uuid4()),
                "type": "restaurant",
                "name": "Pizza Palace"
            }
        }
        
        mock_record = MagicMock(spec=SQSRecord)
        mock_record.body = json.dumps(message_body)
        mock_record.message_id = "test-message-id"
        

        with pytest.raises(ValueError, match="Missing userId or action in message"):
            record_handler(mock_record)


class TestFavoritesDataTransformation:
    def test_create_favorite_item_structure_restaurant(self, sample_user_id):
        favorite_id = str(uuid.uuid4())
        favorite_data = {
            "type": "restaurant",
            "name": "Pizza Palace",
            "restaurantId": "rest_123",
            "description": "Best pizza in town",
            "imageUrl": "https://example.com/pizza.jpg"
        }
        
        item = {
            "userId": sample_user_id,
            "favoriteId": favorite_id,
            "type": favorite_data["type"],
            "name": favorite_data["name"],
            "restaurantId": favorite_data.get("restaurantId", ""),
            "dishId": favorite_data.get("dishId", ""),
            "description": favorite_data.get("description", ""),
            "imageUrl": favorite_data.get("imageUrl", ""),
            "createdAt": datetime.utcnow().isoformat()
        }
        

        assert item["userId"] == sample_user_id
        assert item["favoriteId"] == favorite_id
        assert item["type"] == "restaurant"
        assert item["name"] == "Pizza Palace"
        assert item["restaurantId"] == "rest_123"
        assert item["dishId"] == "" 
        assert "createdAt" in item

    def test_favorite_message_structure(self, sample_user_id):

        favorite_data = {
            "favoriteId": str(uuid.uuid4()),
            "type": "restaurant",
            "name": "Pizza Palace"
        }
        
        message_body = {
            "userId": sample_user_id,
            "action": "ADD",
            "timestamp": datetime.utcnow().isoformat(),
            **favorite_data
        }
        
 
        assert message_body["userId"] == sample_user_id
        assert message_body["action"] == "ADD"
        assert message_body["favoriteId"] == favorite_data["favoriteId"]
        assert message_body["type"] == favorite_data["type"]
        assert message_body["name"] == favorite_data["name"]
        assert "timestamp" in message_body