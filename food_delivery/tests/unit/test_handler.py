import json
import os
import time
import boto3
import pytest
from moto import mock_dynamodb
from contextlib import contextmanager
from decimal import Decimal
from unittest.mock import patch, Mock

TABLE_NAME = "Orders"
USER_ID = "user-123"
ORDER_ID = "order-abc"


@contextmanager
def mock_orders_table():
    with mock_dynamodb():
        dynamodb = boto3.client("dynamodb")
        
        dynamodb.create_table(
            TableName=TABLE_NAME,
            KeySchema=[
                {"AttributeName": "userId", "KeyType": "HASH"}, 
                {"AttributeName": "orderId", "KeyType": "RANGE"},  
            ],
            AttributeDefinitions=[
                {"AttributeName": "userId", "AttributeType": "S"},   
                {"AttributeName": "orderId", "AttributeType": "S"},  
            ],
            BillingMode="PAY_PER_REQUEST"  
        )


        current_time = int(time.time())
        dynamodb.put_item(
            TableName=TABLE_NAME,
            Item={
                "userId": {"S": USER_ID},     
                "orderId": {"S": ORDER_ID},   
                "data": {
                    "M": {
                        "userId": {"S": USER_ID},
                        "orderId": {"S": ORDER_ID},
                        "status": {"S": "PLACED"},
                        "restaurantId": {"S": "rest-123"},
                        "totalAmount": {"N": "25.99"},
                        "orderItems": {"L": [{"M": {"name": {"S": "Pizza"}}}]},
                        "orderTime": {"S": str(current_time)}
                    }
                }
            },
        )
        yield


def create_powertools_event(method, path, body=None, path_params=None):
    return {
        "httpMethod": method,
        "path": path,
        "resource": path,
        "pathParameters": path_params or {},
        "body": json.dumps(body) if body else None,
        "headers": {"Content-Type": "application/json"},
        "requestContext": {
            "authorizer": {
                "claims": {"sub": USER_ID}
            },
            "httpMethod": method,
            "resourcePath": path
        },
        "isBase64Encoded": False
    }


@patch.dict(os.environ, {"TABLE_NAME": TABLE_NAME})
def test_create_order():
    with mock_orders_table():
        from assets.create_order import lambda_handler
        
        order_data = {
            "restaurantId": "rest-456",
            "totalAmount": 30.50,
            "orderItems": [
                {"name": "Burger", "price": 15.99, "quantity": 1},
                {"name": "Fries", "price": 4.99, "quantity": 1}
            ]
        }
        
        event = create_powertools_event(
            method="POST",
            path=f"/orders/{USER_ID}",
            body=order_data
        )
        
        result = lambda_handler(event, {})
        
       
        assert result["statusCode"] == 201 
        body = json.loads(result["body"])
        assert "orderId" in body 
        assert "userId" in body   


@patch.dict(os.environ, {"TABLE_NAME": TABLE_NAME})
def test_list_orders():
    with mock_orders_table():
        from assets.list_order import lambda_handler

        event = create_powertools_event(
            method="GET",
            path="/orders"
        )

        result = lambda_handler(event, {})
        assert result["statusCode"] == 200
        body = json.loads(result["body"])
        assert "orders" in body
        assert len(body["orders"]) == 1


@patch.dict(os.environ, {"TABLE_NAME": TABLE_NAME})
def test_get_order():
    with mock_orders_table():
        from assets.get_order import lambda_handler

        event = create_powertools_event(
            method="GET",
            path=f"/orders/{ORDER_ID}",
            path_params={"orderId": ORDER_ID}
        )

        result = lambda_handler(event, {})
        assert result["statusCode"] == 200
        body = json.loads(result["body"])
        assert body["orderId"] == ORDER_ID
        assert body["userId"] == USER_ID


@patch.dict(os.environ, {"TABLE_NAME": TABLE_NAME})
def test_edit_order():
    with mock_orders_table():
        from assets.edit_order import lambda_handler

        new_order_data = {
            "restaurantId": "rest-123",
            "totalAmount": 35.99,
            "orderItems": [{"name": "Burger", "price": 35.99, "quantity": 1}],
            "status": "PLACED"
        }
        
        event = create_powertools_event(
            method="POST",  
            path=f"/orders/edit/{ORDER_ID}",
            body=new_order_data,
            path_params={"orderId": ORDER_ID}
        )

        result = lambda_handler(event, {})
        assert result["statusCode"] == 200


@patch.dict(os.environ, {"TABLE_NAME": TABLE_NAME})
def test_cancel_order():
    with mock_orders_table():
        from assets.cancel_order import lambda_handler

        event = create_powertools_event(
            method="POST",  
            path=f"/orders/cancel/{ORDER_ID}",
            path_params={"orderId": ORDER_ID}
        )

        result = lambda_handler(event, {})
        assert result["statusCode"] == 200
        body = json.loads(result["body"])
        assert body["status"] == "CANCELED"


@patch.dict(os.environ, {"TABLE_NAME": TABLE_NAME})
def test_cancel_order_time_limit():
    with mock_dynamodb():
        dynamodb = boto3.client("dynamodb")
        
        dynamodb.create_table(
            TableName=TABLE_NAME,
            KeySchema=[
                {"AttributeName": "userId", "KeyType": "HASH"},
                {"AttributeName": "orderId", "KeyType": "RANGE"},
            ],
            AttributeDefinitions=[
                {"AttributeName": "userId", "AttributeType": "S"},
                {"AttributeName": "orderId", "AttributeType": "S"},
            ],
            BillingMode="PAY_PER_REQUEST"
        )


        old_time = int(time.time()) - 700  
        
        dynamodb.put_item(
            TableName=TABLE_NAME,
            Item={
                "userId": {"S": USER_ID},
                "orderId": {"S": ORDER_ID},
                "data": {
                    "M": {
                        "status": {"S": "PLACED"},
                        "orderTime": {"S": str(old_time)}
                    }
                }
            }
        )
        
        from assets.cancel_order import lambda_handler
        
        event = create_powertools_event(
            method="POST",
            path=f"/orders/cancel/{ORDER_ID}",
            path_params={"orderId": ORDER_ID}
        )

        result = lambda_handler(event, {})
        assert result["statusCode"] == 400
        body = json.loads(result["body"])
        assert "cannot be canceled" in body["error"].lower()


@patch.dict(os.environ, {"TABLE_NAME": TABLE_NAME})
def test_create_order_missing_fields():
    with mock_orders_table():
        from assets.create_order import lambda_handler
        
     
        incomplete_data = {
            "totalAmount": 30.50,
            "orderItems": [{"name": "Burger"}]
        }
        
        event = create_powertools_event(
            method="POST",
            path=f"/orders/{USER_ID}",
            body=incomplete_data
        )
        
        result = lambda_handler(event, {})
        assert result["statusCode"] == 400
        body = json.loads(result["body"])
        assert "Missing key: restaurantId" in body["error"]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])