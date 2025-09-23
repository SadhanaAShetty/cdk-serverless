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
    

def lambda_handler(event: dict, context):
    logger.info("Processing order management request", extra={"event": event})
    return app.resolve(event, context)