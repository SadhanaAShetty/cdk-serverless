import os
import uuid
import json
from datetime import datetime
from decimal import Decimal
import boto3
from aws_lambda_powertools import Logger, Tracer
from aws_lambda_powertools.event_handler import APIGatewayRestResolver

logger = Logger()
tracer = Tracer()
app = APIGatewayRestResolver()

dynamodb = boto3.resource("dynamodb")
table = dynamodb.Table(os.environ["TABLE_NAME"])


class DecimalEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, Decimal):
            return float(obj)
        return super().default(obj)


@tracer.capture_method
@app.post("/orders")
def create_order():
    authorizer = getattr(app.current_event.request_context, "authorizer", {})
    userId = None


    if hasattr(authorizer, "claims") and authorizer.claims:
        userId = authorizer.claims.get("sub")
    elif hasattr(authorizer, "userId"):
        userId = authorizer.userId
    elif isinstance(authorizer, dict):
        userId = authorizer.get("userId")

    logger.info(f"Authorizer context: {authorizer}")
    logger.info(f"Extracted userId: {userId}")

    if not userId:
        return {"statusCode": 401, "body": json.dumps({"error": "Unauthorized"})}

    data = app.current_event.json_body
    required_keys = ["restaurantId", "totalAmount", "orderItems"]
    for key in required_keys:
        if key not in data:
            return {
                "statusCode": 400,
                "body": json.dumps({"error": f"Missing key: {key}"}),
            }

    order_id = str(uuid.uuid4())
    order_time = datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")

    item_to_store = {
        "userId": userId,
        "orderId": order_id,
        "restaurantId": data["restaurantId"],
        "totalAmount": Decimal(str(data["totalAmount"])),
        "orderItems": data["orderItems"],
        "status": "PLACED",
        "timestamp": int(datetime.utcnow().timestamp()),
        "orderTime": order_time,
    }

    try:
        table.put_item(
            Item=item_to_store,
            ConditionExpression="attribute_not_exists(orderId) AND attribute_not_exists(userId)",
        )

        return {
            "statusCode": 200,
            "body": json.dumps(item_to_store, cls=DecimalEncoder),
        }

    except Exception as e:
        logger.error(f"Error creating order: {str(e)}")
        return {
            "statusCode": 500,
            "body": json.dumps({"error": "Internal Server Error"}),
        }


def lambda_handler(event, context):
    logger.debug(f"Incoming event: {json.dumps(event)}")

    if (
        event.get("httpMethod") == "POST"
        and event.get("path") == "/orders"
        and "requestContext" in event
        and "authorizer" in event["requestContext"]
    ):
        return handle_create_order_direct(event, context)

    try:
        return app.resolve(event, context)
    except Exception as e:
        logger.error(f"Error in lambda_handler: {str(e)}")
        return {
            "statusCode": 500,
            "body": json.dumps({"error": "Internal Server Error"}),
        }


def handle_create_order_direct(event, context):
    try:
        request_context = event.get("requestContext", {})
        authorizer = request_context.get("authorizer", {})

       
        userId = None
        if "claims" in authorizer:
            claims = (
                json.loads(authorizer["claims"])
                if isinstance(authorizer["claims"], str)
                else authorizer["claims"]
            )
            userId = claims.get("sub")
        elif "userId" in authorizer:
            userId = authorizer["userId"]

        logger.info(f"Direct handler - Authorizer context: {authorizer}")
        logger.info(f"Direct handler - Extracted userId: {userId}")

        if not userId:
            return {"statusCode": 401, "body": json.dumps({"error": "Unauthorized"})}

        body = event.get("body")
        if not body:
            return {
                "statusCode": 400,
                "body": json.dumps({"error": "Missing request body"}),
            }

        data = json.loads(body)
        required_keys = ["restaurantId", "totalAmount", "orderItems"]
        for key in required_keys:
            if key not in data:
                return {
                    "statusCode": 400,
                    "body": json.dumps({"error": f"Missing key: {key}"}),
                }

        order_id = str(uuid.uuid4())
        order_time = datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")

        order_items = []
        for item in data["orderItems"]:
            order_item = item.copy()
            if "price" in order_item:
                order_item["price"] = Decimal(str(order_item["price"]))
            order_items.append(order_item)

        item_to_store = {
            "userId": userId,
            "orderId": order_id,
            "restaurantId": data["restaurantId"],
            "totalAmount": Decimal(str(data["totalAmount"])),
            "orderItems": order_items,
            "status": "PLACED",
            "timestamp": int(datetime.utcnow().timestamp()),
            "orderTime": order_time,
        }

        dynamodb = boto3.resource("dynamodb")
        test_table = dynamodb.Table(os.environ["TABLE_NAME"])

        test_table.put_item(
            Item=item_to_store,
            ConditionExpression="attribute_not_exists(orderId) AND attribute_not_exists(userId)",
        )

        return {
            "statusCode": 200,
            "body": json.dumps(item_to_store, cls=DecimalEncoder),
        }

    except Exception as e:
        logger.error(f"Error creating order: {str(e)}")
        return {
            "statusCode": 500,
            "body": json.dumps({"error": "Internal Server Error"}),
        }
