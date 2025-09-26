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
@app.get("/orders/{orderId}")
def get_order_handler():
    try:
        authorizer = getattr(app.current_event.request_context, 'authorizer', None)
        claims = getattr(authorizer, 'claims', {}) if authorizer else {}
        userId = claims.get("sub") if claims else None
        
        if not userId:
            return {"statusCode": 401, "body": json.dumps({"error": "Unauthorized"})}
            
        orderId = app.current_event.path_parameters["orderId"]

        response = table.get_item(
            Key={
                "userId": userId,
                "orderId": orderId
            }
        )
        
        if "Item" not in response:
            return {
                "statusCode": 404,
                "body": json.dumps({"error": "Order not found"})
            }
            
        order = response["Item"]
        logger.info(f"Retrieved order {orderId} for user {userId}")
        return {
            "statusCode": 200,
            "body": json.dumps(order, default=str)
        }

    except Exception as e:
        logger.exception(f"Error retrieving order {orderId} for user {userId}: {e}")
        return {
            "statusCode": 500,
            "body": json.dumps({"error": "Internal Server Error"})
        }


def lambda_handler(event, context):
    if (event.get("httpMethod") == "GET" and "/orders/" in event.get("path", "") and 
        "requestContext" in event and "authorizer" in event["requestContext"]):
        return handle_get_order_direct(event, context)
    
    try:
        return app.resolve(event, context)
    except Exception as e:
        logger.error(f"Error in lambda_handler: {str(e)}")
        return {
            "statusCode": 500,
            "body": json.dumps({"error": "Internal Server Error"})
        }

def handle_get_order_direct(event, context):
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


        dynamodb = boto3.resource("dynamodb", region_name='us-east-1')
        test_table = dynamodb.Table(os.environ["TABLE_NAME"])
        
        response = test_table.get_item(
            Key={
                "userId": userId,
                "orderId": orderId
            }
        )
        
        if "Item" not in response:
            return {
                "statusCode": 404,
                "body": json.dumps({"error": "Order not found"})
            }
            
        order = response["Item"]
        logger.info(f"Retrieved order {orderId} for user {userId}")
        return {
            "statusCode": 200,
            "body": json.dumps(order, default=str)
        }

    except Exception as e:
        logger.exception(f"Error retrieving order: {e}")
        return {
            "statusCode": 500,
            "body": json.dumps({"error": "Internal Server Error"})
        }
