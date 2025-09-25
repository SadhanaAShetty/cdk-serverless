import os
import json
import boto3
from boto3.dynamodb.conditions import Key
from aws_lambda_powertools import Logger, Tracer
from aws_lambda_powertools.event_handler import APIGatewayRestResolver

logger = Logger()
tracer = Tracer()
app = APIGatewayRestResolver()

dynamodb = boto3.resource("dynamodb")
table = dynamodb.Table(os.environ["TABLE_NAME"])


@tracer.capture_method
@app.get("/orders")
def list_orders():
    event = app.current_event.request
    userId = event["requestContext"]["authorizer"]["claims"]["sub"]

    try:
        response = table.query(
            KeyConditionExpression=Key("userId").eq(userId)
        )
        orders = [item["data"] for item in response.get("Items", [])]
        logger.info(f"Retrieved {len(orders)} orders for user {userId}")
        return {
            "statusCode": 200,
            "body": json.dumps({"orders": orders}, default=str)
        }

    except Exception as e:
        logger.exception(f"Error listing orders for user {userId}: {e}")
        return {
            "statusCode": 500,
            "body": json.dumps({"error": "Internal Server Error"})
        }

def lambda_handler(event, context):
    return app.resolve(event, context)
