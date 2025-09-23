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


