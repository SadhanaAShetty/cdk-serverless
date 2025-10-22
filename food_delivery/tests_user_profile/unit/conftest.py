import pytest
import os
from unittest.mock import patch, MagicMock
import uuid


@pytest.fixture
def mock_environment_variables():
    env_vars = {
        "TABLE_NAME": "UserAddressesTable",
        "FAVORITES_TABLE_NAME": "UserFavoritesTable",
        "QUEUE_URL": "https://sqs.eu-west-1.amazonaws.com/123456789012/food-delivery-favorites-queue",
        "EVENT_BUS_NAME": "food-delivery-address-bus",
        "POWERTOOLS_SERVICE_NAME": "test-service"
    }
    
    with patch.dict(os.environ, env_vars):
        yield env_vars


@pytest.fixture
def mock_dynamodb_table():
    table = MagicMock()
    table.put_item.return_value = {}
    table.get_item.return_value = {"Item": {}}
    table.query.return_value = {"Items": []}
    table.update_item.return_value = {"Attributes": {}}
    table.delete_item.return_value = {}
    return table


@pytest.fixture
def mock_sqs_client():
    client = MagicMock()
    client.send_message.return_value = {"MessageId": str(uuid.uuid4())}
    return client


@pytest.fixture
def mock_eventbridge_client():
    client = MagicMock()
    client.put_events.return_value = {"Entries": [{"EventId": str(uuid.uuid4())}]}
    return client


@pytest.fixture
def sample_user_id():
    return str(uuid.uuid4())


@pytest.fixture
def sample_address_data():
    return {
        "addressLine1": "123 Main Street",
        "addressLine2": "Apt 4B",
        "city": "New York",
        "state": "NY",
        "zipCode": "10001",
        "country": "USA",
        "isDefault": True,
        "label": "Home"
    }


@pytest.fixture
def sample_favorite_data():
    return {
        "type": "restaurant",
        "name": "Pizza Palace",
        "restaurantId": "rest_123",
        "description": "Best pizza in town",
        "imageUrl": "https://example.com/pizza.jpg"
    }


@pytest.fixture
def lambda_context():
    class MockContext:
        def __init__(self):
            self.function_name = "test-function"
            self.function_version = "$LATEST"
            self.invoked_function_arn = "arn:aws:lambda:eu-west-1:123456789012:function:test-function"
            self.memory_limit_in_mb = 128
            self.remaining_time_in_millis = lambda: 30000
            self.log_group_name = "/aws/lambda/test-function"
            self.log_stream_name = "2023/01/01/[$LATEST]test"
            self.aws_request_id = str(uuid.uuid4())
    
    return MockContext()