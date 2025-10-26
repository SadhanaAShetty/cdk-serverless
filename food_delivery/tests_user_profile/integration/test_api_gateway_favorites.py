import pytest
import json
import uuid
from datetime import datetime


class TestFavoritesAPI:
    """Test suite for Favorites API Gateway integration."""

    @pytest.fixture(autouse=True)
    def setup(self, mock_environment_variables, favorites_table, favorites_queue):
        """Setup test environment."""
        self.table = favorites_table
        self.queue_url = favorites_queue

    def test_list_favorites_success(self, api_gateway_event, lambda_context, mock_cognito_claims):
        from address_assets.favorites.list_user_favorites import lambda_handler
        
        
        user_id = mock_cognito_claims["sub"]
        test_favorites = [
            {
                "userId": user_id,
                "favoriteId": str(uuid.uuid4()),
                "type": "restaurant",
                "name": "Pizza Palace",
                "restaurantId": "rest_123",
                "createdAt": "2024-01-01T00:00:00Z"
            },
            {
                "userId": user_id,
                "favoriteId": str(uuid.uuid4()),
                "type": "dish",
                "name": "Margherita Pizza",
                "restaurantId": "rest_123",
                "dishId": "dish_456",
                "createdAt": "2024-01-02T00:00:00Z"
            }
        ]
        
        for favorite in test_favorites:
            self.table.put_item(Item=favorite)
        
        event = api_gateway_event(
            http_method="GET",
            path="/favorites",
            claims=mock_cognito_claims
        )
        
        response = lambda_handler(event, lambda_context)
        
        assert response["statusCode"] == 200
        body = json.loads(response["body"])
        assert "favorites" in body
        assert "count" in body
        assert len(body["favorites"]) == 2
        assert body["count"] == 2
        assert body["favorites"][0]["createdAt"] == "2024-01-02T00:00:00Z"

    def test_list_favorites_empty(self, api_gateway_event, lambda_context, mock_cognito_claims):
        """Test listing favorites when user has none."""
        from address_assets.favorites.list_user_favorites import lambda_handler
        
        event = api_gateway_event(
            http_method="GET",
            path="/favorites",
            claims=mock_cognito_claims
        )
        
        response = lambda_handler(event, lambda_context)
        
        assert response["statusCode"] == 200
        body = json.loads(response["body"])
        assert "favorites" in body
        assert body["favorites"] == []
        assert body["count"] == 0

    def test_list_favorites_unauthorized(self, api_gateway_event, lambda_context):
        """Test listing favorites without authorization."""
        from address_assets.favorites.list_user_favorites import lambda_handler
        
       
        event = api_gateway_event(
            http_method="GET",
            path="/favorites",
            claims=None  
        )
        
        response = lambda_handler(event, lambda_context)
        
        assert response["statusCode"] == 401
        body = json.loads(response["body"])
        assert body["error"] == "Unauthorized"


class TestFavoritesQueueProcessor:
    """Test suite for Favorites SQS Queue Processor."""

    @pytest.fixture(autouse=True)
    def setup(self, mock_environment_variables, favorites_table):
        """Setup test environment."""
        self.table = favorites_table

    def test_process_add_favorite_message(self, sqs_event, lambda_context, sample_user_id):
        """Test processing ADD favorite message from SQS."""
        from address_assets.favorites.process_favorites_queue import lambda_handler
        
        favorite_id = str(uuid.uuid4())
        add_message = {
            "userId": sample_user_id,
            "action": "ADD",
            "favoriteData": {
                "favoriteId": favorite_id,
                "type": "restaurant",
                "name": "Pizza Palace",
                "restaurantId": "rest_123",
                "description": "Best pizza in town"
            },
            "timestamp": datetime.utcnow().isoformat()
        }
        
        event = sqs_event([add_message])
        
        response = lambda_handler(event, lambda_context)
        
     
        assert "batchItemFailures" in response
        assert len(response["batchItemFailures"]) == 0
        
        # Verify the favorite was added to DynamoDB
        db_response = self.table.get_item(
            Key={
                "userId": sample_user_id,
                "favoriteId": favorite_id
            }
        )
        assert "Item" in db_response
        item = db_response["Item"]
        assert item["type"] == "restaurant"
        assert item["name"] == "Pizza Palace"
        assert item["restaurantId"] == "rest_123"

    def test_process_remove_favorite_message(self, sqs_event, lambda_context, sample_user_id):
        """Test processing REMOVE favorite message from SQS."""
        from address_assets.favorites.process_favorites_queue import lambda_handler
        
        # First add a favorite to remove
        favorite_id = str(uuid.uuid4())
        existing_favorite = {
            "userId": sample_user_id,
            "favoriteId": favorite_id,
            "type": "restaurant",
            "name": "Pizza Palace",
            "restaurantId": "rest_123",
            "createdAt": datetime.utcnow().isoformat()
        }
        self.table.put_item(Item=existing_favorite)
        
        # Create remove message
        remove_message = {
            "userId": sample_user_id,
            "action": "REMOVE",
            "favoriteId": favorite_id,
            "timestamp": datetime.utcnow().isoformat()
        }
        
        event = sqs_event([remove_message])
        
        response = lambda_handler(event, lambda_context)
        
        # Check that the function processed successfully
        assert "batchItemFailures" in response
        assert len(response["batchItemFailures"]) == 0
        
        # Verify the favorite was removed from DynamoDB
        db_response = self.table.get_item(
            Key={
                "userId": sample_user_id,
                "favoriteId": favorite_id
            }
        )
        assert "Item" not in db_response

    def test_process_add_dish_favorite_message(self, sqs_event, lambda_context, sample_user_id):
        """Test processing ADD dish favorite message from SQS."""
        from address_assets.favorites.process_favorites_queue import lambda_handler
        
        favorite_id = str(uuid.uuid4())
        add_message = {
            "userId": sample_user_id,
            "action": "ADD",
            "favoriteData": {
                "favoriteId": favorite_id,
                "type": "dish",
                "name": "Margherita Pizza",
                "restaurantId": "rest_123",
                "dishId": "dish_456",
                "description": "Classic margherita pizza",
                "imageUrl": "https://example.com/pizza.jpg"
            },
            "timestamp": datetime.utcnow().isoformat()
        }
        
        event = sqs_event([add_message])
        
        response = lambda_handler(event, lambda_context)
        
        # Check that the function processed successfully
        assert "batchItemFailures" in response
        assert len(response["batchItemFailures"]) == 0
        
        # Verify the dish favorite was added to DynamoDB
        db_response = self.table.get_item(
            Key={
                "userId": sample_user_id,
                "favoriteId": favorite_id
            }
        )
        assert "Item" in db_response
        item = db_response["Item"]
        assert item["type"] == "dish"
        assert item["name"] == "Margherita Pizza"
        assert item["dishId"] == "dish_456"
        assert item["imageUrl"] == "https://example.com/pizza.jpg"

    def test_process_invalid_message_missing_user_id(self, sqs_event, lambda_context):
        """Test processing message with missing userId."""
        from address_assets.favorites.process_favorites_queue import lambda_handler
        from aws_lambda_powertools.utilities.batch.exceptions import BatchProcessingError
        
        invalid_message = {
            "action": "ADD",
            "favoriteData": {
                "favoriteId": str(uuid.uuid4()),
                "type": "restaurant",
                "name": "Pizza Palace"
            }
            
        }
        
        event = sqs_event([invalid_message])
        
        # The batch processor should raise BatchProcessingError for invalid messages
        with pytest.raises(BatchProcessingError):
            lambda_handler(event, lambda_context)

    def test_process_invalid_action(self, sqs_event, lambda_context, sample_user_id):
        """Test processing message with invalid action."""
        from address_assets.favorites.process_favorites_queue import lambda_handler
        from aws_lambda_powertools.utilities.batch.exceptions import BatchProcessingError
        
        invalid_message = {
            "userId": sample_user_id,
            "action": "INVALID_ACTION",
            "favoriteData": {
                "favoriteId": str(uuid.uuid4()),
                "type": "restaurant",
                "name": "Pizza Palace"
            }
        }
        
        event = sqs_event([invalid_message])
        
        # The batch processor should raise BatchProcessingError for invalid messages
        with pytest.raises(BatchProcessingError):
            lambda_handler(event, lambda_context)