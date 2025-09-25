import os
import uuid
import json
from datetime import datetime
from typing import List, Dict, Any
from decimal import Decimal
import boto3
import time
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
@app.post("/orders/cancel/{orderId}")
def cancel_order(orderId: str): 
    userId = app.current_event.request_context.authorizer.claims.get("sub")
    
    if not userId:
        return {
            "statusCode": 401,
            "body": json.dumps({"error": "User not authenticated"})
        }

    current_time = time.time()

    try:
        response = table.update_item(
            Key={"userId": userId, "orderId": orderId},
            UpdateExpression="SET #status = :new_status, canceledAt = :canceled_time",
            ConditionExpression="(#status = :current_status) AND (orderTime > :minOrderTime)",
            ExpressionAttributeNames={
                "#status": "status"
            },
            ExpressionAttributeValues={
                ":current_status": "PLACED",
                ":new_status": "CANCELED",
                ":minOrderTime": current_time - 600, 
                ":canceled_time": datetime.utcnow().isoformat()
            },
            ReturnValues="ALL_NEW"
        )
        
        logger.info(f"Order {orderId} for user {userId} successfully canceled.")

        return {
            "statusCode": 200,
            "body": json.dumps({
                "message": f"Order {orderId} successfully canceled",
                "order": response["Attributes"]
            }, default=str) 
        }

    except ClientError as e:
        if e.response["Error"]["Code"] == "ConditionalCheckFailedException":
            return {
                "statusCode": 400,
                "body": json.dumps({
                    "error": f"Order {orderId} cannot be canceled. Status must be PLACED and within 10 minutes of creation."
                })
            }
        logger.exception(f"DynamoDB ClientError: {e}")
        return {
            "statusCode": 500,
            "body": json.dumps({"error": "Internal Server Error"})
        }

    except Exception as e:
        logger.exception(f"Unexpected error: {e}")
        return {
            "statusCode": 500,
            "body": json.dumps({"error": "Internal Server Error"})
        }


def lambda_handler(event, context):
    return app.resolve(event, context)