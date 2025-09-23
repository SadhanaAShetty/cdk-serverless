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
