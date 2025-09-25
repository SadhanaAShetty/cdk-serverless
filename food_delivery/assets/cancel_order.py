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
def cancel_order():
    event = app.current_event.request
    user_id = event["requestContext"]["authorizer"]["claims"]["sub"]
    order_id = event["pathParameters"]["orderId"]

    current_time = time.time()

    try:
        response = table.update_item(
            Key={"userId": user_id, "orderId": order_id},
            UpdateExpression="set #data.#status = :new_status",
            ConditionExpression="(#data.#status = :current_status) AND (#data.orderTime > :minOrderTime)",
            ExpressionAttributeNames={
                "#data": "data",
                "#status": "status"
            },
            ExpressionAttributeValues={
                ":current_status": "PLACED",
                ":new_status": "CANCELED",
                ":minOrderTime": str(current_time - 600) 
            },
            ReturnValues="ALL_NEW"
        )
        logger.info(f"Order {order_id} for user {user_id} successfully canceled.")
        print(f"Order {order_id} successfully canceled!")

        return {
            "statusCode": 200,
            "body": json.dumps(response["Attributes"]["data"])
        }

    except ClientError as e:
        if e.response["Error"]["Code"] == "ConditionalCheckFailedException":
            return {
                "statusCode": 400,
                "body": json.dumps({
                    "error": f"Order {order_id} cannot be canceled. Status must be PLACED and within 10 minutes of creation."
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