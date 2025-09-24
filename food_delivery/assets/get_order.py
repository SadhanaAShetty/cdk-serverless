import os
import json
import boto3
from aws_lambda_powertools import Logger, Tracer
from aws_lambda_powertools.event_handler import APIGatewayRestResolver
from utils import get_order

logger = Logger()
tracer = Tracer()
app = APIGatewayRestResolver()


@tracer.capture_method
@app.get("/orders/{orderId}")
def get_order_handler():
    event = app.current_event.request
    user_id = event["requestContext"]["authorizer"]["claims"]["sub"]
    order_id = event["pathParameters"]["orderId"]

    try:
        order = get_order(user_id, order_id)
        logger.info(f"Retrieved order {order_id} for user {user_id}")
        return {
            "statusCode": 200,
            "body": json.dumps(order, default=str)
        }

    except Exception as e:
        logger.exception(f"Error retrieving order {order_id} for user {user_id}: {e}")
        return {
            "statusCode": 500,
            "body": json.dumps({"error": "Internal Server Error"})
        }


def lambda_handler(event, context):
    return app.resolve(event, context)
