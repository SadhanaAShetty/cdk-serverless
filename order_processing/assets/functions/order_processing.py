import boto3
import json
import os
import random
import string
from aws_lambda_powertools import Logger
from aws_lambda_powertools.event_handler import APIGatewayRestResolver
from aws_lambda_powertools.event_handler.api_gateway import Response
from aws_lambda_powertools.utilities.typing import LambdaContext

dynamodb = boto3.resource("dynamodb")
table = dynamodb.Table("dynamo")
sns = boto3.client("sns")

logger = Logger()
app = APIGatewayRestResolver()

TOPIC_ARN = os.getenv("TOPIC_ARN")


@app.post("/orders")
def order_call():
    logger.info("Inside order handler")
    data: dict = app.current_event.json_body

    required_keys = ["customer_id", "item", "quantity", "address"]
    for key in required_keys:
        if key not in data:
            return Response(
                status_code=400,
                content_type="application/json",
                body=json.dumps({"error": f"Missing key: {key}"}),
            )

    def generate_order_id(length=8):
        characters = string.digits
        return "".join(random.choice(characters) for _ in range(length))

    order_id = generate_order_id()

    item_to_store = {
        "order_id": order_id,
        "customer_id": data["customer_id"],
        "item": data["item"],
        "address": data["address"],
        "quantity": data["quantity"],
    }

    table.put_item(Item=item_to_store)

    sns.publish(
        TopicArn=TOPIC_ARN,
        Message=json.dumps(item_to_store),
        Subject="New Order Received",
    )

    confirmation = {
        "message": "Order received successfully! Thank you for your order. We will process it shortly.",
        "order_id": order_id,
        "customer_id": data["customer_id"],
        "item": data["item"],
        "address": data["address"],
        "quantity": data["quantity"],
    }

    return Response(
        status_code=200, content_type="application/json", body=json.dumps(confirmation)
    )


@logger.inject_lambda_context
def lambda_handler(event: dict, context: LambdaContext):
    return app.resolve(event, context)
