import pytest
import boto3
import json
import os
from moto import mock_aws
from unittest.mock import patch
import uuid
from datetime import datetime


@pytest.fixture(scope="session")
def aws_credentials():
    """Mocked AWS Credentials for moto."""
    os.environ["AWS_ACCESS_KEY_ID"] = "testing"
    os.environ["AWS_SECRET_ACCESS_KEY"] = "testing"
    os.environ["AWS_SECURITY_TOKEN"] = "testing"
    os.environ["AWS_SESSION_TOKEN"] = "testing"
    os.environ["AWS_DEFAULT_REGION"] = "eu-west-1"


@pytest.fixture(scope="function")
def mock_aws_services(aws_credentials):
    """Mock all AWS services used in the application."""
    with mock_aws():
        yield


@pytest.fixture
def dynamodb_client(mock_aws_services):
    """Create a mocked DynamoDB client."""
    return boto3.client("dynamodb", region_name="eu-west-1")


@pytest.fixture
def dynamodb_resource(mock_aws_services):
    """Create a mocked DynamoDB resource."""
    return boto3.resource("dynamodb", region_name="eu-west-1")


@pytest.fixture
def sqs_client(mock_aws_services):
    """Create a mocked SQS client."""
    return boto3.client("sqs", region_name="eu-west-1")


@pytest.fixture
def eventbridge_client(mock_aws_services):
    """Create a mocked EventBridge client."""
    return boto3.client("events", region_name="eu-west-1")


@pytest.fixture
def cognito_client(mock_aws_services):
    """Create a mocked Cognito client."""
    return boto3.client("cognito-idp", region_name="eu-west-1")


@pytest.fixture
def address_table(dynamodb_resource):
    """Create a mocked DynamoDB table for addresses."""
    table_name = "UserAddressesTable"
    table = dynamodb_resource.create_table(
        TableName=table_name,
        KeySchema=[
            {"AttributeName": "userId", "KeyType": "HASH"},
            {"AttributeName": "addressId", "KeyType": "RANGE"}
        ],
        AttributeDefinitions=[
            {"AttributeName": "userId", "AttributeType": "S"},
            {"AttributeName": "addressId", "AttributeType": "S"}
        ],
        BillingMode="PAY_PER_REQUEST"
    )
    table.wait_until_exists()
    return table


@pytest.fixture
def favorites_table(dynamodb_resource):
    """Create a mocked DynamoDB table for favorites."""
    table_name = "UserFavoritesTable"
    table = dynamodb_resource.create_table(
        TableName=table_name,
        KeySchema=[
            {"AttributeName": "userId", "KeyType": "HASH"},
            {"AttributeName": "favoriteId", "KeyType": "RANGE"}
        ],
        AttributeDefinitions=[
            {"AttributeName": "userId", "AttributeType": "S"},
            {"AttributeName": "favoriteId", "AttributeType": "S"}
        ],
        BillingMode="PAY_PER_REQUEST"
    )
    table.wait_until_exists()
    return table


@pytest.fixture
def favorites_queue(sqs_client):
    """Create a mocked SQS queue for favorites."""
    queue_name = "food-delivery-favorites-queue"
    response = sqs_client.create_queue(
        QueueName=queue_name,
        Attributes={
            "VisibilityTimeoutSeconds": "300",
            "MessageRetentionPeriod": "1209600",
            "ReceiveMessageWaitTimeSeconds": "20"
        }
    )
    return response["QueueUrl"]


@pytest.fixture
def event_bus(eventbridge_client):
    """Create a mocked EventBridge custom bus."""
    bus_name = "food-delivery-address-bus"
    eventbridge_client.create_event_bus(Name=bus_name)
    return bus_name


@pytest.fixture
def sample_user_id():
    """Generate a sample user ID for testing."""
    return str(uuid.uuid4())


@pytest.fixture
def sample_address_data():
    """Sample address data for testing."""
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
    """Sample favorite data for testing."""
    return {
        "type": "restaurant",
        "name": "Pizza Palace",
        "restaurantId": "rest_123",
        "description": "Best pizza in town",
        "imageUrl": "https://example.com/pizza.jpg"
    }


@pytest.fixture
def mock_cognito_claims(sample_user_id):
    """Mock Cognito JWT claims for authorization."""
    return {
        "sub": sample_user_id,
        "email": "test@example.com",
        "cognito:username": "testuser"
    }


@pytest.fixture
def api_gateway_event():
    """Base API Gateway event structure."""
    def _create_event(http_method, path, body=None, path_parameters=None, query_parameters=None, claims=None):
        event = {
            "httpMethod": http_method,
            "path": path,
            "resource": path,
            "requestContext": {
                "requestId": str(uuid.uuid4()),
                "stage": "test",
                "resourcePath": path,
                "httpMethod": http_method,
                "authorizer": {
                    "claims": claims or {}
                }
            },
            "headers": {
                "Content-Type": "application/json",
                "Authorization": "Bearer mock-jwt-token"
            },
            "multiValueHeaders": {},
            "queryStringParameters": query_parameters,
            "multiValueQueryStringParameters": {},
            "pathParameters": path_parameters,
            "stageVariables": {},
            "body": json.dumps(body) if body else None,
            "isBase64Encoded": False
        }
        return event
    return _create_event


@pytest.fixture
def lambda_context():
    """Mock Lambda context."""
    class MockContext:
        def __init__(self):
            self.function_name = "test-function"
            self.function_version = "$LATEST"
            self.invoked_function_arn = "arn:aws:lambda:us-east-1:123456789012:function:test-function"
            self.memory_limit_in_mb = 128
            self.remaining_time_in_millis = lambda: 30000
            self.log_group_name = "/aws/lambda/test-function"
            self.log_stream_name = "2023/01/01/[$LATEST]test"
            self.aws_request_id = str(uuid.uuid4())
    
    return MockContext()


@pytest.fixture
def mock_environment_variables():
    """Mock environment variables for Lambda functions."""
    env_vars = {
        "TABLE_NAME": "UserFavoritesTable", 
        "ADDRESS_TABLE_NAME": "UserAddressesTable", 
        "QUEUE_URL": "https://sqs.us-east-1.amazonaws.com/123456789012/food-delivery-favorites-queue",
        "EVENT_BUS_NAME": "food-delivery-address-bus",
        "POWERTOOLS_SERVICE_NAME": "test-service"
    }
    
    with patch.dict(os.environ, env_vars):
        yield env_vars


@pytest.fixture
def sqs_event():
    """Create a sample SQS event for testing."""
    def _create_sqs_event(messages):
        records = []
        for message in messages:
            records.append({
                "messageId": str(uuid.uuid4()),
                "receiptHandle": "mock-receipt-handle",
                "body": json.dumps(message),
                "attributes": {
                    "ApproximateReceiveCount": "1",
                    "SentTimestamp": str(int(datetime.utcnow().timestamp() * 1000)),
                    "SenderId": "AIDAIENQZJOLO23YVJ4VO",
                    "ApproximateFirstReceiveTimestamp": str(int(datetime.utcnow().timestamp() * 1000))
                },
                "messageAttributes": {},
                "md5OfBody": "mock-md5",
                "eventSource": "aws:sqs",
                "eventSourceARN": "arn:aws:sqs:us-east-1:123456789012:food-delivery-favorites-queue",
                "awsRegion": "us-east-1"
            })
        
        return {"Records": records}
    
    return _create_sqs_event


@pytest.fixture
def eventbridge_event():
    """Create a sample EventBridge event for testing."""
    def _create_eventbridge_event(source, detail_type, detail):
        return {
            "version": "0",
            "id": str(uuid.uuid4()),
            "detail-type": detail_type,
            "source": source,
            "account": "123456789012",
            "time": datetime.utcnow().isoformat(),
            "region": "eu-west-1",
            "detail": detail
        }
    
    return _create_eventbridge_event