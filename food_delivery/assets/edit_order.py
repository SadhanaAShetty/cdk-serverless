import os
import json
from decimal import Decimal
import boto3
from botocore.exceptions import ClientError
from aws_lambda_powertools import Logger, Tracer
from aws_lambda_powertools.event_handler import APIGatewayRestResolver

logger = Logger()
tracer = Tracer()
app = APIGatewayRestResolver()

dynamodb = boto3.resource("dynamodb")
table = dynamodb.Table(os.environ["TABLE_NAME"])


@tracer.capture_method
@app.put("/orders/{orderId}")
def edit_order_handler():
    try:
        authorizer = getattr(app.current_event.request_context, "authorizer", None)
        claims = getattr(authorizer, "claims", {}) if authorizer else {}
        userId = claims.get("sub") if claims else None

        if not userId:
            return {"statusCode": 401, "body": json.dumps({"error": "Unauthorized"})}

        orderId = app.current_event.path_parameters["orderId"]
        data = app.current_event.json_body


        response = table.update_item(
            Key={"userId": userId, "orderId": orderId},
            UpdateExpression="SET restaurantId = :rid, totalAmount = :amount, orderItems = :items",
            ExpressionAttributeValues={
                ":rid": data.get("restaurantId"),
                ":amount": Decimal(str(data.get("totalAmount"))),
                ":items": data.get("orderItems"),
            },
            ReturnValues="ALL_NEW",
        )

        logger.info(f"Updated order {orderId} for user {userId}")
        return {
            "statusCode": 200,
            "body": json.dumps(response["Attributes"], default=str),
        }

    except Exception as e:
        logger.exception(f"Error updating order {orderId} for user {userId}: {e}")
        return {
            "statusCode": 500,
            "body": json.dumps({"error": "Internal Server Error"}),
        }


def lambda_handler(event, context):
    logger.debug(f"Edit order event: {json.dumps(event)}")
    if (
        event.get("httpMethod") == "PUT"
        and "/orders/" in event.get("path", "")
        and "requestContext" in event
        and "authorizer" in event["requestContext"]
    ):
        logger.debug("Using direct handler for edit order")
        return handle_edit_order_direct(event, context)

    logger.debug("Using app.resolve for edit order")
    try:
        return app.resolve(event, context)
    except Exception as e:
        logger.error(f"Error in lambda_handler: {str(e)}")
        return {
            "statusCode": 500,
            "body": json.dumps({"error": "Internal Server Error"}),
        }


def handle_edit_order_direct(event, context):
    try:
        request_context = event.get("requestContext", {})
        authorizer = request_context.get("authorizer", {})
        claims = authorizer.get("claims", {})
        userId = claims.get("sub")

        if not userId:
            return {"statusCode": 401, "body": json.dumps({"error": "Unauthorized"})}

        path_params = event.get("pathParameters", {})
        orderId = path_params.get("orderId")

        if not orderId:
            return {"statusCode": 400, "body": json.dumps({"error": "Missing orderId"})}

        body = event.get("body")
        if not body:
            return {
                "statusCode": 400,
                "body": json.dumps({"error": "Missing request body"}),
            }

        data = json.loads(body)


        dynamodb = boto3.resource("dynamodb", region_name="us-east-1")
        test_table = dynamodb.Table(os.environ["TABLE_NAME"])


        print(f"DEBUG: Looking for userId={userId}, orderId={orderId}")
        existing_item = test_table.get_item(
            Key={"userId": userId, "orderId": orderId}
        )
        print(f"DEBUG: get_item result: {existing_item}")
        
        if "Item" not in existing_item:
            print("DEBUG: Item not found, returning 404")
            return {
                "statusCode": 404,
                "body": json.dumps({"error": "Order not found"})
            }


        response = test_table.update_item(
            Key={"userId": userId, "orderId": orderId},
            UpdateExpression="SET restaurantId = :rid, totalAmount = :amount, orderItems = :items",
            ExpressionAttributeValues={
                ":rid": data.get("restaurantId"),
                ":amount": Decimal(str(data.get("totalAmount"))),
                ":items": data.get("orderItems"),
            },
            ReturnValues="ALL_NEW",
        )

        logger.info(f"Updated order {orderId} for user {userId}")
        return {
            "statusCode": 200,
            "body": json.dumps(response["Attributes"], default=str),
        }

    except Exception as e:
        logger.exception(f"Error updating order: {e}")
        logger.error(f"Exception type: {type(e).__name__}")
        logger.error(f"Exception args: {e.args}")
        return {
            "statusCode": 500,
            "body": json.dumps({"error": "Internal Server Error"}),
        }
