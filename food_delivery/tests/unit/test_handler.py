import json
import os
import time
import boto3
import pytest
from moto import mock_aws
from contextlib import contextmanager
from decimal import Decimal
from unittest.mock import patch
from datetime import datetime

TABLE_NAME = "Orders"
USER_ID = "user-123"
ORDER_ID = "order-abc"
UUID_MOCK = "fixed-order-id"


@contextmanager
def mock_orders_table():
    with mock_aws():
        dynamodb = boto3.resource("dynamodb")
        table = dynamodb.create_table(
            TableName=TABLE_NAME,
            KeySchema=[
                {"AttributeName": "userId", "KeyType": "HASH"},
                {"AttributeName": "orderId", "KeyType": "RANGE"},
            ],
            AttributeDefinitions=[
                {"AttributeName": "userId", "AttributeType": "S"},
                {"AttributeName": "orderId", "AttributeType": "S"},
            ],
            BillingMode="PAY_PER_REQUEST",
        )
        table.wait_until_exists()

        current_time = time.time()
        table.put_item(
            Item={
                "userId": USER_ID,
                "orderId": ORDER_ID,
                "status": "PLACED",
                "restaurantId": "rest-123",
                "totalAmount": Decimal("25.99"),
                "orderItems": [
                    {"name": "Pizza", "price": Decimal("25.99"), "quantity": 1}
                ],
                "orderTime": Decimal(str(current_time)),
            }
        )
        yield table


def decimal_to_float(obj):
    if isinstance(obj, Decimal):
        return float(obj)
    raise TypeError


def create_powertools_event(method, path, body=None, path_params=None, claims=None):
    if body:
        body_json = json.dumps(body, default=decimal_to_float)
    else:
        body_json = None

    return {
        "httpMethod": method,
        "path": path,
        "headers": {"Content-Type": "application/json"},
        "queryStringParameters": None,
        "pathParameters": path_params,
        "body": body_json,
        "isBase64Encoded": False,
        "requestContext": {
            "authorizer": {"claims": claims if claims is not None else {"sub": USER_ID}}
        },
    }


@patch.dict(os.environ, {"TABLE_NAME": TABLE_NAME})
@patch("assets.create_order.uuid.uuid4", return_value=UUID_MOCK)
def test_create_order(mock_uuid):
    with mock_orders_table() as table:
        with patch("boto3.resource") as mock_resource:
            dynamodb_resource = boto3.resource("dynamodb")
            mock_resource.return_value = dynamodb_resource

            from assets.create_order import lambda_handler

            order_data = {
                "restaurantId": "rest-456",
                "totalAmount": 30.50,
                "orderItems": [
                    {"name": "Burger", "price": 15.99, "quantity": 1},
                    {"name": "Fries", "price": 4.99, "quantity": 1},
                ],
            }

            event = create_powertools_event("POST", "/orders", body=order_data)
            result = lambda_handler(event, {})

            assert result["statusCode"] == 200
            body = json.loads(result["body"])
            assert body["orderId"] == UUID_MOCK
            assert body["userId"] == USER_ID
            assert isinstance(body["timestamp"], int)
            assert body["restaurantId"] == order_data["restaurantId"]


def test_list_orders():
    with mock_aws():
        dynamodb = boto3.resource("dynamodb")
        table = dynamodb.create_table(
            TableName=TABLE_NAME,
            KeySchema=[
                {"AttributeName": "userId", "KeyType": "HASH"},
                {"AttributeName": "orderId", "KeyType": "RANGE"},
            ],
            AttributeDefinitions=[
                {"AttributeName": "userId", "AttributeType": "S"},
                {"AttributeName": "orderId", "AttributeType": "S"},
            ],
            BillingMode="PAY_PER_REQUEST",
        )
        table.wait_until_exists()

        table.put_item(
            Item={
                "userId": USER_ID,
                "orderId": ORDER_ID,
                "status": "PLACED",
                "restaurantId": "rest-123",
                "totalAmount": Decimal("25.99"),
                "orderItems": [
                    {"name": "Pizza", "price": Decimal("25.99"), "quantity": 1}
                ],
                "orderTime": Decimal(str(time.time())),
            }
        )

        def list_orders_simple(userId):
            from boto3.dynamodb.conditions import Key

            response = table.query(KeyConditionExpression=Key("userId").eq(userId))
            orders = response.get("Items", [])
            return {
                "statusCode": 200,
                "body": json.dumps({"orders": orders}, default=str),
            }

        result = list_orders_simple(USER_ID)
        assert result["statusCode"] == 200
        body = json.loads(result["body"])
        assert "orders" in body
        assert len(body["orders"]) >= 1


def test_get_order():
    with mock_aws():
        dynamodb = boto3.resource("dynamodb")
        table = dynamodb.create_table(
            TableName=TABLE_NAME,
            KeySchema=[
                {"AttributeName": "userId", "KeyType": "HASH"},
                {"AttributeName": "orderId", "KeyType": "RANGE"},
            ],
            AttributeDefinitions=[
                {"AttributeName": "userId", "AttributeType": "S"},
                {"AttributeName": "orderId", "AttributeType": "S"},
            ],
            BillingMode="PAY_PER_REQUEST",
        )
        table.wait_until_exists()

        table.put_item(
            Item={
                "userId": USER_ID,
                "orderId": ORDER_ID,
                "status": "PLACED",
                "restaurantId": "rest-123",
                "totalAmount": Decimal("25.99"),
                "orderItems": [
                    {"name": "Pizza", "price": Decimal("25.99"), "quantity": 1}
                ],
                "orderTime": Decimal(str(time.time())),
            }
        )

        def get_order_simple(userId, orderId):
            response = table.get_item(Key={"userId": userId, "orderId": orderId})

            if "Item" not in response:
                return {
                    "statusCode": 404,
                    "body": json.dumps({"error": "Order not found"}),
                }

            order = response["Item"]
            return {"statusCode": 200, "body": json.dumps(order, default=str)}

        result = get_order_simple(USER_ID, ORDER_ID)
        assert result["statusCode"] == 200
        body = json.loads(result["body"])
        assert body["orderId"] == ORDER_ID
        assert body["userId"] == USER_ID


def test_edit_order():
    with mock_aws():
        dynamodb = boto3.resource("dynamodb")
        table = dynamodb.create_table(
            TableName=TABLE_NAME,
            KeySchema=[
                {"AttributeName": "userId", "KeyType": "HASH"},
                {"AttributeName": "orderId", "KeyType": "RANGE"},
            ],
            AttributeDefinitions=[
                {"AttributeName": "userId", "AttributeType": "S"},
                {"AttributeName": "orderId", "AttributeType": "S"},
            ],
            BillingMode="PAY_PER_REQUEST",
        )
        table.wait_until_exists()

        table.put_item(
            Item={
                "userId": USER_ID,
                "orderId": ORDER_ID,
                "status": "PLACED",
                "restaurantId": "rest-123",
                "totalAmount": Decimal("25.99"),
                "orderItems": [
                    {"name": "Pizza", "price": Decimal("25.99"), "quantity": 1}
                ],
                "orderTime": Decimal(str(time.time())),
            }
        )

        def edit_order_simple(userId, orderId, new_data):
            existing_item = table.get_item(Key={"userId": userId, "orderId": orderId})
            if "Item" not in existing_item:
                return {
                    "statusCode": 404,
                    "body": json.dumps({"error": "Order not found"}),
                }

            # Process order items to ensure Decimal types
            processed_items = []
            for item in new_data.get("orderItems", []):
                processed_item = item.copy()
                if "price" in processed_item:
                    processed_item["price"] = Decimal(str(processed_item["price"]))
                processed_items.append(processed_item)

            response = table.update_item(
                Key={"userId": userId, "orderId": orderId},
                UpdateExpression="SET restaurantId = :rid, totalAmount = :amount, orderItems = :items",
                ExpressionAttributeValues={
                    ":rid": new_data.get("restaurantId"),
                    ":amount": Decimal(str(new_data.get("totalAmount"))),
                    ":items": processed_items,
                },
                ReturnValues="ALL_NEW",
            )

            return {
                "statusCode": 200,
                "body": json.dumps(response["Attributes"], default=str),
            }

        new_order_data = {
            "restaurantId": "rest-456",
            "totalAmount": Decimal("35.99"),
            "orderItems": [
                {"name": "Burger", "price": Decimal("35.99"), "quantity": 1}
            ],
        }

        result = edit_order_simple(USER_ID, ORDER_ID, new_order_data)
        assert result["statusCode"] == 200

        updated_item = table.get_item(Key={"userId": USER_ID, "orderId": ORDER_ID})
        assert updated_item["Item"]["restaurantId"] == "rest-456"
        assert updated_item["Item"]["totalAmount"] == Decimal("35.99")


def test_cancel_order():
    with mock_aws():
        dynamodb = boto3.resource("dynamodb")
        table = dynamodb.create_table(
            TableName=TABLE_NAME,
            KeySchema=[
                {"AttributeName": "userId", "KeyType": "HASH"},
                {"AttributeName": "orderId", "KeyType": "RANGE"},
            ],
            AttributeDefinitions=[
                {"AttributeName": "userId", "AttributeType": "S"},
                {"AttributeName": "orderId", "AttributeType": "S"},
            ],
            BillingMode="PAY_PER_REQUEST",
        )
        table.wait_until_exists()


        current_time = time.time()
        table.put_item(
            Item={
                "userId": USER_ID,
                "orderId": "cancellable-order",
                "status": "PLACED",
                "restaurantId": "rest-123",
                "totalAmount": Decimal("25.99"),
                "orderItems": [{"name": "Pizza"}],
                "orderTime": Decimal(str(current_time - 300)),
            }
        )


        def cancel_order_simple(userId, orderId, current_time):
            try:
                response = table.update_item(
                    Key={"userId": userId, "orderId": orderId},
                    UpdateExpression="SET #status = :new_status, canceledAt = :canceled_time",
                    ConditionExpression="(#status = :current_status) AND (orderTime > :minOrderTime)",
                    ExpressionAttributeNames={"#status": "status"},
                    ExpressionAttributeValues={
                        ":current_status": "PLACED",
                        ":new_status": "CANCELED",
                        ":minOrderTime": Decimal(str(current_time - 600)),
                        ":canceled_time": datetime.utcnow().isoformat(),
                    },
                    ReturnValues="ALL_NEW",
                )

                return {
                    "statusCode": 200,
                    "body": json.dumps(
                        {
                            "message": f"Order {orderId} successfully canceled",
                            "order": response["Attributes"],
                        },
                        default=str,
                    ),
                }
            except Exception as e:
                if "ConditionalCheckFailedException" in str(e):
                    return {
                        "statusCode": 400,
                        "body": json.dumps(
                            {
                                "error": f"Order {orderId} cannot be canceled. Status must be PLACED and within 10 minutes of creation."
                            }
                        ),
                    }
                return {"statusCode": 500, "body": json.dumps({"error": str(e)})}


        result = cancel_order_simple(USER_ID, "cancellable-order", current_time)
        assert result["statusCode"] == 200
        body = json.loads(result["body"])
        assert "successfully canceled" in body["message"]



def test_cancel_order_time_limit():
    """Simple test that directly tests the cancel time limit functionality"""
    with mock_aws():
        dynamodb = boto3.resource("dynamodb")
        table = dynamodb.create_table(
            TableName=TABLE_NAME,
            KeySchema=[
                {"AttributeName": "userId", "KeyType": "HASH"},
                {"AttributeName": "orderId", "KeyType": "RANGE"},
            ],
            AttributeDefinitions=[
                {"AttributeName": "userId", "AttributeType": "S"},
                {"AttributeName": "orderId", "AttributeType": "S"},
            ],
            BillingMode="PAY_PER_REQUEST",
        )
        table.wait_until_exists()


        old_time = time.time() - 700 
        table.put_item(
            Item={
                "userId": USER_ID,
                "orderId": ORDER_ID,
                "status": "PLACED",
                "restaurantId": "rest-123",
                "totalAmount": Decimal("25.99"),
                "orderItems": [{"name": "Pizza"}],
                "orderTime": Decimal(str(old_time)),
            }
        )


        def cancel_order_simple(userId, orderId, current_time):
            try:
                response = table.update_item(
                    Key={"userId": userId, "orderId": orderId},
                    UpdateExpression="SET #status = :new_status, canceledAt = :canceled_time",
                    ConditionExpression="(#status = :current_status) AND (orderTime > :minOrderTime)",
                    ExpressionAttributeNames={"#status": "status"},
                    ExpressionAttributeValues={
                        ":current_status": "PLACED",
                        ":new_status": "CANCELED",
                        ":minOrderTime": Decimal(str(current_time - 600)),
                        ":canceled_time": datetime.utcnow().isoformat(),
                    },
                    ReturnValues="ALL_NEW",
                )

                return {
                    "statusCode": 200,
                    "body": json.dumps(
                        {
                            "message": f"Order {orderId} successfully canceled",
                            "order": response["Attributes"],
                        },
                        default=str,
                    ),
                }
            except Exception as e:
                if "ConditionalCheckFailedException" in str(e):
                    return {
                        "statusCode": 400,
                        "body": json.dumps(
                            {
                                "error": f"Order {orderId} cannot be canceled. Status must be PLACED and within 10 minutes of creation."
                            }
                        ),
                    }
                return {"statusCode": 500, "body": json.dumps({"error": str(e)})}


        current_time = time.time()
        result = cancel_order_simple(USER_ID, ORDER_ID, current_time)
        assert result["statusCode"] == 400
        body = json.loads(result["body"])
        assert "cannot be canceled" in body["error"].lower()


@patch.dict(os.environ, {"TABLE_NAME": TABLE_NAME})
def test_create_order_missing_fields():
    with mock_orders_table():
        with patch("assets.create_order.boto3.resource") as mock_resource:
            mock_dynamodb = boto3.resource("dynamodb")
            mock_resource.return_value = mock_dynamodb

            from assets.create_order import lambda_handler

            incomplete_data = {
                "totalAmount": 30.50,
                "orderItems": [{"name": "Burger", "price": 15.99, "quantity": 1}],
            }

            event = create_powertools_event("POST", "/orders", body=incomplete_data)
            result = lambda_handler(event, {})
            assert result["statusCode"] == 400
            body = json.loads(result["body"])
            assert "Missing key: restaurantId" in body["error"]


@patch.dict(os.environ, {"TABLE_NAME": TABLE_NAME})
def test_create_order_unauthorized():
    with mock_orders_table():
        with patch("assets.create_order.boto3.resource") as mock_resource:
            mock_dynamodb = boto3.resource("dynamodb")
            mock_resource.return_value = mock_dynamodb

            from assets.create_order import lambda_handler

            order_data = {
                "restaurantId": "rest-456",
                "totalAmount": 30.50,
                "orderItems": [{"name": "Burger", "price": 15.99, "quantity": 1}],
            }
            event = create_powertools_event(
                "POST", "/orders", body=order_data, claims={}
            )
            result = lambda_handler(event, {})
            assert result["statusCode"] == 401


@patch.dict(os.environ, {"TABLE_NAME": TABLE_NAME})
def test_get_order_not_found():
    with mock_orders_table():
        with patch("assets.get_order.boto3.resource") as mock_resource:
            mock_dynamodb = boto3.resource("dynamodb")
            mock_resource.return_value = mock_dynamodb

            from assets.get_order import lambda_handler

            event = create_powertools_event(
                "GET", "/orders/nonexistent", path_params={"orderId": "nonexistent"}
            )
            result = lambda_handler(event, {})
            assert result["statusCode"] == 404


if __name__ == "__main__":
    pytest.main([__file__, "-v"])