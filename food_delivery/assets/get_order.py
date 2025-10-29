import os
import json
import boto3
from aws_lambda_powertools import Logger, Tracer
from aws_lambda_powertools.event_handler import APIGatewayRestResolver

logger = Logger()
tracer = Tracer()
app = APIGatewayRestResolver()

dynamodb = boto3.resource("dynamodb")
table = dynamodb.Table(os.environ["TABLE_NAME"])


@tracer.capture_method
@app.get("/orders/{orderId}")
def get_order_handler():
    logger.info("GET ORDER LAMBDA CALLED")
    try:
        logger.info("GET ORDER: Lambda function started")
        logger.info(f"GET ORDER: Full event: {app.current_event.raw_event}")


        return {
            "statusCode": 200,
            "body": json.dumps({"message": "Lambda is working", "orderId": "test"}),
        }

    except Exception as e:
        logger.exception(f"GET ORDER: Error in handler: {e}")
        return {
            "statusCode": 500,
            "body": json.dumps({"error": "Internal Server Error", "details": str(e)}),
        }


def lambda_handler(event, context):
    logger.info("GET ORDER LAMBDA HANDLER")

    try:
        authorizer = event.get("requestContext", {}).get("authorizer", {})
        userId = authorizer.get("userId")

        logger.info(f"Authorizer context: {authorizer}")
        logger.info(f"Extracted userId: {userId}")

        if not userId:
            logger.error("No userId found in authorizer context")
            return {
                "statusCode": 401,
                "body": json.dumps({"error": "Unauthorized - No userId"}),
                "headers": {"Content-Type": "application/json"},
            }


        orderId = event.get("pathParameters", {}).get("orderId")
        logger.info(f"Extracted orderId: {orderId}")

        if not orderId:
            logger.error("No orderId found in path parameters")
            return {
                "statusCode": 400,
                "body": json.dumps({"error": "Bad Request - No orderId"}),
                "headers": {"Content-Type": "application/json"},
            }

        
        logger.info(f"Querying DynamoDB with userId: {userId}, orderId: {orderId}")
        response = table.get_item(Key={"userId": userId, "orderId": orderId})
        logger.info(f"DynamoDB response: {response}")

        if "Item" not in response:
            logger.error(f"Order not found - userId: {userId}, orderId: {orderId}")
            return {
                "statusCode": 404,
                "body": json.dumps(
                    {"error": "Order not found", "userId": userId, "orderId": orderId}
                ),
                "headers": {"Content-Type": "application/json"},
            }

        order = response["Item"]
        logger.info(f"Found order: {order}")

        return {
            "statusCode": 200,
            "body": json.dumps(order, default=str),
            "headers": {"Content-Type": "application/json"},
        }

    except Exception as e:
        logger.exception(f"Error in lambda_handler: {str(e)}")
        return {
            "statusCode": 500,
            "body": json.dumps({"error": "Internal Server Error", "details": str(e)}),
            "headers": {"Content-Type": "application/json"},
        }
