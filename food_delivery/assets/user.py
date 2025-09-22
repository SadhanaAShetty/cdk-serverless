import os
import uuid
import json
from datetime import datetime
from typing import List, Dict, Any
from decimal import Decimal
import boto3
from botocore.exceptions import ClientError
from aws_lambda_powertools import Logger, Tracer
from aws_lambda_powertools.event_handler import APIGatewayRestResolver
from aws_lambda_powertools.utilities.typing import LambdaContext

logger = Logger()
tracer = Tracer()
app = APIGatewayRestResolver()

dynamodb = boto3.resource("dynamodb")
table = dynamodb.Table(os.environ["TABLE_NAME"])


@tracer.capture_method
@app.get("/orders/{user_id}")
def get_user_orders(user_id: str):
    try:
        response = table.query(
            KeyConditionExpression=boto3.dynamodb.conditions.Key('user_id').Key('order_id')
        )
        
        orders = []
        for item in response.get("Items", []):
            orders.append(item['data'])

        return {
            "statusCode": 200,
            "body": json.dumps({
                "orders": orders,
                "count": len(orders),
                "userId": user_id
            })
        }
    except Exception as e:
        logger.error(f"Error querying orders for user {user_id}: {str(e)}")
        return {"statusCode": 500, "body": json.dumps({"error": "Internal Server Error"})}


@tracer.capture_method
@app.get("/orders/{user_id}/status/{status}")
def get_user_orders_by_status(user_id: str, status: str):
    try:
        response = table.query(
            KeyConditionExpression=boto3.dynamodb.conditions.Key('userId').eq(user_id),
            FilterExpression=boto3.dynamodb.conditions.Attr('status').eq(status)
        )
        
        orders = []
        for item in response.get("Items", []):
            orders.append({
                "userId": item["userId"],
                "orderId": item["orderId"],
                "customer_name": item.get("customer_name"),
                "customer_email": item.get("customer_email"),
                "items": item.get("items", []),
                "total_amount": item.get("total_amount"),
                "status": item.get("status"),
                "delivery_address": item.get("delivery_address"),
                "created_at": item.get("created_at"),
                "updated_at": item.get("updated_at")
            })

        return {
            "statusCode": 200,
            "body": json.dumps({
                "orders": orders,
                "count": len(orders),
                "userId": user_id,
                "status": status
            })
        }
    except Exception as e:
        logger.error(f"Error querying orders for user {user_id} with status {status}: {str(e)}")
        return {"statusCode": 500, "body": json.dumps({"error": "Internal Server Error"})}


@tracer.capture_method
@app.get("/orders/{user_id}/recent")
def get_recent_orders(user_id: str):
    try:
        response = table.query(
            KeyConditionExpression=boto3.dynamodb.conditions.Key('userId').eq(user_id),
            ScanIndexForward=False,  
            Limit=10 
        )
        
        orders = []
        for item in response.get("Items", []):
            orders.append({
                "userId": item["userId"],
                "orderId": item["orderId"],
                "customer_name": item.get("customer_name"),
                "items": item.get("items", []),
                "total_amount": item.get("total_amount"),
                "status": item.get("status"),
                "created_at": item.get("created_at")
            })

        return {
            "statusCode": 200,
            "body": json.dumps({
                "orders": orders,
                "count": len(orders),
                "userId": user_id
            })
        }
    except Exception as e:
        logger.error(f"Error querying recent orders for user {user_id}: {str(e)}")
        return {"statusCode": 500, "body": json.dumps({"error": "Internal Server Error"})}


@tracer.capture_method
@app.get("/orders/{user_id}/{order_id}")
def get_single_order(user_id: str, order_id: str):
    logger.info(f"Retrieving order {order_id} for user {user_id}")
    
    try:
        response = table.get_item(
            Key={
                "userId": user_id,
                "orderId": order_id
            }
        )
        
        if "Item" not in response:
            return {"statusCode": 404, "body": json.dumps({"error": "Order not found"})}

        item = response["Item"]
        order = {
            "userId": item["userId"],
            "orderId": item["orderId"],
            "customer_name": item.get("customer_name"),
            "customer_email": item.get("customer_email"),
            "items": item.get("items", []),
            "total_amount": item.get("total_amount"),
            "status": item.get("status", "pending"),
            "delivery_address": item.get("delivery_address"),
            "special_instructions": item.get("special_instructions", ""),
            "created_at": item.get("created_at"),
            "updated_at": item.get("updated_at")
        }

        return {"statusCode": 200, "body": json.dumps(order)}
    except Exception as e:
        logger.error(f"Error getting order {order_id} for user {user_id}: {str(e)}")
        return {"statusCode": 500, "body": json.dumps({"error": "Internal Server Error"})}


#post
@tracer.capture_method
@app.post("/orders/{user_id}")
def create_order(user_id: str):
    data = app.current_event.json_body

    required = ["restaurantId", "totalAmount", "orderItems"]
    for field in required:
        if field not in data:
            return {
                "statusCode": 400,
                "body": json.dumps({"error": f"Missing field: {field}"})
            }


    restaurant_id = data["restaurantId"]
    total_amount = data["totalAmount"]
    order_items = data["orderItems"]
    order_id = data.get("orderId", str(uuid.uuid4()))
    order_time = datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")

    ddb_item = {
        "orderId": order_id,
        "userId": user_id,
        "data": {
            "orderId": order_id,
            "userId": user_id,
            "restaurantId": restaurant_id,
            "totalAmount": total_amount,
            "orderItems": order_items,
            "status": "PLACED",
            "order_time": order_time,
        },
    }
    ddb_item = json.loads(json.dumps(ddb_item), parse_float=Decimal)

    try:
        table.put_item(
            Item=ddb_item,
            ConditionExpression="attribute_not_exists(orderId) AND attribute_not_exists(userId)"
        )

        data["order_id"] = order_id
        data["order_time"] = order_time
        data["status"] = "PLACED"

        return {
            "statusCode": 200,
            "body": json.dumps(data)
        }
    except Exception as e:
        logger.error(f"Error creating order: {e}")
        return {
            "statusCode": 500,
            "body": json.dumps({"error": "Internal Server Error"})
        }



@tracer.capture_method
@app.put("/orders/{user_id}/{order_id}")
def update_order(user_id: str, order_id: str):
    data = app.current_event.json_body


    data["userId"] = user_id
    data["orderId"] = order_id

    ddb_item = {
        "orderId": order_id,
        "userId": user_id,
        "data": data
    }
    ddb_item = json.loads(json.dumps(ddb_item), parse_float=Decimal)

    try:
        table.put_item(
            Item=ddb_item,
            ConditionExpression="attribute_exists(order_id) AND attribute_exists(user_id) AND #data.#status = :status",
            ExpressionAttributeNames={
                "data": "data",
                "status": "status"
            },
            ExpressionAttributeValues={
                ":status": "PLACED"
            },
            ReturnValuesOnConditionCheckFailure="ALL_OLD"
        )

        logger.info(f"Order {order_id} updated successfully for user {user_id}")

        return {
            "statusCode": 200,
            "body": json.dumps({
                "message": "Order updated successfully",
                "order": data
            })
        }

    except ClientError as exc:
        if exc.response["Error"]["Code"] == "ConditionalCheckFailedException":
            return {
                "statusCode": 400,
                "body": json.dumps({
                    "error": f"Cannot edit Order {order_id}. Please check if it exists and status is PLACED."
                })
            }
        else:
            logger.error(f"DynamoDB error: {exc}")
            return {
                "statusCode": 500,
                "body": json.dumps({"error": "Internal Server Error"})
            }

    except Exception as e:
        logger.error(f"Unexpected error updating order {order_id}: {e}")
        return {
            "statusCode": 500,
            "body": json.dumps({"error": "Internal Server Error"})
        }

@tracer.capture_method
@app.delete("/orders/{user_id}/{order_id}")
def delete_order(user_id: str, order_id: str):
    try:
        response = table.get_item(
            Key={
                "userId": user_id,
                "orderId": order_id
            }
        )
        if "Item" not in response:
            return {"statusCode": 404, "body": json.dumps({"error": "Order not found"})}
        
        table.delete_item(
            Key={
                "userId": user_id,
                "orderId": order_id
            }
        )
        
        return {
            "statusCode": 200,
            "body": json.dumps({
                "message": f"Order {order_id} for user {user_id} deleted successfully"
            })
        }
    except Exception as e:
        logger.error(f"Error deleting order {order_id} for user {user_id}: {str(e)}")
        return {"statusCode": 500, "body": json.dumps({"error": "Internal Server Error"})}


@tracer.capture_method
@app.patch("/orders/{user_id}/{order_id}/status")
def update_order_status(user_id: str, order_id: str):
    data: dict = app.current_event.json_body
    
    if not data or "status" not in data:
        return {"statusCode": 400, "body": json.dumps({"error": "Status field is required"})}
    
    valid_statuses = ["pending", "confirmed", "preparing", "out_for_delivery", "delivered", "cancelled"]
    if data["status"] not in valid_statuses:
        return {
            "statusCode": 400, 
            "body": json.dumps({
                "error": f"Invalid status. Valid options: {valid_statuses}"
            })
        }
    
    try:
        table.update_item(
            Key={
                "userId": user_id,
                "orderId": order_id
            },
            UpdateExpression="SET #status = :status, updated_at = :updated_at",
            ConditionExpression="attribute_exists(userId) AND attribute_exists(orderId)",
            ExpressionAttributeNames={"#status": "status"},
            ExpressionAttributeValues={
                ":status": data["status"],
                ":updated_at": datetime.utcnow().isoformat()
            }
        )
        
        return {
            "statusCode": 200,
            "body": json.dumps({
                "message": f"Order status updated to {data['status']}",
                "userId": user_id,
                "orderId": order_id,
                "status": data["status"]
            })
        }
    except dynamodb.meta.client.exceptions.ConditionalCheckFailedException:
        return {"statusCode": 404, "body": json.dumps({"error": "Order not found"})}
    except Exception as e:
        logger.error(f"Error updating order status {order_id} for user {user_id}: {str(e)}")
        return {"statusCode": 500, "body": json.dumps({"error": "Internal Server Error"})}


def lambda_handler(event: dict, context):
    logger.info("Processing order management request", extra={"event": event})
    return app.resolve(event, context)